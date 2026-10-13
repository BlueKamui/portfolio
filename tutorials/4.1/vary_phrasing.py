"""Block 4.1's tutorial: does the wording change the answer?

One fixed sum. Five ways of asking for it. Several runs of each. The sum never changes, so the
only thing varying is the wording, and wording is the "should not matter" axis: if the count
moves when you rephrase, the effect you found belongs to your prompt, not to the system.

This script is shipped with four gaps marked `TODO`. Filling them is the exercise. Everything
around them is written for you: the call into the agent, the printing, the saved JSON.

Before anything is sent to the model, the script tests all four gaps on known inputs and stops
with a message naming every gap that is still open or still wrong. No call is made until all four
pass.

Run it once the gaps are filled:

    uv run --with claude-agent-sdk python vary_phrasing.py
    uv run --with claude-agent-sdk python vary_phrasing.py --repeats 6

The results file is written again after every run, so a run that stops part-way keeps every run
that finished.

Needs `run_benchmark.py`, `benchmark_cases.py` and `toy_agent.py` in the same folder.
"""

import argparse
import asyncio
import json
from decimal import Decimal
from pathlib import Path

from claude_agent_sdk import ResultMessage, query

from run_benchmark import grade, single_shot_options

# One fixed case, from `benchmark_cases.py`'s hard tier. Two 17-digit integers.
A = "48213756123456789"
B = "91847329876543210"
TRUE_SUM = "140061085999999999"

# Every prompt ends with this, so a script can read the answer back without judging it.
ANSWER_SUFFIX = " State your final numeric answer on its own line as: ANSWER: <number>"

# TODO 1: four more ways of asking for the same sum. Keep `{a}` and `{b}` as the placeholders,
# keep the numbers out of the wording, and make them genuinely different in style: a question, an
# instruction, a bare equation, a word problem. `benchmark_cases.py`'s own PHRASINGS list is a
# fair place to look, but write your own rather than copying all five.
PHRASINGS = [
    "What is {a} plus {b}?",                                  # a question (given)
    "Please calculate the sum of {a} and {b}.",               # an instruction
    "{a} + {b} = ?",                                          # a bare equation
    "I need the total when {a} is added to {b}.",             # a request in plain speech
    "A shop sold {a} items in its first year and {b} items in its second. "
    "How many items did it sell in total?",                   # a word problem
]

MODEL = "claude-haiku-4-5"

# In this course's own repository this path is block 4.1's figure source. On your machine that
# folder does not exist, so the file lands beside this script instead, and the script says where.
_REPO_OUT = (
    Path(__file__).parent.parent.parent
    / "4.1-planning-composition-and-measurement" / "figures" / "vary-phrasing.json"
)
OUT_PATH = _REPO_OUT if _REPO_OUT.parent.is_dir() else Path(__file__).parent / "vary-phrasing.json"


async def ask(question: str, model: str) -> str | None:
    """One single-shot call: no tools, no loop. Returns the model's final text."""
    summary = None
    async for message in query(prompt=question, options=single_shot_options(model)):
        if isinstance(message, ResultMessage):
            summary = message
    return summary.result if summary else None


def is_correct(answer: str | None) -> bool:
    """Decides whether one run was correct. `answer` is the model's whole reply, or None if
    nothing came back."""
    # TODO 2: `grade()` is imported at the top of this file. Read its signature in
    # `run_benchmark.py`, call it with the right two arguments, and return what it gives back,
    # True or False. Replace the line below.
    return grade(TRUE_SUM, answer)


def save(results: dict[str, list[bool]], model: str, repeats: int,
         summary: dict | None = None) -> None:
    """Write every run so far to OUT_PATH. Called after each run, so nothing finished is lost."""
    record = {"a": A, "b": B, "true_sum": TRUE_SUM, "model": model, "repeats": repeats,
              "finished": summary is not None, "results": results}
    if summary:
        record.update(summary)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=2))


async def run_phrasing(template: str, repeats: int, model: str,
                       results: dict[str, list[bool]]) -> None:
    """Ask the same sum, in one wording, `repeats` times. Adds one verdict per run to
    `results[template]`, and saves after every run."""
    question = template.format(a=A, b=B) + ANSWER_SUFFIX
    results[template] = []
    for i in range(1, repeats + 1):
        answer = await ask(question, model)
        correct = is_correct(answer)
        print(f"    run {i}/{repeats}: correct={correct}", flush=True)
        results[template].append(correct)
        save(results, model, repeats)


def count_and_range(results: dict[str, list[bool]]) -> tuple[dict[str, int], int, int]:
    """Counting, repetition and spread, on the phrasing axis.

    Returns the count of correct runs per phrasing, plus the lowest and the highest of those
    counts. The pair is the range: the two numbers an honest report quotes.
    """
    # TODO 3: fill both lines. `counts` maps each phrasing to how many of its runs were correct.
    # `low` and `high` are the smallest and the largest of those counts.
    counts: dict[str, int] = {template: sum(verdicts) for template, verdicts in results.items()}
    low, high = min(counts.values()), max(counts.values())
    return counts, low, high


def verdict(low: int, high: int, repeats: int) -> str:
    """One line saying what these numbers do and do not support.

    Phrasing is the axis that should not matter, so the question is whether the counts moved by
    more than sampling noise would explain.
    """
    # TODO 4: return one of the two sentences below, choosing with a single `if` on `low` and
    # `high`. Treat a gap of one run or less as "no visible effect". Think about why the honest
    # wording is "no visible effect" rather than "no effect".
    #
    #   f"Phrasing shows no visible effect: every wording landed within one run ({low} to {high} of {repeats})."
    #   f"Phrasing may be doing something: {low} to {high} of {repeats} is a wide gap on this few runs. Run more repeats."
    if high - low <= 1:
        return f"Phrasing shows no visible effect: every wording landed within one run ({low} to {high} of {repeats})."
    return f"Phrasing may be doing something: {low} to {high} of {repeats} is a wide gap on this few runs. Run more repeats."


def check_todos() -> None:
    """Tests every gap on known inputs before any model call, and names what is still open."""
    problems = []
    if Decimal(A) + Decimal(B) != Decimal(TRUE_SUM):
        problems.append("TRUE_SUM is not A plus B. If you changed the sum, change all three.")

    if len(PHRASINGS) < 5:
        problems.append(f"TODO 1: PHRASINGS needs five wordings, and has {len(PHRASINGS)}")
    if len(set(PHRASINGS)) < len(PHRASINGS):
        problems.append("TODO 1: two wordings in PHRASINGS are the same")
    for template in PHRASINGS:
        try:
            question = template.format(a=A, b=B)
        except (KeyError, IndexError, ValueError) as exc:
            problems.append(f"TODO 1: {template!r} has a placeholder other than {{a}} and {{b}} "
                            f"({exc!r})")
            continue
        if A not in question or B not in question:
            problems.append(f"TODO 1: {template!r} needs both {{a}} and {{b}}")

    # Two made-up replies: one with the right sum, one that is out by one.
    right = f"Adding column by column.\nANSWER: {TRUE_SUM}"
    wrong = f"Adding column by column.\nANSWER: {Decimal(TRUE_SUM) + 1}"
    try:
        if not is_correct(right):
            problems.append("TODO 2: is_correct() marked a right answer as wrong "
                            "(is it still `return False`?)")
        if is_correct(wrong):
            problems.append("TODO 2: is_correct() marked a wrong answer as right")
    except Exception as exc:
        problems.append(f"TODO 2: is_correct() crashed on a test reply: {exc!r}. Read grade()'s "
                        "signature in run_benchmark.py again, including the order of its arguments")

    try:
        counts, low, high = count_and_range(
            {"first": [True, True, False, True], "second": [False, True, False, False]})
        if counts != {"first": 3, "second": 1} or (low, high) != (1, 3):
            problems.append("TODO 3: for 3 of 4 and 1 of 4, count_and_range() should give counts "
                            f"of 3 and 1, low 1 and high 3. It gave {counts}, {low}, {high}")
    except Exception as exc:
        problems.append(f"TODO 3: count_and_range() crashed on a test input: {exc!r}")

    try:
        close, wide = verdict(3, 4, 4).lower(), verdict(2, 4, 4).lower()
        if "no visible effect" not in close or not wide or "no visible effect" in wide:
            problems.append("TODO 4: verdict() should say 'no visible effect' for 3 to 4 of 4, "
                            "and the other sentence for 2 to 4 of 4")
    except Exception as exc:
        problems.append(f"TODO 4: verdict() crashed on a test input: {exc!r}")

    if problems:
        raise SystemExit("Still to fill in or fix, before any call to the model:\n  "
                         + "\n  ".join(problems))


async def main() -> None:
    parser = argparse.ArgumentParser(description="One sum, five wordings, several runs each.")
    parser.add_argument("--repeats", type=int, default=4, help="runs per phrasing")
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()

    check_todos()

    results: dict[str, list[bool]] = {}
    try:
        for n, template in enumerate(PHRASINGS, 1):
            print(f"  phrasing {n}/{len(PHRASINGS)}: {template}", flush=True)
            await run_phrasing(template, args.repeats, args.model, results)
    except Exception as exc:
        finished = sum(len(verdicts) for verdicts in results.values())
        message = [f"\nStopped part-way by an error: {exc!r}"]
        if finished:
            message.append(f"The {finished} finished runs are saved in {OUT_PATH}.")
        message.append("Run it again, or lower --repeats while you find the cause.")
        raise SystemExit("\n".join(message))

    counts, low, high = count_and_range(results)
    print("\n--- counts per phrasing ---")
    for template, count in counts.items():
        print(f"  {count}/{args.repeats}  {template}")
    print(f"\nrange across wordings: {low} to {high} of {args.repeats}")
    print(verdict(low, high, args.repeats))

    save(results, args.model, args.repeats, {"counts": counts, "low": low, "high": high})
    print(f"saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
