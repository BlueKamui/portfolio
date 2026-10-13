"""Block 3.2, tutorial step 6, extension 1: make the docs run cheaper, and measure turn 1.

Three runs of the same prompt, each stopped after the first model turn (max_turns=1), so the
number printed is the size of the setup: system prompt, tool descriptions and the question.

  A  allow-list is the whole server:  mcp__claude-code-docs__*
  B  allow-list narrowed to the one tool the model actually used
  C  B, plus the other docs tools removed with disallowed_tools

Run it:

    uv run --with claude-agent-sdk python mcp_docs_cheaper.py
"""

import asyncio

from claude_agent_sdk import AssistantMessage, SystemMessage, query

from mcp_docs_demo import DOCS_SERVER, PREFIX, PROMPT, context_size
from toy_agent import build_options

USED_TOOL = "mcp__claude-code-docs__search_claude_code_docs"  # the one call in mcp_docs_demo.py


async def turn_one(label: str, allowed: list[str], disallowed: list[str] | None = None):
    """Run one turn and return (tokens read on turn 1, names of the docs tools on offer)."""
    extra = {"disallowed_tools": disallowed} if disallowed else {}
    options = build_options(
        None,
        extra_mcp_servers=DOCS_SERVER,
        extra_allowed_tools=allowed,
        max_turns=1,
        **extra,
    )
    size, docs_tools = 0, []
    try:
        async for message in query(prompt=PROMPT, options=options):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                tools = message.data.get("tools", [])
                docs_tools = [t for t in tools if t.startswith(PREFIX)]
            elif isinstance(message, AssistantMessage) and message.usage and not size:
                size = context_size(message.usage)
    except Exception as exc:  # max_turns=1 ends the run with an error after turn 1: expected
        print(f"  ({label}: run ended with: {type(exc).__name__})")
    print(f"[{label}] turn 1 read {size} tokens; docs tools on offer: {len(docs_tools)}")
    return size, docs_tools


async def main() -> None:
    a, docs_tools = await turn_one("A whole server allowed", [f"{PREFIX}*"])
    print("  docs tools:", [t.removeprefix(PREFIX) for t in docs_tools])
    b, _ = await turn_one("B allow-list narrowed to one tool", [USED_TOOL])
    others = [t for t in docs_tools if t != USED_TOOL]
    c, _ = await turn_one("C B + other two removed", [USED_TOOL], disallowed=others)
    print("\n--- summary ---")
    print(f"A {a}   B {b}   C {c}")
    print(f"narrowing the allow-list changed turn 1 by {b - a} tokens")
    print(f"removing the other tools changed it by {c - b} tokens")


if __name__ == "__main__":
    asyncio.run(main())
