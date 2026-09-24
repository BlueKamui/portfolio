# AI Use Record

| Date | Tool / model | Prompt (one line) | What came back (one line) | Tokens / usage |
|------|-------------|--------------------|---------------------------|-----------------|
| 24 Sep 2026 | Claude Code, Opus 5.5 | "What date format does this repository use?" then "Commit CLAUDE.md with a clear message, then push it" | Correctly read CLAUDE.md, proposed and ran git add/commit/push with Co-Authored-By trailer | Input 14, Output 1.3k, Cache read 120.7k, Cache write 25.9k (148.0k total tokens, 2 sessions) |
| 24 Sep 2026 | OpenCode, Gemma 4 26B A4B IT (Google free tier) | "What date format does this repository use?" | Started correctly (found CLAUDE.md via ls -R), but hit free-tier quota before answering | Quota exceeded: 16,000 input token limit; not yet completed |
