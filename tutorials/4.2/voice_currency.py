"""Subelement 2 platform: a voice currency assistant, started with one command.

Four parts, wired together (the Day 4 take-home asks for exactly these):

- Tool call:   `convert_currency` (fixed GBP/EUR/USD rates, from block 3.1), an in-process MCP server.
- MCP server:  `rates` (currency) and `speech` (Groq Whisper in, Groq Orpheus out, from block 3.2).
- Modality:    speech. A caller's audio goes in, a spoken answer comes out as a WAV file.
- Loop:        tool loop. The model chooses which tool to call and when it is done.

One command, from this folder, with GROQ_API_KEY set in the terminal:

    uv run --with claude-agent-sdk --with httpx python voice_currency.py

That makes a spoken question (a simulated caller), runs the agent on it, and saves `answer.wav`.
Other ways to run it:

    ... voice_currency.py --case yen                      # the pair with no rate: should answer null
    ... voice_currency.py --case yen --repeats 10         # count how often it is right, for the failure-mode check
    ... voice_currency.py --question-wav my_recording.wav # your own voice instead of the simulated caller

Needs `toy_agent.py` in this folder (copied from 3.2), the `claude` command installed and logged in,
and a free Groq key (`export GROQ_API_KEY=...`).
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

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

HERE = Path(__file__).parent
GROQ_BASE = "https://api.groq.com/openai/v1/audio"

# --- Tool 1: currency (from block 3.1, unchanged) ------------------------------------------------
RATES = {
    ("GBP", "EUR"): 1.17, ("EUR", "GBP"): 0.85,
    ("GBP", "USD"): 1.27, ("USD", "GBP"): 0.79,
    ("EUR", "USD"): 1.08, ("USD", "EUR"): 0.92,
}


@tool(
    "convert_currency",
    "Convert a money amount from one currency to another using fixed exchange rates. "
    "Use it whenever the question asks how much money in one currency is worth in another. "
    "Do not use it for plain arithmetic with no currencies involved. "
    "Returns the converted amount as a number in the target currency, rounded to 2 decimal "
    "places, as text (for example '58.50'). Supports only GBP, EUR and USD, in any direction "
    "between them. For any other currency, or the same currency twice, it returns an error "
    "and no amount: it never guesses a rate.",
    {"amount": float, "from_currency": str, "to_currency": str},
)
async def convert_currency(args: dict) -> dict:
    pair = (args["from_currency"].upper(), args["to_currency"].upper())
    rate = RATES.get(pair)
    if rate is None:
        return {"content": [{"type": "text", "text": f"No rate available for {pair[0]} to {pair[1]}."}],
                "is_error": True}
    return {"content": [{"type": "text", "text": f"{args['amount'] * rate:.2f}"}]}


# --- Tools 2 and 3: speech (from block 3.2) ------------------------------------------------------
def _auth() -> dict[str, str]:
    key = os.environ.get("GROQ_API_KEY", "")
    return {"Authorization": f"Bearer {key}"} if key else {}


async def synthesise(text: str, out_path: Path) -> str | None:
    """Text to a WAV file via Groq. Returns an error string, or None on success."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{GROQ_BASE}/speech", headers=_auth(),
            json={"model": "canopylabs/orpheus-v1-english", "voice": "troy",
                  "input": text, "response_format": "wav"},
        )
    if r.status_code != 200:
        return f"Groq TTS error {r.status_code}: {r.text}"
    out_path.write_bytes(r.content)
    return None


@tool(
    "transcribe_audio",
    "Transcribe a spoken audio file to text using a hosted speech-to-text model. "
    "Use it first, whenever the request arrives as an audio file. Returns the words spoken, as text.",
    {"file_path": str},
)
async def transcribe_audio(args: dict) -> dict:
    path = Path(args["file_path"])
    if not path.exists():
        return {"content": [{"type": "text", "text": f"No such file: {path}"}], "is_error": True}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{GROQ_BASE}/transcriptions", headers=_auth(),
            data={"model": "whisper-large-v3-turbo"},
            files={"file": (path.name, path.read_bytes())},
        )
    if r.status_code != 200:
        return {"content": [{"type": "text", "text": f"Groq STT error {r.status_code}: {r.text}"}],
                "is_error": True}
    return {"content": [{"type": "text", "text": r.json().get("text", "")}]}


@tool(
    "speak_text",
    "Turn a short piece of text into a spoken audio file using a hosted text-to-speech model. "
    "Use it last, to give the caller the final answer aloud. Returns the path of the saved WAV file.",
    {"text": str, "out_path": str},
)
async def speak_text(args: dict) -> dict:
    error = await synthesise(args["text"], Path(args["out_path"]))
    if error:
        return {"content": [{"type": "text", "text": error}], "is_error": True}
    return {"content": [{"type": "text", "text": f"Saved spoken answer to {args['out_path']}"}]}


rates_server = create_sdk_mcp_server(name="rates", version="1.0.0", tools=[convert_currency])
speech_server = create_sdk_mcp_server(name="speech", version="1.0.0", tools=[transcribe_audio, speak_text])
ALLOWED = ["mcp__rates__convert_currency", "mcp__speech__transcribe_audio", "mcp__speech__speak_text"]
MAX_TURNS = 8  # transcribe, convert, speak, final answer = 4 turns (first run used 6 counting overhead); two spare

ANSWER_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {"amount": {"type": ["number", "null"]}, "currency": {"type": "string"}},
        "required": ["amount", "currency"],
        "additionalProperties": False,
    },
}

# The two cases. `check` is (amount, source, target): what a correct answer is judged against.
CASES = {
    "eur": {"text": "I have fifty pounds. How much is that in euros?", "check": (50, "GBP", "EUR")},
    "yen": {"text": "I have fifty pounds. How much is that in Japanese yen?", "check": (50, "GBP", "JPY")},
}


def check_answer(structured: dict | None, amount: float, source: str, target: str) -> str:
    """Judged against the rate table, never against the model (same rule as block 3.1)."""
    if structured is None:
        return "WRONG: no structured answer came back"
    rate = RATES.get((source, target))
    given = structured.get("amount")
    if rate is None:  # no rate exists, so the only honest amount is null; any number was invented
        return "correct: null, as there is no rate" if given is None else f"WRONG: invented {given}"
    if given is None:
        return "WRONG: null, but a rate exists"
    expected = round(amount * rate, 2)
    if structured.get("currency") != target:
        return f"WRONG: currency {structured.get('currency')}, expected {target}"
    return f"correct: {expected} {target}" if abs(given - expected) <= 0.01 else f"WRONG: {given}, expected {expected}"


async def run_once(wav: Path, answer_wav: Path | None, case: dict, model: str, verbose: bool) -> str:
    speak_step = (f"Then speak a one-sentence answer aloud, saving it to {answer_wav}. "
                  if answer_wav else "Do not speak the answer aloud. ")
    prompt = (f"A caller has left a voice message at {wav}. Transcribe it, work out what they are asking, "
              f"and answer it using the tools. {speak_step}"
              "If the conversion cannot be done, say so and give no amount.")
    options = build_options(
        model, extra_mcp_servers={"rates": rates_server, "speech": speech_server},
        extra_allowed_tools=ALLOWED, max_turns=MAX_TURNS, output_format=ANSWER_SCHEMA,
    )
    verdict, structured = "WRONG: run failed", None
    trace = []
    try:
        async for m in query(prompt=prompt, options=options):
            trace.append(str(m))
            if not verbose:
                if isinstance(m, ResultMessage):
                    structured = m.structured_output
                continue
            if isinstance(m, AssistantMessage):
                for b in m.content:
                    if isinstance(b, ToolUseBlock):
                        print(f"  [routed to] {b.name}({b.input})")
                    elif isinstance(b, TextBlock):
                        print(f"  [model says] {b.text}")
            elif isinstance(m, UserMessage) and isinstance(m.content, list):
                for b in m.content:
                    if isinstance(b, ToolResultBlock):
                        print(f"  [tool result] {b.content}")
            elif isinstance(m, ResultMessage):
                structured = m.structured_output
                print(f"  [structured] {structured}   [turns] {m.num_turns}   [cost] ${m.total_cost_usd:.4f}")
        verdict = check_answer(structured, *case["check"])
    except Exception as exc:
        verdict = f"WRONG: run failed ({exc})"
    (HERE / "last_trace.json").write_text(json.dumps(trace, indent=1))
    return verdict


async def main(args) -> None:
    case = CASES[args.case]
    if args.question_wav:
        wav = Path(args.question_wav)
    else:
        wav = HERE / f"question_{args.case}.wav"
        if not wav.exists():  # cached, so repeats do not spend Groq's 100-a-day speech quota
            error = await synthesise(case["text"], wav)
            if error:
                raise SystemExit(error + "\n(Is GROQ_API_KEY set in this terminal?)")
    print(f"caller audio: {wav.name}  (case: {args.case}, model: {args.model}, repeats: {args.repeats})")
    verdicts = []
    for i in range(args.repeats):
        answer_wav = HERE / "answer.wav" if args.repeats == 1 else None
        print(f"\n--- run {i + 1} of {args.repeats} ---")
        v = await run_once(wav, answer_wav, case, args.model, verbose=args.repeats == 1 or args.verbose)
        print(f"[check] {v}")
        verdicts.append(v)
    right = sum(v.startswith("correct") for v in verdicts)
    print(f"\n=== {right} of {args.repeats} correct ({args.case}) ===")
    if args.repeats == 1 and (HERE / "answer.wav").exists():
        print("Spoken answer saved to answer.wav (open it to listen).")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Voice currency assistant: one command, end to end.")
    p.add_argument("--case", choices=CASES, default="eur")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--model", default="claude-haiku-4-5")
    p.add_argument("--question-wav", default=None, help="use your own recording instead of the simulated caller")
    p.add_argument("--verbose", action="store_true", help="print the trace on every repeat, not just a single run")
    asyncio.run(main(p.parse_args()))
