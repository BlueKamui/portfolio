"""Block 3.2, tutorial step 5: retrieval-augmented generation (RAG), built by hand on a small manual.

**Retrieval-augmented generation (RAG)**: at question time, find the passages of an outside
collection that match the question, put them in the context, and have the model answer from them.
This script does every step on one small file, `workshop_manual.txt`, the handbook of a bike
workshop invented for this course, so no model can know its prices from training:

    once, before any question:  cut the manual into chunks, and turn each chunk into a vector
    for every question:         turn the question into a vector the same way, score every chunk
                                by cosine similarity, put the best k in the prompt, ask the model

The vectors (embeddings) are computed on your own machine by `fastembed`, with the small open model
BAAI/bge-small-en-v1.5: free, no key, no GPU. The first run downloads that model, about 65 MB, into
your system's temporary folder, and may print a warning about unauthenticated requests to the
Hugging Face Hub: that warning is harmless. The answer step goes through the Claude Agent SDK, on the
same login as every other script in this folder.

**This script has three gaps in it, marked TODO, and it will not run until you fill them**:
`cosine_similarity()`, which scores how close two vectors point; `top_k()`, which picks the best
chunks; and `build_prompt()`, which writes what the model will actually read. The script tests all
three on known inputs before it downloads, embeds or sends anything. Use your agent to help, and
read what it writes before you accept it.

Run it:

    uv run --with claude-agent-sdk --with fastembed python rag_demo.py
    uv run --with claude-agent-sdk --with fastembed python rag_demo.py --search-only
    uv run --with claude-agent-sdk --with fastembed python rag_demo.py --agentic
    uv run --with claude-agent-sdk --with fastembed python rag_demo.py --k 1 --chunk-words 60

The default run asks the same question twice, first as the plain question and then with the best
passages in the prompt, and prints both answers and what each cost in tokens. `--search-only` stops
after the retrieval step, so it makes no model call and costs nothing: use it to try chunk sizes,
values of k and your own questions. `--agentic` gives the same search to the model as a tool,
`search_manual`, and lets the model decide what to search for. `--whole` also asks with the entire
manual in the prompt, for comparison. `--question "..."` asks your own question.
"""

import argparse
import asyncio
import math
from pathlib import Path

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
MANUAL_PATH = HERE / "workshop_manual.txt"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
CHUNK_WORDS = 0   # 0: one chunk per section. Any other number: cut every that many words
K = 3             # how many chunks go into the prompt
QUESTION = "How much is a Full Service at Spoke and Sprocket, and when is it ready?"

# Words too common to count as a keyword match, for the keyword column in the results table.
STOPWORDS = {
    "a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "how", "i", "if", "in", "is",
    "it", "my", "of", "on", "or", "the", "to", "what", "when", "will", "with", "you", "your",
}


def split_into_chunks(text: str, words_per_chunk: int = 0) -> list[dict]:
    """Cuts the manual into chunks. Each chunk remembers the section it starts in, so an answer can
    name its source.

    With `words_per_chunk` at 0, every section of the manual becomes one chunk. A section starts at
    a line beginning with "# ", and the heading stays in the chunk's text. With a number instead,
    the manual is cut every that many words, ignoring sentences and sections: the simplest way to
    chunk a document, and a common one.
    """
    words, sections = [], []
    section = "Title page"
    for line in text.splitlines():
        if line.startswith("# "):
            section = line[2:].strip()
        for word in line.split():
            words.append(word)
            sections.append(section)
    if words_per_chunk:
        spans = [(start, start + words_per_chunk) for start in range(0, len(words), words_per_chunk)]
    else:
        spans, start = [], 0
        for i in range(1, len(words) + 1):
            if i == len(words) or sections[i] != sections[start]:
                spans.append((start, i))
                start = i
    return [
        {"number": number, "section": sections[start], "text": " ".join(words[start:end])}
        for number, (start, end) in enumerate(spans, start=1)
    ]


# --- TODO 1 of 3 -------------------------------------------------------------------------------
# How close are two vectors? Cosine similarity compares the directions they point in, not their
# lengths:
#
#     cosine(a, b) = (a . b) / (length of a  *  length of b)
#
# where a . b multiplies the two lists position by position and adds up the products, and the
# length of a is the square root of a . a. The result is 1 for the same direction, 0 for a right
# angle. The worked example on the step 5 slide: [3, 4] and [4, 3] give 24 / (5 * 5) = 0.96.
# Plain Python is enough: sum(), zip() and math.sqrt(). Return a float.
def cosine_similarity(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    length_a = math.sqrt(sum(x * x for x in a))
    length_b = math.sqrt(sum(y * y for y in b))
    if length_a == 0 or length_b == 0:
        return 0.0  # a zero vector has no direction, so call it no similarity
    return float(dot / (length_a * length_b))


# --- TODO 2 of 3 -------------------------------------------------------------------------------
# Which chunks go into the prompt? `scores` holds one score per chunk, in chunk order. Return the
# positions of the k highest scores, highest first. For [0.2, 0.9, 0.5, 0.7] and k = 2 that is
# [1, 3]. Hint: sort the positions, range(len(scores)), by their score.
def top_k(scores: list[float], k: int) -> list[int]:
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return ranked[:k]


# --- TODO 3 of 3 -------------------------------------------------------------------------------
# What will the model actually read? Return one string holding three things:
#
#   1. an instruction: answer only from the passages below, name the section each fact came from,
#      and say so if the passages do not contain the answer
#   2. every chunk: its number, its section and its text. Each chunk is a dict with the keys
#      "number", "section" and "text"
#   3. the question
#
# The wording is yours. The script prints the prompt before it sends it, so read it.
def build_prompt(question: str, chunks: list[dict]) -> str:
    instruction = (
        "Answer the question using only the passages from the Spoke and Sprocket workshop "
        "handbook below. After each fact, name the section it came from. If the passages do not "
        "contain the answer, say so rather than guessing."
    )
    passages = "\n\n".join(
        f"[{chunk['number']}] Section: {chunk['section']}\n{chunk['text']}" for chunk in chunks
    )
    return f"{instruction}\n\n{passages}\n\nQuestion: {question}"


def check_todos() -> None:
    """Tests the three gaps on known inputs, before anything is embedded or sent to a model."""
    problems = []
    try:
        same_direction = cosine_similarity([1, 2], [2, 4])
        right_angle = cosine_similarity([1, 0], [0, 1])
        worked_example = cosine_similarity([3, 4], [4, 3])
        if not (abs(same_direction - 1) < 1e-6 and abs(right_angle) < 1e-6
                and abs(worked_example - 0.96) < 1e-6):
            problems.append(
                "TODO 1: cosine_similarity() should give 1 for [1, 2] and [2, 4], 0 for [1, 0] and "
                f"[0, 1], and 0.96 for [3, 4] and [4, 3]. It gave {same_direction}, {right_angle} "
                f"and {worked_example}."
            )
    except Exception as exc:  # an unfilled gap usually fails here first
        problems.append(f"TODO 1: cosine_similarity() crashed on a test input: {exc!r}")
    try:
        if top_k([0.2, 0.9, 0.5, 0.7], 2) != [1, 3]:
            problems.append(
                "TODO 2: top_k([0.2, 0.9, 0.5, 0.7], 2) should give [1, 3], the positions of the "
                "two highest scores, highest first."
            )
    except Exception as exc:
        problems.append(f"TODO 2: top_k() crashed on a test input: {exc!r}")
    test_chunks = [
        {"number": 4, "section": "Brakes", "text": "Pads are replaced below 1.5 mm."},
        {"number": 9, "section": "Loan bikes", "text": "A loan bike needs a 50 pound deposit."},
    ]
    prompt = build_prompt("How thin can a brake pad get?", test_chunks)
    missing = [
        piece for piece in ["How thin can a brake pad get?", "Pads are replaced below 1.5 mm.",
                            "A loan bike needs a 50 pound deposit.", "Brakes", "Loan bikes"]
        if piece not in (prompt or "")
    ]
    if missing:
        problems.append(
            "TODO 3: build_prompt() should contain the question, every chunk's text and every "
            f"chunk's section. Missing: {missing}"
        )
    if problems:
        raise SystemExit("Still to fill in or fix:\n  " + "\n  ".join(problems))


def keyword_hits(question: str, text: str) -> int:
    """How many of the question's words also appear in the chunk: plain keyword search."""
    def words(s: str) -> set[str]:
        return {w.strip(".,?!:;'\"()").lower() for w in s.split()} - STOPWORDS
    return len(words(question) & words(text))


def load_embedder():
    # Imported here, not at the top, so the self-test runs before anything is downloaded.
    from fastembed import TextEmbedding

    print(f"[embedding model] {EMBEDDING_MODEL}, running on this machine")
    return TextEmbedding(EMBEDDING_MODEL)


def build_index(chunks: list[dict], embedder) -> list:
    """The part done once: one vector per chunk, 384 numbers each, kept for every question."""
    return list(embedder.embed([chunk["text"] for chunk in chunks]))


def retrieve(question: str, chunks: list[dict], vectors: list, embedder, k: int) -> list:
    """The part done for every question: embed it the same way, score every chunk, keep the best k."""
    question_vector = next(iter(embedder.embed([question])))
    scores = [cosine_similarity(question_vector, vector) for vector in vectors]
    return [(scores[i], chunks[i]) for i in top_k(scores, k)]


def show_results(question: str, results: list, total: int) -> None:
    print(f"\n--- retrieval: the best {len(results)} of {total} chunks ---")
    print(f"question: {question}\n")
    print(f"{'rank':<6}{'score':<8}{'shared words':<14}{'chunk':<7}section")
    for rank, (score, chunk) in enumerate(results, start=1):
        hits = keyword_hits(question, chunk["text"])
        print(f"{rank:<6}{score:<8.3f}{hits:<14}{'[' + str(chunk['number']) + ']':<7}"
              f"{chunk['section']}")


def show_keyword_best(question: str, chunks: list[dict]) -> None:
    """What plain keyword search would have picked, for comparison with the table above."""
    best = max(keyword_hits(question, chunk["text"]) for chunk in chunks)
    tied = [f"[{chunk['number']}]" for chunk in chunks if keyword_hits(question, chunk["text"]) == best]
    if len(tied) == 1:
        print(f"\nkeyword search alone: {tied[0]} shares the most words with the question, {best}")
    else:
        print(f"\nkeyword search alone: {len(tied)} chunks tie for the most shared words, {best} "
              f"each: {' '.join(tied)}")


def context_size(usage: dict) -> int:
    return (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0))


async def ask(prompt: str, label: str) -> int:
    """One plain model call, no tool needed. Prints the answer and returns the tokens read."""
    read = 0
    async for message in query(prompt=prompt, options=build_options(None)):
        if isinstance(message, ResultMessage):
            usage = message.usage or {}
            read = context_size(usage)
            print(f"\n[{label}] {read} tokens in, {usage.get('output_tokens')} out, "
                  f"${message.total_cost_usd:.6f}")
            print(f"[model says] {message.result}")
    return read


async def compare(question: str, prompt: str, whole_prompt: str | None) -> None:
    without = await ask(question, "without retrieval: the plain question")
    with_passages = await ask(prompt, "with retrieval: the prompt above")
    print(f"\nthe passages and the instruction added {with_passages - without} tokens")
    if whole_prompt is not None:
        whole = await ask(whole_prompt, "the whole manual in the prompt")
        print(f"\nthe whole manual added {whole - without} tokens")


async def agentic(question: str, chunks: list[dict], vectors: list, embedder, k: int) -> None:
    """The same search, handed to the model as a tool. The model writes the query itself."""

    @tool(
        "search_manual",
        "Search the Spoke and Sprocket workshop handbook, which holds this bike workshop's own "
        "prices, services and policies. Returns the most relevant passages, each with its section "
        "name and a similarity score. Use it for any question about this workshop.",
        {"query": str},
    )
    async def search_manual(args: dict) -> dict:
        results = retrieve(args["query"], chunks, vectors, embedder, k)
        text = "\n\n".join(
            f"[{chunk['number']}] Section: {chunk['section']} (score {score:.3f})\n{chunk['text']}"
            for score, chunk in results
        )
        return {"content": [{"type": "text", "text": text}]}

    server = create_sdk_mcp_server(name="manual", version="1.0.0", tools=[search_manual])
    options = build_options(
        None,
        extra_mcp_servers={"manual": server},
        extra_allowed_tools=["mcp__manual__search_manual"],
    )
    prompt = f"{question} Name the section of the handbook each fact came from."
    print(f"\n--- agentic retrieval: the model decides what to search for ---\n{prompt}\n")
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
                    # Only the first line of each passage, so the trace stays readable.
                    text = block.content[0]["text"] if isinstance(block.content, list) else str(block.content)
                    headers = [part.splitlines()[0] for part in text.split("\n\n") if part.startswith("[")]
                    print("[tool result] " + "; ".join(headers))
        elif isinstance(message, ResultMessage):
            usage = message.usage or {}
            print(f"\n[agentic] {message.num_turns} turns, {usage.get('output_tokens')} tokens out, "
                  f"${message.total_cost_usd:.6f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval-augmented generation on a small manual.")
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--k", type=int, default=K, help="how many chunks go into the prompt")
    parser.add_argument("--chunk-words", type=int, default=CHUNK_WORDS,
                        help="0 for one chunk per section, or cut every this many words")
    parser.add_argument("--search-only", action="store_true", help="stop before any model call")
    parser.add_argument("--agentic", action="store_true", help="give the search to the model as a tool")
    parser.add_argument("--whole", action="store_true", help="also ask with the whole manual")
    args = parser.parse_args()

    check_todos()
    if not MANUAL_PATH.is_file():
        raise SystemExit(f"No manual at {MANUAL_PATH}. Download workshop_manual.txt into this folder.")
    text = MANUAL_PATH.read_text(encoding="utf-8")
    chunks = split_into_chunks(text, args.chunk_words)
    embedder = load_embedder()
    vectors = build_index(chunks, embedder)
    size = f"of up to {args.chunk_words} words" if args.chunk_words else "one per section"
    print(f"[index] {len(chunks)} chunks, {size}, one vector of 384 numbers each")

    if args.agentic:
        asyncio.run(agentic(args.question, chunks, vectors, embedder, args.k))
        return

    results = retrieve(args.question, chunks, vectors, embedder, args.k)
    show_results(args.question, results, len(chunks))
    show_keyword_best(args.question, chunks)
    prompt = build_prompt(args.question, [chunk for _, chunk in results])
    print("\n--- the prompt, as it will be sent ---")
    print(prompt)
    if args.search_only:
        return

    whole = None
    if args.whole:
        whole = build_prompt(args.question, [{"number": 1, "section": "the whole handbook",
                                              "text": text}])
    asyncio.run(compare(args.question, prompt, whole))


if __name__ == "__main__":
    main()
