"""Run the toy agent's real query on two model tiers and compare cost and time.

This is what "choosing a model for the task" means as a design decision, felt rather than only
asserted: the same tool call, the same question, on a fast/cheap tier and a slower/more capable
tier, with the real numbers printed side by side. It saves the numbers as
`tier-comparison.json`, beside this script, and prints the path when it finishes.

What each column means:

- turns: how many times the model was called. Every turn re-sends the whole conversation so far.
- tokens in: everything the model read, summed over all turns, including any part it read from
  the prompt cache. `(cached)` is how much of that came from the cache, at a tenth of the price.
- tokens out: everything the model wrote, including its hidden reasoning.
- cost: the harness's own figure, in US dollars. It includes a small call the harness makes to
  Haiku 4.5 on every run, whichever model you asked for.

Run it:

    uv run --with claude-agent-sdk python compare_tiers.py
"""

import asyncio
import json
from pathlib import Path

from claude_agent_sdk import ResultMessage, query

from toy_agent import build_options

# Two tiers named on the slide: fast-and-cheap against slower-and-more-capable.
# Verify these are still current before quoting them: model names and prices move.
MODELS = ["claude-haiku-4-5", "claude-sonnet-5"]

PROMPT = "What is 17 plus 25? Use the add tool."


async def run_one(model: str) -> dict:
    options = build_options(model)
    summary = None
    # Consume the whole generator (ResultMessage is always last) rather than returning as
    # soon as it appears: returning early leaves the async generator mid-iteration, which
    # the SDK's own cleanup logs as a spurious error on exit.
    async for message in query(prompt=PROMPT, options=options):
        if isinstance(message, ResultMessage):
            usage = message.usage or {}
            cached = usage.get("cache_read_input_tokens", 0)
            summary = {
                "model": model,
                "turns": message.num_turns,
                "wall_clock_ms": message.duration_ms,
                "total_cost_usd": message.total_cost_usd,
                "tokens_in": usage.get("input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
                + cached,
                "tokens_in_cached": cached,
                "tokens_out": usage.get("output_tokens", 0),
                "answer": message.result,
            }
    if summary is None:
        raise RuntimeError(f"no ResultMessage for {model}")
    return summary


async def main() -> None:
    results = [await run_one(model) for model in MODELS]

    print(f"{'model':<18}{'turns':>6}{'time (ms)':>11}{'tokens in (cached)':>21}"
          f"{'tokens out':>12}{'cost (USD)':>12}")
    for r in results:
        tokens_in = f"{r['tokens_in']} ({r['tokens_in_cached']})"
        print(f"{r['model']:<18}{r['turns']:>6}{r['wall_clock_ms']:>11}{tokens_in:>21}"
              f"{r['tokens_out']:>12}{r['total_cost_usd']:>12.6f}")

    # In this course's own repository the JSON is a figure source for block 3.1's deck. On your
    # machine that file does not exist, so the file lands beside this script instead.
    repo_out = Path(__file__).parent.parent / "figures" / "tier-comparison.json"
    out_path = repo_out if repo_out.is_file() else Path(__file__).parent / "tier-comparison.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nsaved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
