"""Block 4.1 extension: add one axis to vary_phrasing.py. Here the axis is DIGIT COUNT.

Wording is the axis that should not matter. Difficulty is the axis that should. This keeps one
wording fixed and changes only how many digits each addend has, so the count should fall as the
digits grow. If it does not, the benchmark's tiers are not measuring difficulty.

PREDICTION (written before any run, see prediction.txt):
  3 and 8 digits: 4/4 each. 17 digits: 2 to 4 of 4. 26 digits: 0 to 2 of 4.
  Digit count will matter, wording did not.

Run:  uv run --with claude-agent-sdk python vary_digits.py [--repeats 4]
Written by Claude from vary_phrasing.py's structure; the prediction is Youssef's to confirm or edit.
"""

import argparse
import asyncio
import json
import random
from decimal import Decimal
from pathlib import Path

from vary_phrasing import ANSWER_SUFFIX, MODEL, ask
from run_benchmark import grade

DIGIT_COUNTS = [3, 8, 17, 26]
TEMPLATE = "What is {a} plus {b}?"
OUT_PATH = Path(__file__).parent / "vary-digits.json"


def make_pair(n_digits: int) -> tuple[str, str, str]:
    """A fixed (seeded) pair of n-digit integers and their exact sum."""
    rng = random.Random(n_digits)
    a = str(rng.randint(10 ** (n_digits - 1), 10 ** n_digits - 1))
    b = str(rng.randint(10 ** (n_digits - 1), 10 ** n_digits - 1))
    return a, b, str(Decimal(a) + Decimal(b))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()

    results: dict[int, list[bool]] = {}
    for n in DIGIT_COUNTS:
        a, b, true_sum = make_pair(n)
        print(f"  {n} digits: {a} + {b}", flush=True)
        results[n] = []
        for i in range(1, args.repeats + 1):
            answer = await ask(TEMPLATE.format(a=a, b=b) + ANSWER_SUFFIX, args.model)
            ok = grade(true_sum, answer)
            print(f"    run {i}/{args.repeats}: correct={ok}", flush=True)
            results[n].append(ok)
            OUT_PATH.write_text(json.dumps({"model": args.model, "repeats": args.repeats,
                                            "results": results}, indent=2))

    counts = {n: sum(v) for n, v in results.items()}
    print("\n--- counts per digit count ---")
    for n, c in counts.items():
        print(f"  {c}/{args.repeats}  {n} digits")
    low, high = min(counts.values()), max(counts.values())
    if counts[DIGIT_COUNTS[0]] - counts[DIGIT_COUNTS[-1]] >= 2:
        print(f"\nDigit count shows a visible effect: {low} to {high} of {args.repeats}, "
              "falling as digits grow. Unlike wording, difficulty moves the count.")
    else:
        print(f"\nDigit count shows no visible effect ({low} to {high} of {args.repeats}). "
              "Either the model is robust here or the tiers are not measuring difficulty.")
    print(f"saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
