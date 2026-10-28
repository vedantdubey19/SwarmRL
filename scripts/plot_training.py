#!/usr/bin/env python3
import argparse
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def plot_or_summarize(summary_file: str) -> None:
    if not os.path.exists(summary_file):
        print(f"Summary file not found: {summary_file}")
        return

    records = []
    with open(summary_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    if not records:
        print("No training records found in summary file.")
        return

    print("=== Training Progress Summary ===")
    print(f"{'Iter':<6} | {'Reward':<12} | {'EpLen':<8} | {'Collisions/1k':<14} | {'Explored %':<10} | {'Throughput':<12}")
    print("-" * 75)
    for r in records:
        it = r.get("iteration", 0)
        rew = r.get("episode_reward_mean", 0.0)
        l = r.get("episode_len_mean", 0.0)
        col = r.get("collisions_per_1000", 0.0)
        exp = r.get("explored_fraction", 0.0) * 100.0
        tp = r.get("throughput_steps_per_sec", 0.0)
        print(f"{it:<6d} | {rew:<12.2f} | {l:<8.1f} | {col:<14.2f} | {exp:<9.1f}% | {tp:<10.1f} s/s")


def main():
    parser = argparse.ArgumentParser(description="Summarize SwarmRL Training Run")
    parser.add_argument(
        "--file",
        type=str,
        default=os.path.join(REPO_ROOT, "runs", "training_summary.jsonl"),
        help="Path to training summary JSONL file",
    )
    args = parser.parse_args()
    plot_or_summarize(args.file)


if __name__ == "__main__":
    main()
