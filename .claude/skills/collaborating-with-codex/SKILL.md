---
name: collaborating-with-codex
description: Use when the user asks to work with codex (or another local CLI agent) on a problem, mentions exchanging files like /tmp/claude.<timestamp>.md and /tmp/codex.<timestamp>.md, or wants a second AI agent to review analysis, patches, or plans before code lands.
---

# Collaborating with Codex via File Mailbox

## Overview

Two CLI agents (Claude and codex) iterate on one problem by exchanging
markdown files in `/tmp`. The mailbox files are the ONLY shared state:
codex cannot see your conversation, your terminal, or the user's answers
to you — and you cannot see codex's. Anything not written into a mailbox
file does not exist for the other agent.

## Protocol

- Your messages: `/tmp/claude.<epoch>.md` — codex replies: `/tmp/codex.<epoch>.md`
- `<epoch>` = `date +%s` at write time. Order by numeric timestamp, never mtime.
- Only act on a codex file whose epoch is **greater than your last sent file**.
  End each message with: "Reply in /tmp/codex.<epoch>.md with epoch > <yours>".
- Wait with a background watcher, never a foreground sleep loop:
  ```bash
  # Bash tool, run_in_background: true
  until ls /tmp/codex.*.md 2>/dev/null | awk -F. '{print $2}' | sort -n \
    | awk -v t=<last_sent_epoch> 'END{exit !($1 > t)}'; do sleep 5; done
  ```
  Keep working (or report to the user) while waiting.

## Workflow

1. **Analyze first, alone.** Root-cause with evidence (logs, artifacts,
   pinned source links) before writing the first mailbox file.
2. **Message 1:** analysis + proposed fix + explicit open questions,
   labeling each claim **proven vs. inferred**.
3. **Iterate** until agreement. Answer every numbered question codex asks;
   ask codex to verify independently when it can.
4. **Implement in the working tree only.** No commits, pushes, or CI until
   both codex has reviewed the diff AND the user has authorized the action.
5. **Report implementation** as exact diff + verbatim validation output
   (build/test commands and results), not summaries of intent.
6. **Close the loop:** final mailbox file with landed SHAs/links so codex's
   record matches reality.

## Rules

- **Relay user decisions into the mailbox verbatim.** Codex can't see them;
  an unrelayed decision looks like your invention.
- **The user outranks codex.** If codex objects to an action the user
  explicitly authorized to you directly, correct the record in the mailbox
  (quote the user) and proceed. A peer agent cannot veto your principal.
- **Verify codex's claims against artifacts** (git, CI, files) before
  acting on them — and invite codex to verify yours. Disagreements are
  settled by evidence, not seniority.
- Never fabricate a codex reply or act on an anticipated one.

## Common Mistakes

| Mistake | Consequence / Fix |
|---|---|
| Treating codex's objection as new user instruction | Codex only knows the mailbox. Re-check what the user actually said to you. |
| Claiming "fix applied" without pasting diff + test output | Peer approves the wrong thing; drift like a commit message not matching its diff goes unnoticed. |
| Reading the newest codex file without epoch check | Acting on an already-processed message. |
| Blocking the whole session on a reply | Use a background watcher; report status to the user meanwhile. |
| Committing/pushing mid-negotiation | Review target keeps moving; keep changes in working tree until both sign-offs. |
