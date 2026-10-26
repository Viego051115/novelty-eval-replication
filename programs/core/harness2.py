# -*- coding: utf-8 -*-
"""
完整复刻 harness —— 所有提示词 + 原始预测保存
论文: Old Ideas, Novel Problems (arXiv:2610.02022v1)
"""
from programs.paths import PROJECT_ROOT, PUBLIC_ROOT
import os, re, json, time
import urllib.request, urllib.error

# ---------- 读取 key ----------
def load_env(path=None):
    path = PROJECT_ROOT / ".env" if path is None else path
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

ENV = load_env()

PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/chat/completions",
        "key": ENV.get("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "timeout": 180,
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1/chat/completions",
        "key": ENV.get("KIMI_API_KEY", ""),
        "model": "kimi-k2.6",
        "timeout": 300,
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "key": ENV.get("GLM_API_KEY", ""),
        "model": "glm-4-flash",
        "timeout": 180,
    },
}

# ================= 提示词（原文 Prompt 4/5/7-12） =================
_REF_HEADER_PW = """You are a senior reviewer for an AI scientific conference such as ICLR, ACL, ICML. Your task is to review the novelty of the following two ideas and to decide which one is more novel. Focus only on the novelty and not on other aspects such as feasibility, clarity, etc.
### Idea-0
{idea0}
### Idea-1
{idea1}
"""

_CRITERIA = """Compare these ideas based on the following criteria:
Novelty: The substantive originality of the idea, characterized by:
- The introduction of new frameworks, concepts, evaluations, resources or approaches absent from existing knowledge.
- The non-trivial synthesis of existing frameworks, concepts, evaluations, resources or approaches.
- The extension of established frameworks, concepts, evaluations, resources or approaches into previously unexplored problem domains.
"""

_GUARDRAILS = """In general, composite methods / multi-stage pipelines built from several existing motifs in haphazard manner, stringing together all kinds of common methods, are NOT to be considered novel, except if the composition is highly different than any existing work, involves substantial creativity, and the combination is highly non-trivial.
Do NOT rely on assumptions of all kinds of unknown hypotheticals. For example, "this could be novel IF formulated as..." is NOT acceptable as a reason to judge an idea as novel. Only use what is explicitly stated.
Do NOT assume a new model/training method/technical algorithmic/mathematical contribution is more novel than a new analysis, new evaluation, new task, or new resource. All types of contributions could either be novel, or not, depending on context and the state of scientific knowledge.
"""

_TIP_PW = """**Tip**: Think about the main contributions of each idea. Which makes more novel contributions? Which makes relatively more incremental contributions?
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
```"""

_PW_LOGIC = """**Comparative Logic**:
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
```"""

_REF_HEADER_PT = """You are a senior reviewer for an AI scientific conference such as ICLR, ACL, ICML. Your task is to review the novelty of the following idea and to decide whether it is novel. Focus only on the novelty and not on other aspects such as feasibility, clarity, etc.
### Idea
{idea}
"""

_PT_LOGIC = """**Review Logic**:
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
```"""

_PT_CRITERIA = """Judge this idea based on the following criteria:
Novelty: The substantive originality of the idea, characterized by:
- The introduction of new frameworks, concepts, evaluations, resources or approaches absent from existing knowledge.
- The non-trivial synthesis of existing frameworks, concepts, evaluations, resources or approaches.
- The extension of established frameworks, concepts, evaluations, resources or approaches into previously unexplored problem domains.
"""

PROMPTS = {
    # ---- pairwise ----
    "ref":    _REF_HEADER_PW + _CRITERIA + _GUARDRAILS + _TIP_PW,          # Prompt 4
    "P1":     _REF_HEADER_PW + _CRITERIA + _TIP_PW,                        # 去护栏
    "P2":     _REF_HEADER_PW + _PW_LOGIC,                                  # 删判据 (Prompt 8)
    "P3": """You are a reviewer specialized in Artificial intelligence and Machine Learning research. You are given two ideas. One of them is judged as novel by reviewers for a top AI conference (like ICLR or ACL) reviewers and the other one is not. Your task is to identify the one that is judged as novel.
The two ideas are:
paper 0: {idea0}
paper 1: {idea1}
Now decide which one is judged as novel. Return a json string with the selected idea index {{'novelty': <index>}} and nothing else.""",
    "P4": """You are a reviewer specialized in Artificial intelligence and Machine Learning research. You are given two ideas. Your task is to identify the one that is novel.
The two ideas are:
paper 0: {idea0}
paper 1: {idea1}
Now decide which one is novel. Return a json string with the selected idea index {{'novelty': <index>}} and nothing else.""",
    "P5": """You are a reviewer specialized in Artificial intelligence and Machine Learning research. You are given two ideas. One of them is judged as more novel than the other by reviewers for a top AI conference (like ICLR or ACL). Your task is to identify the idea that is judged as more novel.
The two ideas are:
paper 0: {idea0}
paper 1: {idea1}
Now decide which one is judged as more novel. Return a json string with the selected idea index {{'novelty': <index>}} and nothing else.""",
    # ---- pointwise ----
    "ref_pw": _REF_HEADER_PT + _PT_CRITERIA + _GUARDRAILS + _PT_LOGIC,    # Prompt 5
    "P1_pw":  _REF_HEADER_PT + _PT_CRITERIA + _PT_LOGIC,                   # 去护栏
    "P2_pw":  _REF_HEADER_PT + _PT_LOGIC,                                  # 删判据 (Prompt 9)
}

# ================= 调用 =================
def call_chat(provider, messages, max_tokens=8192, retries=8):
    cfg = PROVIDERS[provider]
    body = {"model": cfg["model"], "messages": messages, "max_tokens": max_tokens}
    req = urllib.request.Request(
        cfg["base_url"], data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
    )
    last = None
    for i in range(retries):
        try:
            r = urllib.request.urlopen(req, timeout=cfg["timeout"])
            d = json.loads(r.read().decode("utf-8"))
            msg = d["choices"][0]["message"]
            content = msg.get("content") or ""
            if not content and msg.get("reasoning_content"):
                content = msg["reasoning_content"]
            return content, d.get("usage", {})
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode("utf-8", "ignore")[:200]
            last = f"HTTP {e.code}: {body_txt}"
            if e.code == 429 or e.code >= 500:
                time.sleep(3 * (i + 1)); continue   # 限流/服务端故障：指数退避
            break
        except Exception as e:
            last = repr(e)
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"[{provider}] {last}")

def parse_verdict(content):
    m = re.search(r'"novelty"\s*:\s*([01])', content)
    if m:
        return int(m.group(1))
    m = re.findall(r'\b([01])\b', content)
    return int(m[-1]) if m else None

# ================= 判定（含聚合开关） =================
def judge_pair(provider, prompt_key, idea_a, idea_b, aggregate=True):
    """返回 (verdict, votes)。verdict: 0=A更优, 1=B更优, None=平局/无法解析"""
    tpl = PROMPTS[prompt_key]
    n_per_dir = 3 if aggregate else 1
    a_wins = total = 0
    votes = []
    for _ in range(n_per_dir):
        c, _u = call_chat(provider, [{"role": "user", "content": tpl.format(idea0=idea_a, idea1=idea_b)}])
        v = parse_verdict(c)
        votes.append(v)
        if v is not None:
            total += 1
            if v == 0:
                a_wins += 1
    for _ in range(n_per_dir):
        c, _u = call_chat(provider, [{"role": "user", "content": tpl.format(idea0=idea_b, idea1=idea_a)}])
        v = parse_verdict(c)
        votes.append(v)
        if v is not None:
            total += 1
            if v == 1:
                a_wins += 1
    if total == 0:
        return None, votes
    frac = a_wins / total
    if frac > 0.5: return 0, votes
    if frac < 0.5: return 1, votes
    return None, votes

def judge_pointwise(provider, prompt_key, idea, aggregate=True):
    """返回 (verdict, votes)"""
    tpl = PROMPTS[prompt_key]
    n = 3 if aggregate else 1
    votes = []
    for _ in range(n):
        c, _u = call_chat(provider, [{"role": "user", "content": tpl.format(idea=idea)}])
        votes.append(parse_verdict(c))
    valid = [v for v in votes if v is not None]
    if not valid:
        return None, votes
    return (1 if sum(valid) > len(valid) / 2 else 0), votes
