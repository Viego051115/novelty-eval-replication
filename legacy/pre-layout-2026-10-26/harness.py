# -*- coding: utf-8 -*-
"""
复刻脚本 —— LLM 新颖性评委（pairwise）
论文: Old Ideas, Novel Problems (arXiv:2610.02022v1)
方案 A: 复用官方数据，替换评判器骨干为国产模型。

用法:
    python harness.py --prompt ref --provider deepseek --limit 5
    python harness.py --prompt P3  --provider glm      --limit 5
    python harness.py --prompt P4  --provider kimi     --limit 5
"""
import os, re, json, argparse, time
import urllib.request, urllib.error
import pandas as pd

# ---------- 从 .env 读取 key ----------
def load_env(path=".env"):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

ENV = load_env()

# ---------- 三家国产模型的配置 ----------
PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/chat/completions",
        "key": ENV.get("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "temperature": 0.0,
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1/chat/completions",
        "key": ENV.get("KIMI_API_KEY", ""),
        "model": "kimi-k2.6",
        "temperature": None,   # kimi-k2.6 不支持 temperature 参数
        "timeout": 300,        # 推理型模型，响应慢
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "key": ENV.get("GLM_API_KEY", ""),
        "model": "glm-4-flash",   # 免费版（glm-4-plus 需充值）
    },
}

# ---------- 三种 prompt（原文 Prompt 4 / 10 / 11） ----------
PROMPTS = {
    # 参考配置（原文 Prompt 4，带完整新颖性判据）
    "ref": """You are a senior reviewer for an AI scientific conference such as ICLR, ACL, ICML. Your task is to review the novelty of the following two ideas and to decide which one is more novel. Focus only on the novelty and not on other aspects such as feasibility, clarity, etc.
### Idea-0
{idea0}
### Idea-1
{idea1}
Compare these ideas based on the following criteria:
Novelty: The substantive originality of the idea, characterized by:
- The introduction of new frameworks, concepts, evaluations, resources or approaches absent from existing knowledge.
- The non-trivial synthesis of existing frameworks, concepts, evaluations, resources or approaches.
- The extension of established frameworks, concepts, evaluations, resources or approaches into previously unexplored problem domains.
In general, composite methods / multi-stage pipelines built from several existing motifs in haphazard manner, stringing together all kinds of common methods, are NOT to be considered novel, except if the composition is highly different than any existing work, involves substantial creativity, and the combination is highly non-trivial.
Do NOT rely on assumptions of all kinds of unknown hypotheticals. For example, "this could be novel IF formulated as..." is NOT acceptable as a reason to judge an idea as novel. Only use what is explicitly stated.
Do NOT assume a new model/training method/technical algorithmic/mathematical contribution is more novel than a new analysis, new evaluation, new task, or new resource. All types of contributions could either be novel, or not, depending on context and the state of scientific knowledge.
**Tip**: Think about the main contributions of each idea. Which makes more novel contributions? Which makes relatively more incremental contributions?
**Comparative Logic**:
* Assign **0** if the novelty of Idea-0 is superior.
* Assign **1** if the novelty of Idea-1 is superior.
**Required Response Format**:
<thinking>
[Your reasoning here]
</thinking>
```json
{{
"novelty": <0 or 1>
}}
```""",

    # P3「哪个被判为新颖？」（原文 Prompt 10，评审预设 + 二值）
    "P3": """You are a reviewer specialized in Artificial intelligence and Machine Learning research. You are given two ideas. One of them is judged as novel by reviewers for a top AI conference (like ICLR or ACL) reviewers and the other one is not. Your task is to identify the one that is judged as novel.
The two ideas are:
paper 0: {idea0}
paper 1: {idea1}
Now decide which one is judged as novel. Return a json string with the selected idea index {{'novelty': <index>}} and nothing else.""",

    # P4「哪个新颖？」（原文 Prompt 11，去掉评审预设）
    "P4": """You are a reviewer specialized in Artificial intelligence and Machine Learning research. You are given two ideas. Your task is to identify the one that is novel.
The two ideas are:
paper 0: {idea0}
paper 1: {idea1}
Now decide which one is novel. Return a json string with the selected idea index {{'novelty': <index>}} and nothing else.""",

    # 参考配置 pointwise（原文 Prompt 5）
    "ref_pw": """You are a senior reviewer for an AI scientific conference such as ICLR, ACL, ICML. Your task is to review the novelty of the following idea and to decide whether it is novel. Focus only on the novelty and not on other aspects such as feasibility, clarity, etc.
### Idea
{idea}
Judge this idea based on the following criteria:
Novelty: The substantive originality of the idea, characterized by:
- The introduction of new frameworks, concepts, evaluations, resources or approaches absent from existing knowledge.
- The non-trivial synthesis of existing frameworks, concepts, evaluations, resources or approaches.
- The extension of established frameworks, concepts, evaluations, resources or approaches into previously unexplored problem domains.
In general, composite methods / multi-stage pipelines built from several existing motifs in haphazard manner, stringing together all kinds of common methods, are NOT to be considered novel, except if the composition is highly different than any existing work, involves substantial creativity, and the combination is highly non-trivial.
Do NOT rely on assumptions of all kinds of unknown hypotheticals. For example, "this could be novel IF formulated as..." is NOT acceptable as a reason to judge an idea as novel. Only use what is explicitly stated.
Do NOT assume a new model/training method/technical algorithmic/mathematical contribution is more novel than a new analysis, new evaluation, new task, or new resource. All types of contributions could either be novel, or not, depending on context and the state of scientific knowledge.
**Review Logic**:
* Assign **0** if the idea is not novel.
* Assign **1** if the idea is novel.
**Required Response Format**:
<thinking>
[Your reasoning here]
</thinking>
```json
{{
"novelty": <0 or 1>
}}
```""",
}

# ---------- LLM 调用 ----------
def call_chat(provider, messages, max_tokens=8192, retries=4):
    cfg = PROVIDERS[provider]
    timeout = cfg.get("timeout", 120)
    # 忠实论文（附录 B.1）：只设 max_tokens，其余参数用默认值，不设 temperature
    body = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        cfg["base_url"],
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
    )
    last_err = None
    for i in range(retries):
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
            d = json.loads(r.read().decode("utf-8"))
            msg = d["choices"][0]["message"]
            content = msg.get("content") or ""
            # 推理型模型可能把最终答案放 reasoning_content，取不到再兜底
            if not content and msg.get("reasoning_content"):
                content = msg["reasoning_content"]
            return content, d.get("usage", {})
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:200]
            last_err = f"HTTP {e.code}: {body}"
            # 429(限流) 与 5xx(服务端故障/过载) 都重试；4xx 客户端错误不重试
            if e.code == 429 or e.code >= 500:
                time.sleep(2 * (i + 1)); continue
            break
        except Exception as e:
            last_err = repr(e)
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"[{provider}] 调用失败: {last_err}")

# ---------- 解析 verdict（0 或 1） ----------
def parse_verdict(content):
    m = re.search(r'"novelty"\s*:\s*([01])', content)
    if m:
        return int(m.group(1))
    # 兜底：找最后一个出现的 0 或 1
    m = re.findall(r'\b([01])\b', content)
    if m:
        return int(m[-1])
    return None

# ---------- 对一对想法做 6 次调用并聚合（消除位置偏置） ----------
def judge_pair(provider, prompt_key, idea_a, idea_b):
    tpl = PROMPTS[prompt_key]
    a_wins = 0
    total = 0
    # 顺序 1: A 作为 Idea-0, B 作为 Idea-1
    for _ in range(3):
        content, _ = call_chat(provider, [{"role": "user", "content": tpl.format(idea0=idea_a, idea1=idea_b)}])
        v = parse_verdict(content)
        if v is not None:
            total += 1
            if v == 0:  # Idea-0 更优 = A 赢
                a_wins += 1
    # 顺序 2: B 作为 Idea-0, A 作为 Idea-1
    for _ in range(3):
        content, _ = call_chat(provider, [{"role": "user", "content": tpl.format(idea0=idea_b, idea1=idea_a)}])
        v = parse_verdict(content)
        if v is not None:
            total += 1
            if v == 1:  # Idea-1 更优 = A 赢
                a_wins += 1
    if total == 0:
        return None  # 全部无法解析
    frac = a_wins / total
    if frac > 0.5:
        return 0       # A 更优
    elif frac < 0.5:
        return 1       # B 更优
    else:
        return None    # 平局

# ---------- pointwise 判定（3 次投票取多数） ----------
def judge_pointwise(provider, prompt_key, idea):
    tpl = PROMPTS[prompt_key]
    votes = []
    for _ in range(3):
        content, _ = call_chat(provider, [{"role": "user", "content": tpl.format(idea=idea)}])
        v = parse_verdict(content)
        if v is not None:
            votes.append(v)
    if not votes:
        return None
    ones = sum(votes)
    return 1 if ones > len(votes) / 2 else 0

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="ref", choices=["ref", "P3", "P4"])
    ap.add_argument("--provider", default="deepseek", choices=list(PROVIDERS))
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 对（0=全部 154 对）")
    ap.add_argument("--setting", default="human-plus-generated", choices=["human-only", "human-plus-generated"])
    args = ap.parse_args()

    df = pd.read_parquet(f"data/{args.setting}_pairwise.parquet")
    if args.limit > 0:
        df = df.head(args.limit)

    correct = 0; tie = 0; total = 0
    for _, row in df.iterrows():
        pred = judge_pair(args.provider, args.prompt, row["idea_a"], row["idea_b"])
        expected = int(row["expected_winner"])
        if pred is None:
            tie += 1
            total += 1
        else:
            total += 1
            if pred == expected:
                correct += 1
        print(f"id={row['id']:>3}  expected={expected}  pred={pred}  "
              f"correct={correct}/{total}  tie={tie}")

    print("\n===== 汇总 =====")
    print(f"provider={args.provider}  prompt={args.prompt}  setting={args.setting}  pairs={total}")
    if total:
        print(f"strict-accuracy = {correct/total:.4f}  ({correct}/{total})   tie率 = {tie/total:.4f}")

if __name__ == "__main__":
    main()
