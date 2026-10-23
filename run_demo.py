# -*- coding: utf-8 -*-
"""并行跑 ref / P3 / P4 三个 prompt，输出 strict-accuracy 对比表。"""
import argparse, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from harness import PROMPTS, judge_pair

def run_prompt(provider, prompt_key, df, workers=16):
    rows = list(zip(df["idea_a"], df["idea_b"]))
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge_pair, provider, prompt_key, a, b): i for i, (a, b) in enumerate(rows)}
        done = 0
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = None
                print(f"  pair {i} 出错: {repr(e)[:100]}")
            done += 1
            if done % 25 == 0:
                print(f"  [{prompt_key}] {done}/{len(rows)} 对完成")
    correct = tie = total = 0
    for i, exp in enumerate(df["expected_winner"]):
        pred = results.get(i)
        total += 1
        if pred is None:
            tie += 1
        elif pred == int(exp):
            correct += 1
    return correct, tie, total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--prompts", default="ref,P3,P4")
    ap.add_argument("--limit", type=int, default=0, help="0=全部 154 对")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--setting", default="human-plus-generated")
    args = ap.parse_args()

    df = pd.read_parquet(f"data/{args.setting}_pairwise.parquet")
    if args.limit:
        df = df.head(args.limit)
    print(f"provider={args.provider}  pairs={len(df)}  prompts={args.prompts}  workers={args.workers}\n")

    summary = {}
    for pk in args.prompts.split(","):
        t0 = time.time()
        c, tie, total = run_prompt(args.provider, pk.strip(), df, args.workers)
        acc = c / total if total else 0
        summary[pk.strip()] = (acc, c, total, tie)
        print(f"=== {pk.strip():4s}  strict-accuracy = {acc:.4f}  ({c}/{total})  平局 {tie}  ({time.time()-t0:.0f}s) ===\n")

    print("\n===== 汇总对比 =====")
    print("prompt\tstrict-accuracy")
    for k, (acc, c, total, tie) in summary.items():
        print(f"{k}\t{acc:.4f}\t({c}/{total}, tie={tie})")

if __name__ == "__main__":
    main()
