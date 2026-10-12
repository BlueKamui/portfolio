"""First on-purpose failure: a vague tool description. Then fix it, and count.

Same handler as `toy_agent.py`'s `add` function, still just does `a + b`. The only change is the
name and the description: instead of "add two numbers together", it is called "calculate" and
described only as "perform an arithmetic operation on two numbers". Nothing about the code
changed, only the words the model reads before deciding whether and how to call the tool.

Then the prompt asks for a multiplication. Watch what the model does with a tool that cannot tell
it what operation it actually performs.

Run it:

    uv run --with claude-agent-sdk python break_tool_description.py
    uv run --with claude-agent-sdk python break_tool_description.py --runs 5

Each run prints whether the model called the tool and whether its final answer contains the right
product, 425. With `--runs 5` it also prints the totals, so one lucky run cannot decide it.

**The two lines to change are DESCRIPTION and PROMPT, just below the imports.** Change one at a
time and run again, so you know which change did what.

What actually happened, the first time this was run (real transcript, not paraphrased):

    TOOL CALL: mcp__calculator__calculate {'a': 17, 'b': 25}
    FINAL RESULT: It looks like the calculator tool only performed addition here (17 + 25 = 42),
    not multiplication -- it doesn't seem to have an option to specify the operation type, and it
    returned 42.

    For the actual multiplication: 17 x 25 = 425.

The misuse is real: the model called an addition-only tool believing it might multiply, because
the description never said which operation it performs. What happens next is a genuine, separate
finding: the model independently knows that 17 x 25 = 425, so it noticed the tool's answer did
not match and said so.

Do not read that as "vague descriptions are fine because the model checks its own work". It
checked here only because multiplication is something the model can verify on its own, with no
tool at all. Swap this toy example for a tool that looks up a real exchange rate, a real account
balance or a real database record, and there is nothing for the model to check its answer
against: the wrong number goes straight into the final answer with no warning attached.
"""

import argparse
import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

# Broken on purpose: the description never says this tool only adds.
DESCRIPTION = "Perform an arithmetic operation on two numbers."

# The prompt tells the model which tool to use. Try it without the second sentence as well.
PROMPT = "What is 17 times 25? Use the calculate tool."


@tool("calculate", DESCRIPTION, {"a": float, "b": float})
async def calculate(args: dict) -> dict:
    result = args["a"] + args["b"]  # always adds, whatever was asked
    return {"content": [{"type": "text", "text": str(result)}]}


calculator_server = create_sdk_mcp_server(name="calculator", version="1.0.0", tools=[calculate])


async def run_once() -> tuple[bool, bool]:
    """One run. Returns (did it call the tool, does the final answer contain 425)."""
    options = ClaudeAgentOptions(
        mcp_servers={"calculator": calculator_server},
        allowed_tools=["mcp__calculator__calculate"],
        tools=[],
        setting_sources=[],
    )
    called, answer = False, ""
    async for message in query(prompt=PROMPT, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    called = True
                    print(f"TOOL CALL: {block.name} {block.input}")
        if isinstance(message, ResultMessage):
            answer = message.result or ""
            print(f"FINAL RESULT: {answer}")
    return called, "425" in answer


async def main(runs: int) -> None:
    print(f"description: {DESCRIPTION!r}\nprompt: {PROMPT!r}")
    tally = []
    for i in range(1, runs + 1):
        print(f"\n--- run {i} of {runs} ---")
        tally.append(await run_once())
    if runs > 1:
        print(f"\ncalled the tool: {sum(c for c, _ in tally)} of {runs}")
        print(f"answer contains 425: {sum(r for _, r in tally)} of {runs}")


if __name__ == "__main__":
    # On Windows, when another program reads this script's output (your agent, for example), Python
    # can print only some characters and stops with an error on the rest. This line prevents that.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="A vague tool description, counted.")
    parser.add_argument("--runs", type=int, default=1)
    asyncio.run(main(parser.parse_args().runs))
