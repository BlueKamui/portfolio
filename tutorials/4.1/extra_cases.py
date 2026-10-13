"""Block 4.1's tutorial: three benchmark cases of your own, written to a specification.

`benchmark_cases.py` has twenty cases somebody else wrote. This file is where you write three, to
a spec, and then run the real benchmark over yours as well as theirs:

    uv run --with claude-agent-sdk python run_benchmark.py --pattern tool-loop --extra-cases --repeats 1

Three gaps marked `TODO`. The specification each case has to meet is right above the first one.
Before anything is sent to the model, `check_todos()` tests your question text and your true sums,
and stops with a message naming every one still open or wrong.

Nothing here invents a new measure: a case is only usable if its true answer can be computed
exactly, in one line, without judgement. That is what makes the grading script possible.
"""

from decimal import Decimal, localcontext

from benchmark_cases import ANSWER_SUFFIX, EXACT_DIGITS, PHRASINGS

# The specification your three cases have to meet.
#
#   Case A, tier "easy":   two integers, 2 or 3 digits each. Nothing should ever get this wrong.
#   Case B, tier "medium": two numbers with decimal places, at least two each, and a different
#                          number of decimal places between the two, so lining them up matters.
#   Case C, tier "hard":   two integers of at least 20 digits each. A float holds every whole
#                          number exactly only up to 2**53, a 16-digit number, so this case is the
#                          one that will show you something about the tool rather than the model.
#
# Write the numbers as strings, never as Python numbers: `0.1 + 0.2` in Python is
# 0.30000000000000004, and a ground truth computed that way is wrong before the agent runs.

# TODO 1: three cases, as (a, b, tier) string triples, matching the spec above.
RAW_EXTRA_CASES: list[tuple[str, str, str]] = [
    ("372", "58", "easy"),                                          # 3 digits + 2 digits
    ("245.67", "18.325", "medium"),                                 # 2 and 3 decimal places
    ("73920184756102938475", "26184093827561049283", "hard"),       # 20 digits each
]


def build_extra_cases() -> list[dict]:
    """Turn each raw case into the dict `run_benchmark.py` already knows how to run.

    Case ids start at 100, so your cases never collide with the twenty in `benchmark_cases.py`.
    """
    cases = []
    for i, (a, b, tier) in enumerate(RAW_EXTRA_CASES):
        # TODO 2: build the prompt. Pick one of `PHRASINGS` (it is a list of templates with `{a}`
        # and `{b}` in them), fill in this case's own numbers, and add `ANSWER_SUFFIX` on the end.
        # Without the suffix the grading script has no convention to read the answer off.
        question = PHRASINGS[i % len(PHRASINGS)].format(a=a, b=b) + ANSWER_SUFFIX

        # TODO 3: the exact ground truth for this case. One line, using `Decimal`, never `float`.
        # `benchmark_cases.py`'s own `build_cases()` does the same thing: read it if you are stuck.
        # Keep your line inside the `with` block: it gives `Decimal` room for 100 digits, where the
        # default of 28 would round the sum of two long numbers.
        with localcontext() as ctx:
            ctx.prec = EXACT_DIGITS
            true_sum = Decimal(a) + Decimal(b)

        cases.append(
            {
                "id": 100 + i,
                "a": a,
                "b": b,
                "tier": tier,
                "phrasing_index": None,
                "question": question,
                "true_sum": str(true_sum),
            }
        )
    check_todos(cases)
    return cases


def check_todos(cases: list[dict]) -> None:
    """Tests TODO 2 and TODO 3 on your own cases before any model call, and names what is still
    open or wrong. Without this, an empty question would be sent to the model and graded against 0."""
    problems = []
    for case in cases:
        a, b, question = str(case["a"]), str(case["b"]), case["question"]
        if ANSWER_SUFFIX not in question or a not in question or b not in question:
            problems.append(f"TODO 2: the question for {a} + {b} needs both numbers and "
                            "ANSWER_SUFFIX")
        with localcontext() as ctx:
            ctx.prec = EXACT_DIGITS
            exact = Decimal(a) + Decimal(b)
        if Decimal(case["true_sum"]) != exact:
            problems.append(f"TODO 3: the true sum for {a} + {b} is {case['true_sum']}, "
                            "which is not exactly a plus b")
    if problems:
        raise SystemExit("Still to fill in or fix, before any call to the model:\n  "
                         + "\n  ".join(problems))


if __name__ == "__main__":
    built = build_extra_cases()
    if not built:
        raise SystemExit("TODO 1 is not done yet: RAW_EXTRA_CASES is empty.")
    for case in built:
        print(f"[{case['tier']:<6}] {case['question']}")
        print(f"         true sum: {case['true_sum']}\n")
