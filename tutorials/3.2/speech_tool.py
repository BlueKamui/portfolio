"""Block 3.2, tutorial step 4: two custom tools wrapping a real, hosted, free speech API.

Speech does not arrive natively in a model's context, and building your own recogniser or
synthesiser is the wrong move here. Call a hosted one instead, and that hosted call is a real
tool call. Groq (https://groq.com, nothing to do with Grok the chat model) is the
pick: a free tier with no payment method, running both directions, Whisper speech-to-text and
Orpheus text-to-speech, over a plain REST API.

Unlike steps 1 to 3, this file has no gaps to fill. It depends on a third-party account and a
network call, which is a poor place to be stuck, so it is here to read and run rather than to
complete. Read the two `@tool` decorators: they are the same four parts as block 3.1's `add`.

Verified this session, live:

- `https://api.groq.com/openai/v1/audio/transcriptions` (Whisper) and
  `https://api.groq.com/openai/v1/audio/speech` (Orpheus TTS) both answered a real, unauthenticated
  request with `401 {"error": {"message": "Invalid API Key", ...}}`, confirming both endpoints are
  live and reachable, not a stale or renamed URL.
- Groq's own rate-limit docs (https://console.groq.com/docs/rate-limits) list a free tier for
  both: `whisper-large-v3` and `whisper-large-v3-turbo` at 20 requests/minute, 2,000/day;
  `canopylabs/orpheus-v1-english` at 10 requests/minute, 100/day.
- Groq's own billing FAQs (https://console.groq.com/docs/billing-faqs, checked 24 September 2026)
  require a payment method only to upgrade from the free tier to the Developer tier, so the free
  tier needs an email or Google sign-in and nothing else.

**What this build session could not do**: get a personal Groq API key. Creating a real, live
third-party account is not something to do inside an unattended authoring session, so the two
tools below are real, complete, and tested up to the authentication boundary, not beyond it.
Running either with `GROQ_API_KEY` unset reaches the real endpoint and gets the real
"Invalid API Key" response quoted above: genuine evidence the call is real, just not yet a
successful one. Set `GROQ_API_KEY` (free, from https://console.groq.com/keys) before teaching
this live to see a full, successful transcription and synthesis.

Run it. Set the key once in your terminal first, with `export GROQ_API_KEY=...` on macOS and Linux
or `$env:GROQ_API_KEY="..."` in Windows PowerShell, then:

    uv run --with claude-agent-sdk --with httpx python speech_tool.py transcribe path/to/clip.wav
    uv run --with claude-agent-sdk --with httpx python speech_tool.py speak "Hello from block 3.2" out.wav

Without a key set, both commands still run a real HTTP call and print Groq's real error.

The run prints three kinds of line. `[model calls]` is the call the model proposed. `[tool result]`
is what the tool itself returned: Whisper's own transcription, or Groq's own error message. `[model
says]` is the model retelling that result. To check the round trip, compare the words you spoke
with the `[tool result]` line, not with the model's retelling of it.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from toy_agent import build_options

GROQ_BASE = "https://api.groq.com/openai/v1/audio"


def _auth_headers() -> dict[str, str]:
    key = os.environ.get("GROQ_API_KEY", "")
    # No key set: send no Authorization header at all, so the request still reaches Groq's
    # real servers and comes back with their real "Invalid API Key" response, rather than
    # httpx rejecting an empty bearer token before the request is even sent.
    return {"Authorization": f"Bearer {key}"} if key else {}


@tool(
    "transcribe_audio",
    "Transcribe a spoken audio file to text using a hosted speech-to-text model.",
    {"file_path": str},
)
async def transcribe_audio(args: dict[str, Any]) -> dict[str, Any]:
    path = Path(args["file_path"])
    if not path.exists():
        return {"content": [{"type": "text", "text": f"No such file: {path}"}], "is_error": True}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GROQ_BASE}/transcriptions",
            headers=_auth_headers(),
            data={"model": "whisper-large-v3-turbo"},
            files={"file": (path.name, path.read_bytes())},
        )

    if response.status_code != 200:
        return {
            "content": [{"type": "text", "text": f"Groq STT error {response.status_code}: {response.text}"}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": response.json().get("text", "")}]}


@tool(
    "speak_text",
    "Turn text into a spoken audio file using a hosted text-to-speech model.",
    {"text": str, "out_path": str},
)
async def speak_text(args: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GROQ_BASE}/speech",
            headers=_auth_headers(),
            json={
                "model": "canopylabs/orpheus-v1-english",
                "voice": "troy",
                "input": args["text"],
                "response_format": "wav",
            },
        )

    if response.status_code != 200:
        return {
            "content": [{"type": "text", "text": f"Groq TTS error {response.status_code}: {response.text}"}],
            "is_error": True,
        }
    Path(args["out_path"]).write_bytes(response.content)
    return {"content": [{"type": "text", "text": f"Saved {len(response.content)} bytes to {args['out_path']}"}]}


speech_server = create_sdk_mcp_server(name="speech", version="1.0.0", tools=[transcribe_audio, speak_text])


async def run(prompt: str) -> None:
    options = build_options(
        None,
        extra_mcp_servers={"speech": speech_server},
        extra_allowed_tools=["mcp__speech__transcribe_audio", "mcp__speech__speak_text"],
    )
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"[model calls] {block.name}({block.input})")
                elif isinstance(block, TextBlock):
                    print(f"[model says] {block.text}")
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    # What the tool itself returned: Whisper's own words, or Groq's own error,
                    # before the model retells it. Compare against this line, not [model says].
                    print(f"[tool result] {block.content}")
        elif isinstance(message, ResultMessage):
            print(f"\n[final] {message.result}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    if action == "transcribe":
        asyncio.run(run(f"Transcribe the audio file at {sys.argv[2]} and tell me what it says."))
    elif action == "speak":
        text, out_path = sys.argv[2], sys.argv[3]
        asyncio.run(run(f"Speak the text {text!r} and save it to {out_path}."))
    else:
        print(__doc__)
