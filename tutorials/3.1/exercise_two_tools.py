"""Block 3.1 exercise: build a second tool, set its limits, and check its answer.

The toy agent has one tool, so the model only ever decides whether to call it. This script gives
it two, so the model also decides which. Then it asks for the answer in a fixed shape, and checks
whether that answer is actually right.

**Five gaps to fill, all marked TODO.** Before anything is sent to the model, the script tests
your tool and your check on known inputs, and stops with a message naming whatever is still open
or still wrong. Nothing runs until all five pass.

Using an agent for this is expected. Ask it to draft each gap, then read what it wrote and check
it against the run. A description that reads well and routes badly is the interesting case.

Run it:

    uv run --with claude-agent-sdk python exercise_two_tools.py
    uv run --with claude-agent-sdk python exercise_two_tools.py --max-turns 1

Needs `toy_agent.py` in the same folder, and the `claude` command installed and logged in.
"""

import argparse
import asyncio

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

# Fixed rates, so the tool needs no network and no API key. Real rates move; these do not.
RATES = {
    ("GBP", "EUR"): 1.17,
    ("EUR", "GBP"): 0.85,
    ("GBP", "USD"): 1.27,
    ("USD", "GBP"): 0.79,
    ("EUR", "USD"): 1.08,
    ("USD", "EUR"): 0.92,
}


# TODO 1: write the whole tool, both halves.
#
# The contract, which is all the model ever reads:
#   name:         one word, lower case, no spaces.
#   description:  the four-point checklist from the lecture. What it does. When to use it and
#                 when not to. What it returns, and in what units. What it refuses.
#   input schema: a dictionary of argument names and types, like add's {"a": float, "b": float}.
#                 It must name exactly the three arguments the handler reads, listed below.
#
# The handler, which is all the harness ever runs:
#   - read args["amount"], args["from_currency"] and args["to_currency"]
#   - look the pair of codes up in RATES, in upper case, so "gbp" works as well as "GBP"
#   - a known pair: return the converted amount, rounded to 2 decimal places, as one text block,
#     the same shape add returns in toy_agent.py
#   - an unknown pair: return a text block saying so, and add "is_error": True beside "content"
@tool(
    "convert_currency",
    "Convert a money amount from one currency to another using fixed exchange rates. "
    "Use it whenever the question asks how much money in one currency is worth in another. "
    "Do not use it for plain arithmetic with no currencies involved; use the add tool for that. "
    "Returns the converted amount as a number in the target currency, rounded to 2 decimal "
    "places, as text (for example '58.50'). Supports only GBP, EUR and USD, in any direction "
    "between them. For any other currency, or the same currency twice, it returns an error "
    "and no amount: it never guesses a rate.",
    {"amount": float, "from_currency": str, "to_currency": str},
)
async def convert_currency(args: dict) -> dict:
    amount = args["amount"]
    pair = (args["from_currency"].upper(), args["to_currency"].upper())
    rate = RATES.get(pair)
    if rate is None:
        return {
            "content": [{"type": "text", "text": f"No rate available for {pair[0]} to {pair[1]}."}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": f"{amount * rate:.2f}"}]}


rates_server = create_sdk_mcp_server(name="rates", version="1.0.0", tools=[convert_currency])

# TODO 2: name the new tool on the allow-list, so the harness is allowed to run it.
# The full name is mcp__<server>__<tool>. The server above is called "rates".
# Worth getting wrong on purpose once, with a name that does not exist: the model still proposes
# the call, and the harness is what refuses it. Watch what the answer schema does then.
ALLOWED_TOOLS: list[str] = ["mcp__rates__convert_currency"]

# TODO 3: set a stop condition. How many model turns should one question be allowed?
# Guess first. Then test your guess: run with --max-turns 1, then 2, then 3, and write down for
# each question whether it finished and what [turns] it reported. Pick the smallest value that
# lets every question finish, plus one. Too low and a correct run fails; too high and a run that
# goes wrong keeps paying.
MAX_TURNS: int | None = 3

# TODO 4: describe the shape the final answer must arrive in, so the value can be read straight
# out instead of scraped from a sentence. Two fields: the converted amount as a number, and the
# currency it is in as a string. Both required.
ANSWER_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {"amount": {"type": ["number", "null"]}, "currency": {"type": "string"}},
        "required": ["amount", "currency"],
        "additionalProperties": False,
    },
}

# The three questions. Only the second and third ask for a structured answer, and each of those
# carries what a correct answer would be, so check_answer() has something to compare against.
QUESTIONS = [
    {"text": "What is 17 plus 25?"},
    {"text": "I have 50 pounds. How much is that in euros?", "check": (50, "GBP", "EUR")},
    {"text": "I have 50 pounds. How much is that in Japanese yen?", "check": (50, "GBP", "JPY")},
]


# TODO 5: check the answer against the rate table, not against the model.
#
# `structured` is the model's structured answer, a dictionary like {"amount": 58.5,
# "currency": "EUR"}, or None if nothing came back. Return a string that starts with "correct"
# or with "WRONG", followed by why. Three cases:
#   - the pair is in RATES: correct only if the currency is `target` and the amount is within
#     0.01 of amount times the rate, rounded to 2 decimal places
#   - the pair is not in RATES: the tool cannot answer it, so what counts as correct? Decide, and
#     say in a comment why
#   - structured is None: say so
def check_answer(structured: dict | None, amount: float, source: str, target: str) -> str:
    if structured is None:
        return "WRONG: no structured answer came back (a failed run, not a refusal)"
    rate = RATES.get((source, target))
    given = structured.get("amount")
    if rate is None:
        # No rate in the table, so the honest answer is "no amount": null.
        # Any number here was invented. A missing answer is a failure, not a refusal.
        if given is None:
            return f"correct: amount is null, and the table has no {source} to {target} rate"
        return f"WRONG: returned {given}, but the table has no {source} to {target} rate"
    if given is None:
        return f"WRONG: amount is null, but the table does have a {source} to {target} rate"
    expected = round(amount * rate, 2)
    if structured.get("currency") != target:
        return f"WRONG: currency is {structured.get('currency')}, expected {target}"
    if abs(given - expected) > 0.01:
        return f"WRONG: amount is {given}, expected {expected}"
    return f"correct: {expected} {target}"


def check_todos(max_turns_given: bool) -> None:
    """Tests every gap on known inputs before any model call, and names what is still open."""
    problems = []
    if not convert_currency.name:
        problems.append("TODO 1: the tool's name")
    if not convert_currency.description:
        problems.append("TODO 1: the tool's description")
    if set(convert_currency.input_schema) != {"amount", "from_currency", "to_currency"}:
        problems.append("TODO 1: the input schema must name amount, from_currency and to_currency")
    try:
        known = asyncio.run(
            convert_currency.handler({"amount": 50, "from_currency": "gbp", "to_currency": "EUR"})
        )
        unknown = asyncio.run(
            convert_currency.handler({"amount": 50, "from_currency": "GBP", "to_currency": "JPY"})
        )
        if known["content"][0]["text"] != "58.50":
            problems.append(f"TODO 1: 50 gbp to EUR should give '58.50', gave {known['content']}")
        if not unknown.get("is_error"):
            problems.append("TODO 1: an unknown pair should come back with is_error set to True")
    except NotImplementedError:
        problems.append("TODO 1: the tool's handler")
    except Exception as exc:
        problems.append(f"TODO 1: the handler crashed on a test input: {exc!r}")
    if not ALLOWED_TOOLS:
        problems.append("TODO 2: the allow-list entry")
    if MAX_TURNS is None and not max_turns_given:
        problems.append("TODO 3: a stop condition, or try one with --max-turns")
    if not ANSWER_SCHEMA["schema"]["properties"]:
        problems.append("TODO 4: the answer schema")
    right = check_answer({"amount": 58.5, "currency": "EUR"}, 50, "GBP", "EUR")
    wrong = check_answer({"amount": 0, "currency": "EUR"}, 50, "GBP", "EUR")
    if not right.startswith("correct") or not wrong.startswith("WRONG"):
        problems.append("TODO 5: check_answer() should pass 58.5 EUR and fail 0 EUR for 50 GBP")
    if problems:
        raise SystemExit("Still to fill in or fix:\n  " + "\n  ".join(problems))


async def ask(question: dict, max_turns: int) -> None:
    """One run. Prints which tool the model chose, what came back, and the check."""
    structured = "check" in question
    extra = {"output_format": ANSWER_SCHEMA} if structured else {}
    options = build_options(
        "claude-sonnet-5",
        extra_mcp_servers={"rates": rates_server},
        extra_allowed_tools=ALLOWED_TOOLS,
        max_turns=max_turns,
        **extra,
    )

    print(f"\n--- {question['text']!r} (schema: {'yes' if structured else 'no'}) ---")
    try:
        async for message in query(prompt=question["text"], options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        print(f"[routed to] {block.name}({block.input})")
                    elif isinstance(block, TextBlock):
                        print(f"[model says] {block.text}")
            elif isinstance(message, UserMessage) and isinstance(message.content, list):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        print(f"[tool result] {block.content}")
            elif isinstance(message, ResultMessage):
                print(f"[structured] {message.structured_output}")
                print(f"[turns] {message.num_turns}   [cost] ${message.total_cost_usd:.6f}")
                if structured:
                    print(f"[check] {check_answer(message.structured_output, *question['check'])}")
    except Exception as exc:  # max_turns and schema failures arrive as exceptions
        print(f"[run failed] {exc}")


async def main(max_turns: int) -> None:
    for question in QUESTIONS:
        await ask(question, max_turns)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Two tools, one limit, one check.")
    parser.add_argument("--max-turns", type=int, default=None,
                        help="override MAX_TURNS for one run, for the stop-condition experiment")
    args = parser.parse_args()
    check_todos(max_turns_given=args.max_turns is not None)
    asyncio.run(main(args.max_turns if args.max_turns is not None else MAX_TURNS))
