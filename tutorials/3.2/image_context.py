"""Block 3.2, tutorial step 2: feed a real image into context, predict its cost, then measure it.

No OCR step, no captioning tool. This is the point of "images go into context natively": the
bytes go in as part of the prompt, the same way text does, and the model reads them directly. No
separate vision pipeline, and no tool call at all for this part, just a different kind of content
block in the same message.

**This script has three gaps in it, marked TODO, and it will not run until you fill them.** The
first is the image block itself, which is the whole mechanism. The second predicts what the
picture costs from the patch rule on the lecture slide. The third checks the model's answer
against what the picture really says. The script then asks the same question twice, once without
the picture and once with it, so the difference is the picture's measured cost, and prints your
prediction beside it. Use your agent to help, and read what it writes before you accept it.

The image used here is `toy-agent-trace.png`, saved beside this script: a screenshot of a real
toy-agent run (the terminal trace for "17 plus 25", with a wall-clock time and a dollar cost
printed at the bottom). Those numbers are not something the model could know in advance, only
something it can read from the picture.

The Agent SDK's single-string `prompt` argument cannot carry an image (`query(prompt="...")` is
text only). Sending mixed content needs the streaming form instead: an async generator yielding
user-turn message dicts, where `content` is a list of blocks exactly like the Messages API's own
image blocks. See https://code.claude.com/docs/en/agent-sdk/python for the accepted prompt shapes.

Run it:

    uv run --with claude-agent-sdk python image_context.py
"""

import asyncio
import base64
import json
import math
import struct
from pathlib import Path
from typing import AsyncIterator

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, query

from toy_agent import build_options

_REPO_IMAGE = Path(__file__).parent.parent / "figures" / "toy-agent-trace.png"
# In this course's own repository the screenshot is block 3.1's figure. On your machine it is a
# download that sits beside this script.
IMAGE_PATH = _REPO_IMAGE if _REPO_IMAGE.is_file() else Path(__file__).parent / "toy-agent-trace.png"

QUESTION = (
    "This is a screenshot of a terminal. Read the summary at the bottom and tell me two things: "
    "the wall-clock time in milliseconds, and the total cost in US dollars. Quote both numbers "
    "exactly as printed, nothing else."
)


async def one_user_turn_with_image(text: str, image_path: Path) -> AsyncIterator[dict]:
    """The streaming prompt form: one user turn, text plus an inline base64 image block."""
    encoded = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                # --- TODO 1 of 3 --------------------------------------------------------
                # One more content block goes here, and it is the whole point of this file.
                # An image block has a "type" of "image" and a "source" dict. The source
                # needs three keys:
                #
                #   "type"        the encoding. Here the bytes are base64 encoded.
                #   "media_type"  the MIME type. This file is a .png.
                #   "data"        the encoded bytes, already sitting in `encoded` above.
                #
                # Anthropic's Vision page shows the exact shape:
                # https://platform.claude.com/docs/en/build-with-claude/vision
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": encoded,
                    },
                },
            ],
        },
    }


async def one_user_turn_text_only(text: str) -> AsyncIterator[dict]:
    """The same turn with no image, so the difference between the two runs is the picture."""
    yield {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


# --- TODO 2 of 3 -------------------------------------------------------------------------------
# Predict what an image of this size costs, before you measure it. The lecture slide "What an
# image costs" gives the rule: one visual token per 28 by 28 pixel patch, and a patch that is
# only partly covered still counts as a whole one. math.ceil() rounds up.
def visual_tokens(width: int, height: int) -> int:
    return math.ceil(width / 28) * math.ceil(height / 28)


# --- TODO 3 of 3 -------------------------------------------------------------------------------
# Did the model read the picture correctly? The summary at the bottom of the screenshot says
# "wall clock: 3860 ms" and "total cost: $0.010976". Return True only if the answer contains
# both numbers exactly as printed.
def read_correctly(answer: str) -> bool:
    return "3860 ms" in answer and "$0.010976" in answer


def png_size(path: Path) -> tuple[int, int]:
    """Width and height of a PNG, read from its header: bytes 16 to 24 hold them."""
    return struct.unpack(">II", path.read_bytes()[16:24])


def _gaps_left() -> list[str]:
    """Tests each gap on known inputs before any model call."""
    gaps = []
    first_turn = asyncio.run(_first(one_user_turn_with_image(QUESTION, IMAGE_PATH)))
    if not any(block.get("type") == "image" for block in first_turn["message"]["content"]):
        gaps.append("TODO 1: there is no image block in the prompt yet, only text.")
    if visual_tokens(1000, 1000) != 1296 or visual_tokens(500, 500) != 324:
        gaps.append("TODO 2: visual_tokens() should give 1296 for 1000 by 1000, 324 for 500 by 500.")
    if not read_correctly("3860 ms, $0.010976") or read_correctly("3860 ms, $0.01"):
        gaps.append("TODO 3: read_correctly() should need both numbers, exactly as printed.")
    return gaps


async def _first(generator: AsyncIterator[dict]) -> dict:
    return [turn async for turn in generator][0]


async def ask(prompt: AsyncIterator[dict], label: str, trace: list) -> tuple[int, str]:
    """One run. Returns how many input tokens the model read, and its answer."""
    options = build_options(None)  # the calculator tool is unused here, harmless to leave in
    read, answer = 0, ""
    async for message in query(prompt=prompt, options=options):
        trace.append(message)
        if isinstance(message, AssistantMessage) and label == "with the image":
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[model says] {block.text}")
        elif isinstance(message, ResultMessage):
            usage = message.usage or {}
            read = (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0))
            answer = message.result or ""
            print(f"[{label}] {read} input tokens, ${message.total_cost_usd:.6f}")
    return read, answer


async def run(trace_path: Path | None) -> None:
    width, height = png_size(IMAGE_PATH)
    predicted = visual_tokens(width, height)
    print(f"--- image: {IMAGE_PATH.name}, {width} by {height} pixels ---")
    print(f"--- predicted: {predicted} visual tokens ---\n")

    raw_trace: list = []
    without, _ = await ask(one_user_turn_text_only(QUESTION), "without the image", raw_trace)
    with_image, answer = await ask(
        one_user_turn_with_image(QUESTION, IMAGE_PATH), "with the image", raw_trace
    )

    print("\n--- summary ---")
    print(f"predicted cost of the picture: {predicted} tokens")
    print(f"measured cost of the picture:  {with_image - without} tokens "
          f"({with_image} with it, {without} without)")
    print(f"read the picture correctly: {'yes' if read_correctly(answer) else 'NO'}")

    if trace_path is not None:
        serialisable = [m.__dict__ if hasattr(m, "__dict__") else str(m) for m in raw_trace]
        trace_path.write_text(json.dumps(serialisable, indent=2, default=str))
        print(f"\nfull trace saved to {trace_path}")


if __name__ == "__main__":
    import sys

    if not IMAGE_PATH.is_file():
        print(f"No image at {IMAGE_PATH}.")
        print("Download toy-agent-trace.png from this block's Canvas module into this folder.")
        sys.exit(1)
    gaps = _gaps_left()
    if gaps:
        print("This script is not finished yet:\n")
        for gap in gaps:
            print(f"  {gap}")
        print("\nFill them in, then run it again.")
        sys.exit(1)
    trace_out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(run(trace_out))
