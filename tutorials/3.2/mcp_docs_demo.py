"""Block 3.2, tutorial step 1: connect a real, hosted MCP server to the toy agent.

`toy_agent.py`'s calculator runs in-process: the same Python file defines the tool and the
script that calls it. A real MCP server is different. It is someone else's program, running on
someone else's machine, that this script has never seen the code of. This is the Claude Code
documentation server, picked because it needs no account, no API key, and no local install: add
its URL and it works, which makes it the easiest live demo of a hosted server there is.

**This script has four gaps in it, marked TODO, and it will not run until you fill them.**
That is deliberate. Filling them is the exercise: the two changes you make to add any MCP server,
then the two pieces that measure what the server costs you in context. When they are filled, the
script prints your own version of the lecture's cost table: the setup on the first turn, what the
search result added, and the answer. Use your agent to help, and read what it writes before you
accept it.

Verified live: `https://code.claude.com/docs/mcp` connects with a plain HTTP transport and no
auth, exactly as documented at https://code.claude.com/docs/en/mcp-quickstart. The Claude Agent
SDK's own MCP guide (https://code.claude.com/docs/en/agent-sdk/mcp) uses this same server as its
quickstart example, which is why it is reused here rather than something narrower.

`build_options()` is unchanged from block 3.1's version except for the two keyword arguments
`extra_mcp_servers` and `extra_allowed_tools`, added so this script (and the image and Skill
demos alongside it) extend the one shared harness setup rather than redefining it.

Run it:

    uv run --with claude-agent-sdk python mcp_docs_demo.py

Requires the same `claude` CLI login as every other script in this folder. No separate
credential: this server needs none, and the SDK still authenticates to Claude itself through the
CLI's own OAuth session, exactly as `toy_agent.py` does.
"""

import asyncio
import json
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from toy_agent import build_options

# --- TODO 1 of 4 -------------------------------------------------------------------------
# A hosted MCP server is one entry in a dictionary, and it needs two things.
#
#   "type": the transport. "stdio" means a program started on your own machine; "http" means
#           one already running at a URL. This server is already running, so which is it?
#   "url":  the address. This one is https://code.claude.com/docs/mcp and it needs no key.
#
# Replace both "TODO" strings. The Agent SDK's MCP page shows the shape:
# https://code.claude.com/docs/en/agent-sdk/mcp
DOCS_SERVER = {
    "claude-code-docs": {
        "type": "http",
        "url": "https://code.claude.com/docs/mcp",
    }
}

# --- TODO 2 of 4 -------------------------------------------------------------------------
# The allow-list is the only thing that decides what the model may call, so nothing from this
# server can be used until it is granted here. Every tool a server exposes is named
# mcp__<server>__<tool>, and a pattern ending in * matches any tool name. Write one pattern
# that grants every tool from the "claude-code-docs" server at once.
DOCS_ALLOWED_TOOLS = ["mcp__claude-code-docs__*"]

# --- TODO 3 of 4 -------------------------------------------------------------------------
# How big was the context on one turn? Every model turn reports a `usage` dictionary with three
# input counts:
#
#   "input_tokens"                 new text on this turn, not cached
#   "cache_creation_input_tokens"  new text on this turn, written to the cache for next time
#   "cache_read_input_tokens"      text from earlier turns, read back from the cache
#
# The cache changes the price of a token, not whether the model read it. Return how many tokens
# the model read on this turn. A missing key counts as 0.
def context_size(usage: dict) -> int:
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )


# --- TODO 4 of 4 -------------------------------------------------------------------------
# Every tool description a server exposes lands in your context, and you pay for it on every
# turn. The run counts how many of the available tools came from the docs server, so the number
# is on screen rather than guessed at. Tools are named mcp__<server>__<tool>: complete the
# prefix that every tool from this server starts with.
PREFIX = "mcp__claude-code-docs__"

PROMPT = (
    "Use the claude-code-docs server to look up what an MCP server is and how Claude Code "
    "connects to one. Answer in two short sentences."
)


def _gaps_left() -> list[str]:
    """Which TODOs are still unfilled. Keeps the failure readable instead of a traceback."""
    entry = DOCS_SERVER["claude-code-docs"]
    gaps = []
    if entry["type"] == "TODO" or entry["url"] == "TODO":
        gaps.append("TODO 1: DOCS_SERVER needs a transport type and a URL.")
    if "TODO" in DOCS_ALLOWED_TOOLS:
        gaps.append("TODO 2: DOCS_ALLOWED_TOOLS needs one mcp__<server>__<tool> pattern.")
    turn_one = {"input_tokens": 2, "cache_creation_input_tokens": 2547}
    turn_two = {"input_tokens": 2, "cache_creation_input_tokens": 12504,
                "cache_read_input_tokens": 2547}
    if context_size(turn_one) != 2549 or context_size(turn_two) != 15053:
        gaps.append("TODO 3: context_size() should give 2549 and 15053 for the two test turns.")
    if PREFIX == "TODO":
        gaps.append("TODO 4: PREFIX needs completing.")
    return gaps


async def run(trace_path: Path | None) -> None:
    gaps = _gaps_left()
    if gaps:
        print("This script is not finished yet:\n")
        for gap in gaps:
            print(f"  {gap}")
        print("\nFill them in near the top of this file, then run it again.")
        return

    options = build_options(
        None,
        extra_mcp_servers=DOCS_SERVER,
        extra_allowed_tools=DOCS_ALLOWED_TOOLS,
    )
    raw_trace = []
    seen_turns: set[str] = set()
    turn_sizes: list[int] = []

    print(f"--- prompt: {PROMPT!r} ---\n")

    async for message in query(prompt=PROMPT, options=options):
        raw_trace.append(message)

        if isinstance(message, SystemMessage) and message.subtype == "init":
            # This is how you check a hosted server actually connected, rather than assuming
            # it did because no exception was raised.
            print("[mcp server]")
            for server in message.data.get("mcp_servers", []):
                print(f"  {server['name']}: {server['status']}")

            all_tools = message.data.get("tools", [])
            from_docs = [t for t in all_tools if t.startswith(PREFIX)]
            print(
                f"[tools] {len(all_tools)} available, "
                f"{len(from_docs)} of them from claude-code-docs"
            )
        elif isinstance(message, AssistantMessage):
            # One model turn can arrive as several messages sharing one message_id, one per
            # block, each carrying the same usage. Count each turn once.
            if message.usage and message.message_id not in seen_turns:
                seen_turns.add(message.message_id)
                turn_sizes.append(context_size(message.usage))
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"[model calls] {block.name}({block.input})")
                elif isinstance(block, TextBlock):
                    print(f"[model says] {block.text}")
        elif isinstance(message, ResultMessage):
            # Real, measured numbers, not an estimate.
            usage = message.usage or {}
            print("\n--- what went into the context ---")
            for i, size in enumerate(turn_sizes, start=1):
                if i == 1:
                    print(f"turn {i}: {size:>6} tokens read, all new: the setup")
                else:
                    added = size - turn_sizes[i - 2]
                    print(f"turn {i}: {size:>6} tokens read, {added} new: the tool call and result")
            print(f"answer: {usage.get('output_tokens'):>6} tokens out")
            print(f"total cost: ${message.total_cost_usd:.6f}")
            print(f"answer: {message.result}")

    if trace_path is not None:
        serialisable = [m.__dict__ if hasattr(m, "__dict__") else str(m) for m in raw_trace]
        trace_path.write_text(json.dumps(serialisable, indent=2, default=str))
        print(f"\nfull trace saved to {trace_path}")


if __name__ == "__main__":
    import sys

    trace_out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(run(trace_out))
