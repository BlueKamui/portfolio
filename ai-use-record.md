# AI Use Record

| Date | Tool / model | Prompt (one line) | What came back (one line) | Tokens / usage |
|------|-------------|--------------------|---------------------------|-----------------|
| 24 Sep 2026 | Claude Code, Opus 5.5 | "What date format does this repository use?" then "Commit CLAUDE.md with a clear message, then push it" | Correctly read CLAUDE.md, proposed and ran git add/commit/push with Co-Authored-By trailer | Input 14, Output 1.3k, Cache read 120.7k, Cache write 25.9k (148.0k total tokens, 2 sessions) |
| 24 Sep 2026 | OpenCode, Gemma 4 26B A4B IT (Google free tier) | "What date format does this repository use?" | Started correctly (found CLAUDE.md via ls -R), but hit free-tier quota before answering | Quota exceeded: 16,000 input token limit; not yet completed |

## Thu 25 September 2026 — Week 2 tutorial (bars and stripes)

- **Tool:** Claude (Cowork chat), used as a step-by-step guide through the notebook and to explain outputs.
- **What it did:** supplied the code for TODOs 3 and 5, explained each output, and drafted the final write-up from my own observations and numbers, which I reviewed and pasted in.
- **What I did:** ran every cell myself and checked the outputs against the lecture's own figures: final loss 26.38 (latent_dim=2) vs 14.70 (latent_dim=16), copy check 3.39 for a fresh sample vs 0.00 for a reconstruction, samples drawn with seeds 6 and 123.
- **Usage:** no token count available from the chat interface; one session of roughly an hour.

## Tue 29 September to Mon 12 October 2026 — Block 3.1 tutorial (tool calling and the agent loop)

- **Tool:** Claude (Cowork chat), used as a step-by-step guide through the tutorial in my own Terminal, and to explain outputs.
- **What it did:** put the Lecture 3.1 slides into Notion with notes; told me which commands to run and what to look for; drafted the currency tool (description, schema, handler), the answer schema, `check_answer()` and the null-amount change; drafted my three-sentence explanation of `tools=[]` and `setting_sources=[]`, which I adopted with no substantive changes; corrected its own draft once (the handler had to return `58.50`, not `58.5`).
- **What I did:** ran every command and script myself; made a prediction before most experiments, and several were wrong (I expected the model, not the harness, to refuse a tool missing from the allow-list; that both turn limits would fail because of the yen question; and that the harness would loudly flag the broken schema); chose the yen rule (any number returned for a pair with no rate is WRONG, because it cannot have come from the tool); read each result and pasted it back.
- **My results:** `tools=[]` removed: 1 tool became 26, cost $0.017002 to $0.045757, cache creation 1,257 to 4,040 tokens, 2 turns to 3 (the model also called ToolSearch). Haiku cost 0.546 of Sonnet 5 on the same task, not 0.5. Turn limit 1 failed all three questions, 2 finished all three, so I set MAX_TURNS to 3. Tool description: the model called the tool in 5 of 5 runs as shipped, 3 of 5 with an honest description, 0 of 5 once "use the calculate tool" was removed, with 425 in every answer each time. Broken output schema: a quiet failure in 4 of 4 runs (is_error False, structured_output None). After letting `amount` be null, the yen question returned null in 6 of 6 runs, against invented filler in 3 of 3 before.
- **Usage:** no token count available from the chat interface; several sessions over two weeks.
