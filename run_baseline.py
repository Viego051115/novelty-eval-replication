# -*- coding: utf-8 -*-
"""参考配置基线：pointwise(宏F1) + pairwise(strict-accuracy)，两个设定。"""
import argparse, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from harness import judge_pair, judge_pointwise

def _f1(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * p * r / (p + r) if (p + r) else 0.0

def macro_f1(truth, pred):
    tp = sum(1 for t, p in zip(truth, pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(truth, pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(truth, pred) if t == 1 and p == 0)
    f1_pos = _f1(tp, fp, fn)
    tp0 = sum(1 for t, p in zip(truth, pred) if t == 0 and p == 0)
    fp0 = sum(1 for t, p in zip(truth, pred) if t == 1 and p == 0)
    fn0 = sum(1 for t, p in zip(truth, pred) if t == 0 and p == 1)
    f1_neg = _f1(tp0, fp0, fn0)
    return (f1_pos + f1_neg) / 2, f1_pos, f1_neg

def run_pointwise(provider, df, workers=16):
    rows = list(zip(df["idea"], df["label"]))
    results = {}
    errors = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge_pointwise, provider, "ref_pw", idea): i for i, (idea, _) in enumerate(rows)}
        done = 0
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = None
                errors += 1
                if errors <= 3:
                    print(f"    ! 出错: {repr(e)[:180]}")
            done += 1
            if done % 50 == 0:
                print(f"    pointwise {done}/{len(rows)}  (错误={errors})")
    truth = [1 if lbl == "POSITIVE" else 0 for _, lbl in rows]
    pred = [results.get(i) for i in range(len(rows))]
    valid = [(t, p) for t, p in zip(truth, pred) if p is not None]
    if not valid:
        return None
    t = [a for a, _ in valid]; p = [b for _, b in valid]
    m, f1p, f1n = macro_f1(t, p)
    return m, f1p, f1n, len(rows) - len(valid)

def run_pairwise(provider, df, workers=16):
    rows = list(zip(df["idea_a"], df["idea_b"]))
    results = {}
    errors = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge_pair, provider, "ref", a, b): i for i, (a, b) in enumerate(rows)}
        done = 0
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = None
                errors += 1
                if errors <= 3:
                    print(f"    ! 出错: {repr(e)[:180]}")
            done += 1
            if done % 30 == 0:
                print(f"    pairwise {done}/{len(rows)}  (错误={errors})")
    correct = tie = total = 0
    for i, exp in enumerate(df["expected_winner"]):
        pred = results.get(i)
        total += 1
        if pred is None:
            tie += 1
        elif pred == int(exp):
            correct += 1
    return correct / total, tie, total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--settings", default="human-plus-generated,human-only")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0, help="每个设定只跑前 N 条（0=全部）")
    args = ap.parse_args()

    print(f"provider={args.provider}  settings={args.settings}  workers={args.workers}  limit={args.limit or '全部'}\n")
    print("=" * 60)
    for setting in args.settings.split(","):
        setting = setting.strip()
        # pointwise
        df_pw = pd.read_parquet(f"data/{setting}_pointwise.parquet")
        if args.limit:
            # 采样：保证正负类各占一半
            pos = df_pw[df_pw["label"] == "POSITIVE"].head(args.limit // 2)
            neg = df_pw[df_pw["label"] == "NEGATIVE"].head(args.limit // 2)
            df_pw = pd.concat([pos, neg])
        t0 = time.time()
        r = run_pointwise(args.provider, df_pw, args.workers)
        if r:
            m, f1p, f1n, miss = r
            print(f"[{setting}] pointwise  macro-F1={m:.4f}  (novel={f1p:.4f} / not={f1n:.4f})  未解析={miss}  ({time.time()-t0:.0f}s)")
        # pairwise
        df_pr = pd.read_parquet(f"data/{setting}_pairwise.parquet")
        if args.limit:
            df_pr = df_pr.head(args.limit // 2)
        t0 = time.time()
        acc, tie, total = run_pairwise(args.provider, df_pr, args.workers)
        print(f"[{setting}] pairwise  strict-acc={acc:.4f}  ({int(acc*total)}/{total})  平局={tie}  ({time.time()-t0:.0f}s)")
        print("-" * 60)

if __name__ == "__main__":
    main()
