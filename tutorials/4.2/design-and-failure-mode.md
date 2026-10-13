# Day 4 take-home: design paragraph and failure mode (Subelement 2 platform)

**Status: first draft written by Claude from my real runs (voice_currency.py run on 13 October 2026: 6 turns, $0.0173, correct; yen case 10 of 10 correct). Not yet reworded in my own voice.**

## Design paragraph

I chose a tool loop for a voice currency assistant: the caller's audio is transcribed, the amount is converted with a `convert_currency` tool (fixed GBP, EUR and USD rates), and the answer is spoken back, with all three tools served over MCP. The task shape that fits is one bounded external step inside the model's own reasoning, where the order of tool calls (transcribe, convert, speak) depends on what the caller says, so a fixed plan is not needed. The cost is one model call per step: a single question took 6 turns and $0.0173, against one call for single-shot, which cannot hear audio or look up a rate at all. I rejected plan-then-execute because a wrong first step, such as a mis-transcribed currency, would carry through the frozen plan silently, whereas the loop reads each tool result before deciding what to do next. I would check the choice by running the same cases 10 times, counting correct answers against the rate table, and reporting the range, as in block 4.1.

## Failure mode and measure

**Failure:** when the caller asks for a pair with no rate (pounds to Japanese yen), the agent invents an amount instead of saying it cannot convert. In block 3.1 this happened in 3 of 3 runs before I let `amount` be null.

**Measure:** run `uv run --with claude-agent-sdk --with httpx python voice_currency.py --case yen --repeats 10` and count runs where `check_answer()` returns "correct: null". Any number returned for GBP to JPY counts as a failure, because the tool refuses that pair, so it cannot have come from the tool. Report the count out of 10 and, if it is not 10, read the failing runs to see whether the model ignored the tool error or the transcription changed the question.

**Result (13 October 2026, claude-haiku-4-5, one simulated caller recording, 10 runs):** 10 of 10 correct: the agent returned null every time for GBP to JPY. So this failure did not show up in this set-up. The claim this supports is narrow: with this tool description, this schema (amount may be null) and this one spoken wording, Haiku 4.5 did not invent a yen amount in 10 runs. It does not show it never would: one wording, one voice, one model, 10 runs. Next checks: different spoken wordings, a noisy or accented recording through Whisper, a currency the tool never mentions (e.g. Swiss francs), and the 3.1 version of the schema without null allowed, to confirm the check can fail at all.
