"""Block 4.1's tutorial: read your own benchmark run back and report it honestly.

`run_benchmark.py` writes every run into `benchmark_results.json`, one record per run, newest
last. This script turns the last record for each pattern into the three numbers a report needs:
the count per difficulty tier, the spread across repeats, and one line saying what the numbers
support.

No agent, no API call, no `--with` flag. Pure arithmetic over a file you already produced:

    uv run python report_results.py

Three gaps marked `TODO`. The loading and the printing are written for you.
"""

import json
from pathlib import Path

RESULTS_PATH = Path(__file__).parent / "benchmark_results.json"
TIERS = ["easy", "medium", "hard"]


def load_latest_per_pattern() -> dict[str, dict]:
    """The newest record for each pattern. A later run of the same pattern replaces an earlier."""
    if not RESULTS_PATH.exists():
        raise SystemExit(
            f"no {RESULTS_PATH.name} here yet. Run run_benchmark.py at least once first."
        )
    latest: dict[str, dict] = {}
    for record in json.loads(RESULTS_PATH.read_text()):
        latest[record["pattern"]] = record
    return latest


def all_cases(record: dict) -> list[dict]:
    """Every graded case in the record, flattened across its repeats."""
    return [case for repeat in record["repeats"] for case in repeat["cases"]]


def count_by_tier(record: dict) -> dict[str, tuple[int, int]]:
    """Per tier, how many cases were correct and how many were run.

    This is the "counting" half of counting, repetition and spread, cut by the axis that is
    supposed to matter. If the hard tier does not look worse than the easy tier, either the
    system is genuinely robust or the tiers are not doing what they claim to.
    """
    cases = all_cases(record)
    counts = {}
    for tier in TIERS:
        in_tier = [c for c in cases if c["tier"] == tier]
        counts[tier] = (sum(1 for c in in_tier if c["correct"]), len(in_tier))
    return counts


def spread(record: dict) -> tuple[int, int]:
    """The lowest and the highest count across repeats: the range an honest report quotes."""
    counts = [repeat["n_correct"] for repeat in record["repeats"]]
    return min(counts), max(counts)


def claim(low: int, high: int, n_total: int, n_repeats: int) -> str:
    """One line saying what this range does and does not support."""
    if n_repeats == 1:
        return f"One repeat: {low} of {n_total}. One run has no spread, so it cannot show stability."
    elif low == high == n_total:
        return f"Stable across {n_repeats} repeats: {low} of {n_total} every time."
    else:
        return f"Not stable: {low} to {high} of {n_total} across repeats, so quote the range, not the best run."


def main() -> None:
    for pattern, record in load_latest_per_pattern().items():
        cases = all_cases(record)
        n_total = record["repeats"][0]["n_total"]
        n_repeats = len(record["repeats"])
        repeats_word = "repeat" if n_repeats == 1 else "repeats"
        print(f"\n=== {pattern} ({record['model']}, {n_repeats} {repeats_word}) ===")

        for tier, (correct, total) in count_by_tier(record).items():
            rate = f"{100 * correct / total:.0f}%" if total else "no cases"
            print(f"  {tier:<6} {correct:>3} / {total:<3} {rate}")

        low, high = spread(record)
        print(f"  spread across repeats: {low} to {high} of {n_total}")
        print(f"  {claim(low, high, n_total, n_repeats)}")

        cost = sum(c["cost_usd"] or 0 for c in cases)
        seconds = sum(c["wall_clock_s"] or 0 for c in cases)
        print(f"  {len(cases)} runs, ${cost:.4f}, {seconds / 60:.1f} minutes of waiting")


if __name__ == "__main__":
    main()
