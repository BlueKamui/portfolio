"""Block 4.2's real benchmark: run `benchmark_cases.py`'s twenty cases under two of block 4.1's
loop patterns, single-shot and tool loop, and grade every real answer.

**Single-shot** (block 4.1's pattern 1): no tools at all, `tools=[]`, `mcp_servers={}`. The model
answers directly from its own text generation, one pass, no loop.

**Tool loop** (block 4.1's pattern 2, the same pattern block 3.1 already built): the toy agent's
own `add` tool, via `toy_agent.build_options()`. Reasoning and acting, interleaved, until the model
stops. This block does not build a third pattern: it measures two that already exist.

Both patterns get the exact same question text, including the exact same phrasing across all
twenty cases (see `benchmark_cases.py`), so the only thing that differs between a "single-shot"
run and a "tool-loop" run of the same case is whether the `add` tool is available. Grading a tool
call by the same yardstick as a raw text answer is itself a design decision worth naming: see the
deck's "What the numbers do not show" section.

Grading is exact numeric match against `benchmark_cases.py`'s own `Decimal` ground truth, read off
a fixed convention ("ANSWER: <number>") every prompt asks for. This is deliberately a simple,
gradeable measure, not an LLM-as-judge: Subelement 3's own brief states a simple, well-chosen
measure is fine, and grading two-number addition needs no judgement at all, only arithmetic.

Run it (results append to `benchmark_results.json` in this folder):

    uv run --with claude-agent-sdk python run_benchmark.py --pattern single-shot --repeats 3
    uv run --with claude-agent-sdk python run_benchmark.py --pattern tool-loop --repeats 3

`--extra-cases` also runs whatever is in `extra_cases.py`, which is block 4.1's tutorial
exercise: three cases the student writes to a specification. `report_results.py`, in this same
folder, reads `benchmark_results.json` back and reports the counts, the tiers and the spread.

Each repeat runs all twenty cases once, in order. Repeating the whole set, rather than one case
twenty times, combines two techniques block 4.1 teaches:
systematic variation (twenty different cases, varying phrasing and difficulty) and counting,
repetition and spread (running the same set more than once to see whether the success rate itself
is stable or noisy). `repetition_demo.py`, in this same folder, is the other half: one fixed case,
run twenty times, block 4.1's own real number for "run a task twenty times."
"""

import argparse
import asyncio
import json
import re
import time
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from benchmark_cases import EXACT_DIGITS, build_cases
from toy_agent import build_options

RESULTS_PATH = Path(__file__).parent / "benchmark_results.json"

# Strip invisible Unicode that showed up in one real run at extreme digit counts (a zero-width
# space inside a long number), before any number-matching regex runs.
_INVISIBLE = ["​", "‌", "‍", "﻿"]


def extract_answer(text: str | None) -> Decimal | None:
    """Read the number after 'ANSWER:', or fall back to the last number-like token in the
    text if the model did not follow the convention exactly. Real runs occasionally wrap the
    number in markdown bold (**42**) or add thousands separators (1,000,000): both are stripped
    before matching."""
    if not text:
        return None
    for ch in _INVISIBLE:
        text = text.replace(ch, "")
    text = text.replace(",", "").replace("*", "")
    answer_match = re.search(r"ANSWER:\s*(-?\d+\.?\d*)", text)
    candidates = [answer_match.group(1)] if answer_match else re.findall(r"-?\d+\.?\d*", text)
    if not candidates:
        return None
    try:
        return Decimal(candidates[-1])
    except InvalidOperation:
        return None


def grade(true_sum: str, model_answer: str | None, tolerance: Decimal = Decimal("0.01")) -> bool:
    got = extract_answer(model_answer)
    if got is None:
        return False
    # Room for long numbers: the default of 28 significant digits would round the subtraction.
    with localcontext() as ctx:
        ctx.prec = EXACT_DIGITS
        return abs(got - Decimal(true_sum)) <= tolerance


def single_shot_options(model: str | None) -> ClaudeAgentOptions:
    """Block 4.1's pattern 1: no tools, no loop, one prompt, one answer."""
    return ClaudeAgentOptions(
        tools=[], mcp_servers={}, allowed_tools=[], setting_sources=[], model=model,
    )


async def run_one(case: dict, pattern: str, model: str) -> dict:
    options = (
        single_shot_options(model) if pattern == "single-shot" else build_options(model)
    )
    summary = None
    t0 = time.time()
    async for message in query(prompt=case["question"], options=options):
        if isinstance(message, ResultMessage):
            summary = message
    wall_clock = time.time() - t0
    if summary is None:
        return {
            "case_id": case["id"], "tier": case["tier"], "correct": False, "answer": None,
            "cost_usd": None, "input_tokens": None, "output_tokens": None,
            "wall_clock_s": wall_clock, "error": "no ResultMessage",
        }
    correct = grade(case["true_sum"], summary.result)
    return {
        "case_id": case["id"],
        "tier": case["tier"],
        "true_sum": case["true_sum"],
        "answer": summary.result,
        "correct": correct,
        "cost_usd": summary.total_cost_usd,
        "input_tokens": summary.usage.get("input_tokens"),
        "output_tokens": summary.usage.get("output_tokens"),
        "wall_clock_s": round(wall_clock, 2),
    }


async def run_repeat(cases: list[dict], pattern: str, model: str, repeat_index: int) -> dict:
    results = []
    for case in cases:
        result = await run_one(case, pattern, model)
        print(
            f"  [{pattern} repeat {repeat_index}] case {case['id']:>2} ({case['tier']:<6}) "
            f"correct={result['correct']} wall={result['wall_clock_s']}s",
            flush=True,
        )
        results.append(result)
    n_correct = sum(r["correct"] for r in results)
    total_cost = sum(r["cost_usd"] or 0 for r in results)
    return {
        "repeat_index": repeat_index,
        "n_correct": n_correct,
        "n_total": len(results),
        "total_cost_usd": round(total_cost, 6),
        "cases": results,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the toy agent's 20-case benchmark.")
    parser.add_argument("--pattern", choices=["single-shot", "tool-loop"], required=True)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--extra-cases",
        action="store_true",
        help="also run the cases in extra_cases.py, block 4.1's tutorial exercise",
    )
    args = parser.parse_args()

    cases = build_cases()
    if args.extra_cases:
        # Imported here, not at the top of the file, so this script still runs in a folder that
        # has no extra_cases.py in it.
        from extra_cases import build_extra_cases

        extra = build_extra_cases()
        if not extra:
            raise SystemExit("extra_cases.py has no cases in it yet: TODO 1 is not done.")
        print(f"--- adding {len(extra)} case(s) from extra_cases.py ---", flush=True)
        cases = cases + extra
    repeats = []
    for r in range(1, args.repeats + 1):
        print(f"--- {args.pattern}, repeat {r}/{args.repeats} ---", flush=True)
        repeats.append(await run_repeat(cases, args.pattern, args.model, r))

    record = {
        "pattern": args.pattern,
        "model": args.model,
        "extra_cases": args.extra_cases,
        "repeats": repeats,
    }

    existing = []
    if RESULTS_PATH.exists():
        existing = json.loads(RESULTS_PATH.read_text())
    existing.append(record)
    RESULTS_PATH.write_text(json.dumps(existing, indent=2))
    print(f"\nsaved to {RESULTS_PATH}")

    counts = [r["n_correct"] for r in repeats]
    print(f"\n{args.pattern}: successes per repeat = {counts} (out of {len(cases)} each)")


if __name__ == "__main__":
    asyncio.run(main())
