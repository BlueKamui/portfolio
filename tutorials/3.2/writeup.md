# Block 3.2 write-up: what goes in the context

**Status: first draft written by Claude from my real run outputs. I have not yet reworded it in my own voice; the numbers are all from my own terminal runs.**

All scripts are in this folder and run with `uv run --with claude-agent-sdk python <script>.py` from `tutorials/3.2`.

## Step 1: connect a real MCP server and measure what it costs (`mcp_docs_demo.py`)

The docs server connected (`claude-code-docs: connected`), the model made one search call, and I measured the context on each turn.

| | Lecture | Mine |
|---|---|---|
| Turn 1: setup (system prompt, 4 tool descriptions, question) | 3,113 | 3,278 |
| Turn 2: total read | 15,639 | 16,213 |
| Turn 2: new (search result and call) | 12,526 | 12,935 |
| Answer out | 588 | 458 |
| Cost | $0.122859 | $0.139634 |

The search result added about 12,900 tokens, roughly four times the setup, and I typed none of it. Three of the four tools came from the docs server, so their descriptions are paid for on every turn. My numbers differ from the lecturer's for reasons I have not confirmed: the setup is about 165 tokens larger (probably a different model, system prompt or tool set), the search result is live documentation so its length varies between runs, and my answer was shorter. The run also added an unrequested note about unauthorised claude.ai connectors, which is context the harness added, not me.

## Step 2: feed it an image and price it (`image_context.py`)

| | Lecture | Mine |
|---|---|---|
| Predicted (74 x 33 patches) | 2,442 | 2,442 |
| Without the image | 1,010 | 1,433 |
| With the image | 3,484 | 3,856 |
| Measured picture cost | 2,474 | 2,423 |
| Read correctly | yes | yes |

Mine came out 19 tokens (0.8%) under the prediction. The measured cost is the difference between two separate runs, so any difference in the baseline between them shows up as noise. Possible sources, none confirmed: a different cached baseline in each run (my without-image run was larger than the lecturer's), a small overhead around the image block, and the patch rule being an approximation. The rule predicts the cost to within about 1%, but the measurement cannot say why it is a few tokens off.

## Step 3: explain `one_user_turn_with_image()`

`one_user_turn_with_image()` is an async generator that uses `yield` to send a user message as a dictionary instead of returning a string, because `query()` accepts a stream of structured messages and a plain string can only carry text. PNG files contain raw bytes that cannot go directly into a JSON-style message, so `base64.standard_b64encode(...)` converts them into ASCII bytes and `.decode("ascii")` turns them into a normal Python string. The text and the image are two blocks in the same `"content"` list, so the model receives them together in one turn. I can confirm from the code that the content list contains an image block, because `_gaps_left()` fails if there is none. The code does not show why the SDK needs the streaming form, so for that I would have to check its documentation or implementation.

## Step 4: speech out and back in (`speech_tool.py`)

My first run failed with `401 Invalid API Key` because I had typed the export command wrongly, so `GROQ_API_KEY` was never set. After fixing that, Groq returned `400 model_terms_required` for the Orpheus voice model until I accepted its terms once in the Groq console. After that: `Saved 57670 bytes to out.wav`, and Whisper's `[tool result]` was ` 42`.

I said "Forty two" and Whisper returned "42", digits with a leading space. The meaning survived but the exact words did not, because Whisper normalises spoken numbers to digits. A check for the exact words would have flagged this even though the answer was right, which is a small example of the non-text step changing content without any error. The model's retelling of the 401 also pointed at "MCP server settings" when the real cause was an unset terminal variable, which is why I compare against the `[tool result]` line and not `[model says]`.

## Step 5: build retrieval by hand (`rag_demo.py`)

| | Result |
|---|---|
| Top 3 of 13 chunks | [3] Service levels and prices 0.696, [4] How long a service takes 0.674, [10] Loan bikes 0.646 |
| Keyword search alone | picks [4] first (most shared words) |
| Plain question | 1,386 tokens in, "I couldn't find any information about Spoke and Sprocket" |
| With retrieval | 1,871 tokens in, GBP 119, ready at 16:00 on the third working day, both sections named |
| Cost of the passages and instruction | 485 tokens |

I checked one fact by hand: GBP 119 is in chunk [3] ("The Full Service costs 119 pounds") and the 16:00 on the third working day is in chunk [4]. With `--agentic`, the model searched twice, in 3 turns: "Full Service price" (returned [3], then [4] and [10]) and "Full Service turnaround time when ready" (returned [4] at 0.766, higher than the 0.674 in the fixed run). It reached the same answer at $0.035142 against $0.015025 for fixed retrieval, about 2.3 times as much, because each extra turn re-reads the whole conversation.

`retrieve()` runs for every question: it embeds the question, scores it with `cosine_similarity` against every stored chunk vector, and returns the best `k` using `top_k`. The chunk vectors are built once by `build_index()` before any question. The question has to go through the same embedding model as the chunks, because the cosine score compares directions in one shared 384-number space, and a question embedded with a different model would land in a different space and give meaningless scores.

## Step 6: make the docs run cheaper (`mcp_docs_cheaper.py`)

| Run | Turn 1 tokens | Docs tools offered |
|---|---|---|
| A: whole docs server allowed | 3,616 | 3 |
| B: allow-list narrowed to the one tool used | 3,616 | 3 |
| C: B, with the other two removed via `disallowed_tools` | 2,379 | 1 |

Narrowing the allow-list changed turn 1 by 0 tokens. Removing the two unused tools (`query_docs_filesystem_claude_code_docs` and `submit_feedback`) with `disallowed_tools` cut it by 1,237 tokens, about a third of the setup. The allow-list is a permission: it says what the model may call, but the descriptions are still sent. `disallowed_tools` takes the tools out of the context completely. Caveats: one run per setting, and the two tools were removed together, so I cannot say how much each accounts for (about 620 each on average).

## Debrief answers

1. What did the search result add against the setup? About 12,900 tokens against 3,278, and everyone's number differs because the documentation is live and the setup depends on model and harness.
2. Predicted against measured image cost: 2,442 predicted, 2,423 measured.
3. Retrieval: I did not find a question that sent the wrong section to the top. I only ran the lecture's question, so this is still open (extension 3 is untried).
4. Groq: my sentence did not come back word for word ("Forty two" became "42").

## Take-home question

Not yet answered: if my agent has three tools and a task needing several steps, what should decide which tool it tries first and when it is done, and do I control that or leave it to the model?
