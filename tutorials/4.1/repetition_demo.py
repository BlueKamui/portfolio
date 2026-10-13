"""The lecture's own real number for "counting, repetition and spread": one fixed task, run
twenty times, count the successes.

This is deliberately a different exercise from `run_benchmark.py`'s twenty *different* cases.
Here the case is exactly the same, wording and numbers both, on every one of the twenty runs.
Any variation in the outcome is not systematic variation (block 4.1's other technique): it is pure
non-determinism, sampling noise on an identical input, the exact thing Song et al. (2024) argue
single-output evaluation hides.

Uses the single-shot pattern (no tool), on one case from the hard tier of `benchmark_cases.py`
(17-digit integers). With block 3.1's `add` tool, Python would do the sum instead of the model,
so twenty runs would say little about sampling spread. (That tool's `float` schema is not even
exact at 17 digits: see `benchmark_cases.py`.)

Run it:

    uv run --with claude-agent-sdk python repetition_demo.py
"""

import asyncio
import json
from pathlib import Path

from run_benchmark import grade, single_shot_options
from claude_agent_sdk import ResultMessage, query

CASE = {
    "a": "48213756123456789",
    "b": "91847329876543210",
    "true_sum": "140061085999999999",
}
QUESTION = (
    f"What is {CASE['a']} plus {CASE['b']}? "
    "State your final numeric answer on its own line as: ANSWER: <number>"
)
N_RUNS = 20
OUT_PATH = Path(__file__).parent / "repetition-demo.json"


async def run_once(model: str) -> dict:
    options = single_shot_options(model)
    summary = None
    async for message in query(prompt=QUESTION, options=options):
        if isinstance(message, ResultMessage):
            summary = message
    correct = grade(CASE["true_sum"], summary.result if summary else None)
    return {"answer": summary.result if summary else None, "correct": correct}


async def main() -> None:
    model = "claude-haiku-4-5"
    runs = []
    for i in range(1, N_RUNS + 1):
        result = await run_once(model)
        print(f"run {i:>2}/{N_RUNS}: correct={result['correct']}", flush=True)
        runs.append(result)

    n_correct = sum(r["correct"] for r in runs)
    print(f"\n{n_correct} / {N_RUNS} correct, same task, same wording, every time.")

    OUT_PATH.write_text(json.dumps({"case": CASE, "n_runs": N_RUNS, "n_correct": n_correct,
                                     "runs": runs}, indent=2))
    print(f"saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
