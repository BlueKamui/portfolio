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
