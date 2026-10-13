"""The course's toy agent: a script that gives Claude one tool, "add", and lets it call it.

This is the running thread for the rest of the course. Block 3.2 adds a real MCP server, a real
image and a real hosted speech API (`mcp_docs_demo.py`, `image_context.py` and `speech_tool.py`),
block 4.1 an Agent Skill (`skill_demo.py`), later blocks benchmark it and break it on purpose, and
every one of those scripts imports `build_options()` from this file.

What this script demonstrates, in order:

1. A tool is just a Python function plus a name, a description and an input schema. The
   description is what the model reads to decide when to call it: see `break_tool_description.py`
   for what happens when that description is vague.
2. The Claude Agent SDK's `query()` function runs the whole loop for you: it sends the prompt,
   reads the model's reply, runs the tool if the model asked for one, sends the result back, and
   repeats until the model is done. You never write that loop by hand.
3. Every step of the loop arrives as a typed message. Printing them, in order, is the real trace:
   this is what "walk one real trace line by line" means in the lecture.

Run it:

    uv run --with claude-agent-sdk python toy_agent.py
    uv run --with claude-agent-sdk python toy_agent.py --model claude-haiku-4-5
    uv run --with claude-agent-sdk python toy_agent.py --a 100 --b 250 --model claude-opus-5-5

`uv run --with claude-agent-sdk` installs the one dependency on the fly. No project setup, no
virtual environment to manage by hand, same pattern as `uv run --with pythae ...` in block 2.1.

Requires the `claude` CLI already installed and logged in (block 1.2's setup). The Agent SDK does
not talk to the Anthropic API directly: it drives your own installed `claude` command as a
subprocess and reuses whatever OAuth session `claude login` already set up. No separate API key,
no extra billing account. Confirmed by running this script with `ANTHROPIC_API_KEY` unset: the
trace below still reports `apiKeySource: none`, meaning it used the CLI's own login.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

# On Windows, when another program reads this script's output (your agent, for example), Python
# can print only some characters and stops with an error on the rest. This line prevents that.
sys.stdout.reconfigure(encoding="utf-8")


# Step 1: define the tool. Four parts: a name, a description, an input schema (as a plain
# dict, {"a": float, "b": float} means "two required numbers"), and a handler function that
# does the actual work. Claude never sees the Python code below the decorator, only the name,
# description and schema, so those three are the entire interface contract.
@tool("add", "Add two numbers together and return the sum.", {"a": float, "b": float})
async def add(args: dict) -> dict:
    result = args["a"] + args["b"]
    # A tool result is a list of content blocks. For a plain number, one text block is enough.
    return {"content": [{"type": "text", "text": str(result)}]}


# Step 2: wrap the tool in an in-process MCP server. This runs inside this same Python process,
# not as a separate program: MCP is the wire format the harness speaks internally, even for a
# tool defined a few lines up in the same file. Block 3.2 connects a *real*, separately hosted
# MCP server the same way, just with mcp_servers pointing at a URL instead of this object.
calculator_server = create_sdk_mcp_server(name="calculator", version="1.0.0", tools=[add])


def build_options(
    model: str | None,
    *,
    extra_mcp_servers: dict | None = None,
    extra_allowed_tools: list[str] | None = None,
    **extra_options,
) -> ClaudeAgentOptions:
    """The harness's configuration for this run.

    tools=[] removes every built-in tool (file read, bash, web search, the lot), leaving only
    the one tool this script defines. setting_sources=[] skips loading any project or user level
    Claude Code settings files, including CLAUDE.md. Both choices keep the demo minimal: the
    anatomy on screen is model, harness, one tool, nothing else.

    It is not a clean room, though. The harness still adds a few things of its own to the
    context: your account's email address, today's date, and any memory notes Claude Code keeps
    for this folder. Ask the agent what it can see about you to check.

    Block 3.2 extends this same function rather than redefining the harness setup:
    `extra_mcp_servers` adds a real, hosted MCP server (see `mcp_docs_demo.py`)
    alongside the in-process calculator, `extra_allowed_tools` grants the matching tool names, and
    any other `ClaudeAgentOptions` field (`cwd`, `setting_sources`, `skills`, for the Skill demo in
    `skill_demo.py`) can be passed straight through as a keyword argument. Passing none of these
    reproduces block 3.1's exact behaviour, so `compare_tiers.py` and the break scripts are
    unaffected.
    """
    mcp_servers = {"calculator": calculator_server, **(extra_mcp_servers or {})}
    allowed_tools = ["mcp__calculator__add", *(extra_allowed_tools or [])]
    fields = dict(
        mcp_servers=mcp_servers,
        allowed_tools=allowed_tools,
        tools=[],
        setting_sources=[],
        model=model,  # None means "the harness's own default"
    )
    fields.update(extra_options)  # e.g. cwd, setting_sources, skills for skill_demo.py
    return ClaudeAgentOptions(**fields)


async def run(prompt: str, model: str | None, trace_path: Path | None) -> None:
    options = build_options(model)
    raw_trace = []

    print(f"--- prompt: {prompt!r} (model: {model or 'harness default'}) ---\n")

    async for message in query(prompt=prompt, options=options):
        raw_trace.append(message)

        # Step 3: the loop, one message at a time. This is the anatomy on screen:
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    # The model proposes a tool call. It has not run yet.
                    print(f"[model proposes] {block.name}({block.input})")
                elif isinstance(block, TextBlock):
                    print(f"[model says] {block.text}")
        elif isinstance(message, UserMessage):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    # Something outside the model (this script's own `add` function) has now
                    # run, and its result has come back into the context as a new turn.
                    print(f"[tool result] {block.content}")
        elif isinstance(message, ResultMessage):
            # The loop is done. Real, measured cost and timing, not an estimate.
            print("\n--- summary ---")
            print(f"answer: {message.result}")
            print(f"wall clock: {message.duration_ms} ms")
            print(f"total cost: ${message.total_cost_usd:.6f}")
            print(f"input tokens: {message.usage.get('input_tokens')}, "
                  f"output tokens: {message.usage.get('output_tokens')}")

    if trace_path is not None:
        # Save every message as JSON so the trace can be inspected after the run, not just
        # scrolled past in the terminal. dataclasses are not JSON-serialisable directly, so this
        # goes through each object's own dict representation.
        serialisable = [
            m.__dict__ if hasattr(m, "__dict__") else str(m) for m in raw_trace
        ]
        trace_path.write_text(json.dumps(serialisable, indent=2, default=str))
        print(f"\nfull trace saved to {trace_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="The course's toy agent: adds two numbers.")
    parser.add_argument("--a", type=float, default=17)
    parser.add_argument("--b", type=float, default=25)
    parser.add_argument(
        "--model",
        default=None,
        help="e.g. claude-haiku-4-5, claude-sonnet-5, claude-opus-5-5. "
        "Omit to use the harness's own default.",
    )
    parser.add_argument("--trace-out", default=None, help="path to save the full JSON trace")
    args = parser.parse_args()

    prompt = f"What is {args.a} plus {args.b}? Use the add tool."
    trace_path = Path(args.trace_out) if args.trace_out else None
    asyncio.run(run(prompt, args.model, trace_path))


if __name__ == "__main__":
    main()
