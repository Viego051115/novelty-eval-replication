# -*- coding: utf-8 -*-
"""
完整复刻实验矩阵（DeepSeek）
用法: python -u run_matrix.py --stage all --workers 20
      python -u run_matrix.py --stage p4b --workers 20
"""
import argparse, json, os, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from harness2 import judge_pair, judge_pointwise

LOCK = threading.Lock()

def f1(tp, fp, fn):
    p = tp/(tp+fp) if (tp+fp) else 0.0
    r = tp/(tp+fn) if (tp+fn) else 0.0
    return 2*p*r/(p+r) if (p+r) else 0.0

def metrics_pair(results, expected):
    correct = tie = total = 0
    for i, exp in enumerate(expected):
        r = results.get(i)
        total += 1
        if r is None:
            tie += 1
        elif r == int(exp):
            correct += 1
    soft = (correct + 0.5*tie)/total if total else 0
    return {"strict": correct/total if total else 0, "soft": soft,
            "correct": correct, "tie": tie, "total": total,
            "tie_rate": tie/total if total else 0}

def metrics_point(results, truth):
    pairs = [(t, results.get(i)) for i, t in enumerate(truth)]
    valid = [(t, p) for t, p in pairs if p is not None]
    if not valid:
        return None
    t = [a for a, _ in valid]; p = [b for _, b in valid]
    tp = sum(1 for a, b in zip(t, p) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(t, p) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(t, p) if a == 1 and b == 0)
    tp0 = sum(1 for a, b in zip(t, p) if a == 0 and b == 0)
    fp0 = sum(1 for a, b in zip(t, p) if a == 1 and b == 0)
    fn0 = sum(1 for a, b in zip(t, p) if a == 0 and b == 1)
    f1p, f1n = f1(tp, fp, fn), f1(tp0, fp0, fn0)
    return {"macro_f1": (f1p+f1n)/2, "f1_pos": f1p, "f1_neg": f1n,
            "unparsed": len(pairs)-len(valid), "total": len(pairs)}

def run_pairwise(provider, prompt_key, data_path, workers, aggregate=True, out_path=None):
    df = pd.read_parquet(data_path)
    rows = list(zip(df["idea_a"], df["idea_b"]))
    expected = list(df["expected_winner"])
    results = {}
    errors = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge_pair, provider, prompt_key, a, b, aggregate): i
                for i, (a, b) in enumerate(rows)}
        done = 0
        for fut in as_completed(futs):
            i = futs[fut]
            failed = False
            try:
                pred, votes = fut.result()
            except Exception as e:
                pred, votes, failed = None, [], True
                errors += 1
                if errors <= 2:
                    print(f"    ! {repr(e)[:120]}", flush=True)
            results[i] = pred
            if out_path:
                with LOCK:
                    with open(out_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"i": i, "pred": pred, "votes": votes,
                                            "expected": int(expected[i]),
                                            "failed": failed}) + "\n")
            done += 1
            if done % 200 == 0:
                print(f"      {done}/{len(rows)} (errors={errors})", flush=True)
    m = metrics_pair(results, expected)
    m.update({"secs": round(time.time()-t0), "errors": errors})
    return m

def run_pointwise(provider, prompt_key, data_path, workers, aggregate=True, out_path=None):
    df = pd.read_parquet(data_path)
    ideas = list(df["idea"])
    truth = [1 if l == "POSITIVE" else 0 for l in df["label"]]
    results = {}
    errors = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge_pointwise, provider, prompt_key, idea, aggregate): i
                for i, idea in enumerate(ideas)}
        done = 0
        for fut in as_completed(futs):
            i = futs[fut]
            failed = False
            try:
                pred, votes = fut.result()
            except Exception as e:
                pred, votes, failed = None, [], True
                errors += 1
                if errors <= 2:
                    print(f"    ! {repr(e)[:120]}", flush=True)
            results[i] = pred
            if out_path:
                with LOCK:
                    with open(out_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"i": i, "pred": pred, "votes": votes,
                                            "expected": truth[i],
                                            "failed": failed}) + "\n")
            done += 1
            if done % 200 == 0:
                print(f"      {done}/{len(ideas)} (errors={errors})", flush=True)
    m = metrics_point(results, truth)
    if m is None:
        m = {"macro_f1": None, "error": "all failed"}
    m.update({"secs": round(time.time()-t0), "errors": errors})
    return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--stage", default="all",
                    choices=["all", "p4b", "p4a", "fig12", "fig13"])
    args = ap.parse_args()

    os.makedirs("results", exist_ok=True)
    summary = []
    SETTINGS = ["human-plus-generated", "human-only"]

    def load_done(path, n):
        """已完整跑过则返回 pred 字典，否则 None"""
        if not os.path.exists(path):
            return None
        try:
            rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        except Exception:
            return None
        if len(rows) != n:
            return None
        if any(r.get("failed") for r in rows):
            return None      # 有调用失败 → 重跑
        preds = {r["i"]: r["pred"] for r in rows}
        if all(v is None for v in preds.values()):
            return None      # 全部失败 → 重跑
        return preds

    def go(name, kind, prompt, data, agg=True):
        safe = name.replace("/", "_")
        out = f"results/{args.provider}_{safe}.jsonl"
        df_len = len(pd.read_parquet(data))
        existing = load_done(out, df_len)
        if existing is not None:
            print(f"\n>>> {name} — 已完成，复用结果", flush=True)
            if kind == "pair":
                df = pd.read_parquet(data)
                m = metrics_pair(existing, list(df["expected_winner"]))
            else:
                df = pd.read_parquet(data)
                truth = [1 if l == "POSITIVE" else 0 for l in df["label"]]
                m = metrics_point(existing, truth) or {"macro_f1": None}
            m["secs"] = 0
        else:
            if os.path.exists(out):
                os.remove(out)
            print(f"\n>>> {name} | {prompt} | {os.path.basename(data)} | agg={agg}", flush=True)
            if kind == "pair":
                m = run_pairwise(args.provider, prompt, data, args.workers, agg, out)
            else:
                m = run_pointwise(args.provider, prompt, data, args.workers, agg, out)

        if kind == "pair":
            print(f"    → strict={m['strict']:.4f} soft={m['soft']:.4f} tie={m['tie_rate']:.3f} ({m['secs']}s)", flush=True)
        else:
            v = m.get("macro_f1")
            print(f"    → macroF1={'N/A' if v is None else f'{v:.4f}'} ({m['secs']}s)", flush=True)
        summary.append({"config": name, "kind": kind, "prompt": prompt,
                        "data": os.path.basename(data), "aggregate": agg, **m})

    # ---------- 图 4b：pairwise 消融 ----------
    if args.stage in ("all", "p4b"):
        for s in SETTINGS:
            for pk in ["ref", "P1", "P2", "P3", "P4", "P5"]:
                go(f"p4b/{s}/{pk}", "pair", pk, f"data/{s}_pairwise.parquet")
            go(f"p4b/{s}/noagg", "pair", "ref", f"data/{s}_pairwise.parquet", agg=False)
            go(f"p4b/{s}/plan", "pair", "ref", f"data/{s}_pairwise_plan.parquet")

    # ---------- 图 4a：pointwise 消融 ----------
    if args.stage in ("all", "p4a"):
        for s in SETTINGS:
            for pk in ["ref_pw", "P1_pw", "P2_pw"]:
                go(f"p4a/{s}/{pk}", "point", pk, f"data/{s}_pointwise.parquet")
            go(f"p4a/{s}/noagg", "point", "ref_pw", f"data/{s}_pointwise.parquet", agg=False)
            go(f"p4a/{s}/plan", "point", "ref_pw", f"data/{s}_pointwise_plan.parquet")

    # ---------- 图 12：计划格式 + prompt 变体 ----------
    if args.stage in ("all", "fig12"):
        s = "human-plus-generated"
        for pk in ["P3", "P4", "P5"]:
            go(f"fig12/{s}/{pk}_plan", "pair", pk, f"data/{s}_pairwise_plan.parquet")

    # ---------- 图 13：换 D− 生成器 ----------
    if args.stage in ("all", "fig13"):
        for g in ["gpt-5", "gpt-5.1", "gpt-5.4", "opus-4-5"]:
            go(f"fig13/{g}/pair", "pair", "ref", f"data/human-plus-generated_pairwise_backbone-{g}.parquet")
            go(f"fig13/{g}/point", "point", "ref_pw", f"data/human-plus-generated_pointwise_backbone-{g}.parquet")

    # ---------- 保存汇总 ----------
    with open(f"results/summary_{args.provider}.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n===== 完成，汇总已存 results/summary_%s.json =====" % args.provider, flush=True)

if __name__ == "__main__":
    main()
