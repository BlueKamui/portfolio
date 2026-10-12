"""Second on-purpose failure: a schema the model cannot possibly satisfy.

`toy_agent.py` never constrains the model's final answer to a shape, it just replies in prose.
This script asks for a structured answer instead, using `output_format`: the harness makes the
model produce JSON matching a schema, so code downstream can parse it reliably instead of
scraping a sentence. That is "structured output" as the other half of the tool-schema contract.

The schema below is broken on purpose: it requires a field called "total", but "total" is never
defined anywhere in the schema's own list of properties. There is no way to produce an object that
both matches the properties list and satisfies the requirement, because the requirement points at
a field that does not exist.

Run it:

    uv run --with claude-agent-sdk python break_output_schema.py

What actually happened, the first time this was run (real transcript, not paraphrased):

    result text: None
    structured_output: None
    is_error: True
    errors: ['Failed to provide valid structured output after 5 attempts']

The harness tried five times and gave up cleanly: `is_error` is set, the error names exactly what
failed, and nothing pretends to have succeeded. Compare this to the tool description failure
above, where the model's own reasoning quietly patched over the problem: here there is no way to
patch over an impossible schema, so the loop fails loudly instead of silently. That is the schema
half of "a vague description is a bug": a broken contract on either side of the loop breaks it,
the only difference is whether the break is visible.

**Not every run fails this exact way, and that is worth knowing before presenting this live.**
Across four runs made while building this block, three gave the clean harness failure quoted
above, and one had the model instead notice the contradiction itself and reply in plain text,
explaining that the schema cannot be satisfied and giving the arithmetic answer directly, with
`is_error` left `False`. Both outcomes make the same point: something in the loop noticed the
contract was broken. Only one of them makes the harness itself say so. If your own run looks like
the second shape, that is not a broken exercise, it is the same failure surfacing one level up.
"""

import asyncio
import sys

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
    tool,
)


@tool("add", "Add two numbers together and return the sum.", {"a": float, "b": float})
async def add(args: dict) -> dict:
    result = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": str(result)}]}


calculator_server = create_sdk_mcp_server(name="calculator", version="1.0.0", tools=[add])

# Broken on purpose: "required" names "total", but "properties" never defines a "total" field.
BROKEN_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
            "sum": {"type": "number"},
        },
        "required": ["a", "b", "total"],
        "additionalProperties": False,
    },
}


async def main() -> None:
    options = ClaudeAgentOptions(
        mcp_servers={"calculator": calculator_server},
        allowed_tools=["mcp__calculator__add"],
        tools=[],
        setting_sources=[],
        output_format=BROKEN_SCHEMA,
    )
    try:
        async for message in query(
            prompt="What is 17 plus 25? Use the add tool.", options=options
        ):
            if isinstance(message, ResultMessage):
                print(f"result text: {message.result}")
                print(f"structured_output: {message.structured_output}")
                print(f"is_error: {message.is_error}")
                print(f"errors: {message.errors}")
    except Exception as exc:
        print(f"EXCEPTION: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    # On Windows, when another program reads this script's output (your agent, for example), Python
    # can print only some characters and stops with an error on the rest. This line prevents that.
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
