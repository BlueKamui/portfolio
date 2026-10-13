"""Block 4.1, tutorial, while vary_phrasing.py runs: one Agent Skill, and a test of when it loads.

An Agent Skill is a folder with a `SKILL.md` file: a name, a description, and instructions. See
`.claude/skills/receipt-format/SKILL.md` next to this script. The harness puts every Skill's name
and description into the context at the start. The model reads them, and when a task matches a
description it loads that Skill's full body, through a built-in tool called `Skill`. Verified at
https://agentskills.io and https://code.claude.com/docs/en/agent-sdk/skills.

This script sends a list of prompts, each with your prediction of whether it should load the
Skill, and prints a table: what you predicted, whether the model called the `Skill` tool, and
whether the answer contains the Skill's reference line, `Ref: TA-...`. Nobody would write that
line without reading the Skill's body, so it is a second piece of evidence beside the tool call.

**Four gaps: three here, one in `SKILL.md`.** Fill the three here first and run it: the Skill is
discovered and nothing loads, because its description is still a placeholder. Then write the
description and run it again.

Run it:

    uv run --with claude-agent-sdk python skill_demo.py
"""

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    ToolUseBlock,
    query,
)

from toy_agent import build_options

TOY_AGENT_DIR = Path(__file__).parent
SKILL_FILE = TOY_AGENT_DIR / ".claude" / "skills" / "receipt-format" / "SKILL.md"
MARKER = "Ref: TA-"  # only the Skill's body asks for this line

# Each entry is (prompt, should it load the Skill?).
PROMPTS = [
    ("What is 17 plus 25? Use the add tool.", False),
    ("What is 17 plus 25? Use the add tool, then show me the result as a receipt.", True),
    # --- TODO 3 --------------------------------------------------------------------------------
    # Add four more, with your prediction for each. Two that should load the Skill, worded
    # differently from the one above. Two that should not, and make at least one of those close:
    # about money or a bill, without asking for a receipt. Predict before you run.
]


def skill_options():
    """The harness options that make a Skill on disk available to a run.

    `cwd` is done for you: it points the harness at this folder, which is the one holding
    `.claude/skills/`. Three more options are missing.
    """
    return build_options(
        None,
        cwd=str(TOY_AGENT_DIR),
        # --- TODO 1 ------------------------------------------------------------------------
        # Three options belong here, and without all three no Skill can load.
        #
        #   1. setting_sources=[...]: which settings levels the harness reads. "project" is the
        #      level that reads this folder's own .claude directory.
        #   2. skills=...: which Skills to offer. "all" is fine here.
        #   3. A Skill loads through a built-in tool called "Skill". Block 3.1 showed what
        #      build_options()'s tools=[] does to built-in tools. Decide what this run needs.
        #
        # The [tools] line this script prints shows which tools the run really has. Check it.
    )


# --- TODO 2 ------------------------------------------------------------------------------------
# Return the Skill's name if this block is the model loading a Skill, and None otherwise.
# A Skill loads through a tool call: a ToolUseBlock whose name is "Skill", with the Skill's own
# name in its input under the key "skill". If in doubt, print one block and look.
def skill_called(block) -> str | None:
    return None


def check_todos() -> None:
    """Tests the gaps that can be tested without a model call."""
    problems = []
    fake_skill = ToolUseBlock(id="test", name="Skill", input={"skill": "receipt-format"})
    fake_tool = ToolUseBlock(id="test", name="mcp__calculator__add", input={"a": 1, "b": 2})
    if skill_called(fake_skill) != "receipt-format" or skill_called(fake_tool) is not None:
        problems.append("TODO 2: skill_called() should return 'receipt-format' for a Skill call "
                        "and None for any other tool call")
    if len(PROMPTS) < 6:
        problems.append(f"TODO 3: PROMPTS has {len(PROMPTS)} entries, it needs at least 6")
    if problems:
        raise SystemExit("Still to fill in or fix:\n  " + "\n  ".join(problems))


async def run_one(prompt: str, show_setup: bool) -> tuple[bool, bool]:
    """One run. Returns (did the model load the Skill, does the answer carry its marker)."""
    loaded, marker = False, False
    async for message in query(prompt=prompt, options=skill_options()):
        if isinstance(message, SystemMessage) and message.subtype == "init" and show_setup:
            tools = message.data.get("tools") or []
            skills = message.data.get("skills") or []
            print(f"[tools] {tools}")
            print(f"[skills discovered] {len(skills)}, receipt-format "
                  f"{'among them' if 'receipt-format' in skills else 'NOT among them'}")
            if "receipt-format" not in skills:
                print("  Check TODO 1, and that the folder is .claude/skills/receipt-format/.")
            if "Skill" not in tools:
                print("  There is no Skill tool in this run, so nothing can load. See TODO 1.")
            print()
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                name = skill_called(block)
                if name:
                    loaded = True
                    print(f"  [skill loaded] {name}")
        elif isinstance(message, ResultMessage):
            marker = MARKER in (message.result or "")
    return loaded, marker


async def main() -> None:
    if SKILL_FILE.is_file() and "description: TODO" in SKILL_FILE.read_text():
        print("Note: SKILL.md's description is still the placeholder, so nothing should load.")
        print("That is a useful first run. Write the description and run this again.\n")
    rows = []
    for i, (prompt, expected) in enumerate(PROMPTS):
        print(f"--- {prompt!r}")
        loaded, marker = await run_one(prompt, show_setup=(i == 0))
        rows.append((expected, loaded, marker, prompt))

    print(f"\n{'predicted':<10}{'loaded':<8}{'marker':<8}prompt")
    for expected, loaded, marker, prompt in rows:
        yes = {True: "yes", False: "no"}
        print(f"{yes[expected]:<10}{yes[loaded]:<8}{yes[marker]:<8}{prompt[:60]}")
    right = sum(expected == loaded for expected, loaded, _, _ in rows)
    print(f"\nyour prediction matched {right} of {len(rows)}")


if __name__ == "__main__":
    check_todos()
    asyncio.run(main())
