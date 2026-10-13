# AI Use Record

| Date | Tool / model | Prompt (one line) | What came back (one line) | Tokens / usage |
|------|-------------|--------------------|---------------------------|-----------------|
| 24 Sep 2026 | Claude Code, Opus 5.5 | "What date format does this repository use?" then "Commit CLAUDE.md with a clear message, then push it" | Correctly read CLAUDE.md, proposed and ran git add/commit/push with Co-Authored-By trailer | Input 14, Output 1.3k, Cache read 120.7k, Cache write 25.9k (148.0k total tokens, 2 sessions) |
| 24 Sep 2026 | OpenCode, Gemma 4 26B A4B IT (Google free tier) | "What date format does this repository use?" | Started correctly (found CLAUDE.md via ls -R), but hit free-tier quota before answering | Quota exceeded: 16,000 input token limit; not yet completed |

## Fri 25 September 2026 — Week 2 tutorial (bars and stripes)

- **Tool:** Claude (Cowork chat), used as a step-by-step guide through the notebook and to explain outputs.
- **What it did:** supplied the code for TODOs 3 and 5, explained each output, and drafted the final write-up from my own observations and numbers, which I reviewed and pasted in.
- **What I did:** ran every cell myself and checked the outputs against the lecture's own figures: final loss 26.38 (latent_dim=2) vs 14.70 (latent_dim=16), copy check 3.39 for a fresh sample vs 0.00 for a reconstruction, samples drawn with seeds 6 and 123.
- **Usage:** no token count available from the chat interface; one session of roughly an hour.

## Tue 29 September to Mon 12 October 2026 — Block 3.1 tutorial (tool calling and the agent loop)

- **Tool:** Claude (Cowork chat), used as a step-by-step guide through the tutorial in my own Terminal, and to explain outputs.
- **What it did:** put the Lecture 3.1 slides into Notion with notes; told me which commands to run and what to look for; drafted the currency tool (description, schema, handler), the answer schema, `check_answer()` and the null-amount change; corrected its own draft once (the handler had to return `58.50`, not `58.5`).
- **What I did:** ran every command and script myself; made a prediction before most experiments, and several were wrong (I expected the model, not the harness, to refuse a tool missing from the allow-list; that both turn limits would fail because of the yen question; and that the harness would loudly flag the broken schema); chose the yen rule (any number returned for a pair with no rate is WRONG, because it cannot have come from the tool); wrote my own three-sentence explanation of `tools=[]` and `setting_sources=[]` and my own observations and predictions (Claude did not draft them); read each result and pasted it back.
- **My results:** `tools=[]` removed: 1 tool became 26, cost $0.017002 to $0.045757, cache creation 1,257 to 4,040 tokens, 2 turns to 3 (the model also called ToolSearch). Haiku cost 0.546 of Sonnet 5 on the same task, not 0.5. Turn limit 1 failed all three questions, 2 finished all three, so I set MAX_TURNS to 3. Tool description: the model called the tool in 5 of 5 runs as shipped, 3 of 5 with an honest description, 0 of 5 once "use the calculate tool" was removed, with 425 in every answer each time. Broken output schema: a quiet failure in 4 of 4 runs (is_error False, structured_output None). After letting `amount` be null, the yen question returned null in 6 of 6 runs, against invented filler in 3 of 3 before.
- **Usage:** no token count available from the chat interface; several sessions over two weeks.

## Mon 12 to Tue 13 October 2026 — Block 3.2 tutorial (what goes in the context)

- **Tool:** Claude (Cowork chat), used as a step-by-step guide through the tutorial in my own Terminal, and to explain outputs.
- **What it did:** put the Lecture 3.2 slides into Notion with notes; found the Canvas files in my Downloads folder and copied them into `tutorials/3.2`; filled in the gaps in `mcp_docs_demo.py` (gaps 3 and 4), `image_context.py` (all 3) and `rag_demo.py` (all 3) after I did gaps 1 and 2 of step 1 with its hints; wrote `mcp_docs_cheaper.py` for step 6; drafted the step 3 explanation (I rewrote it in my own words and it corrected one claim about `_gaps_left()`); and drafted the whole of `tutorials/3.2/writeup.md` from my run outputs. **Claude wrote that write-up, not me; I have not yet reworded it.**
- **What I did:** ran every script myself in Terminal and pasted the outputs back; made my own Groq account and key (it leaked into the chat once, so I revoked it and made a new one); accepted the Orpheus terms in the Groq console; checked the answers against the passages and the lecture's figures.
- **My results:** MCP docs run: turn 1 3,278, turn 2 16,213 (12,935 new), cost $0.139634. Image: predicted 2,442, measured 2,423 (3,856 with, 1,433 without). Speech: "Forty two" came back as " 42". Retrieval: passages added 485 tokens; agentic retrieval cost $0.035142 against $0.015025 for fixed retrieval. Cheaper docs run: turn 1 3,616 (allow-list narrowed: no change) against 2,379 with `disallowed_tools`.
- **Usage:** no token count available from the chat interface; one long session.

