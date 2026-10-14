---
name: codex-claude-collab
description: Coordinate iterative review or development work between Claude and Codex using timestamped response files in a shared message directory. Use when the user asks Claude to collaborate with Codex, poll Codex response files, exchange review comments, jointly develop or validate code, or write a done marker when both agents are finished.
---

# Codex-Claude Collaboration

Use this workflow to coordinate with a separate Codex session through response files in a shared message directory.

## Message Location (Required)

**You MUST know the exact directory where messages are exchanged before writing or polling for anything. Never assume `/tmp` or any other path.**

- If the user has not given the exact message location, ask for it and wait for the answer before writing a first prompt or polling. Do not guess, and do not fall back to a default directory.
- Once established, store it in a shell variable for the session's commands: `MSG_DIR=/exact/path/the/user/gave`.
- Use that exact directory for BOTH Claude's outgoing responses and Codex's incoming responses for the entire collaboration.
- Confirm the resolved `MSG_DIR` back to the user in your first status update.
- Never look in a different directory than the one the user specified, even if similarly named files appear elsewhere. Files outside `MSG_DIR` are not part of this collaboration.
- If the user changes the location mid-collaboration, reset the read ledger and re-confirm before continuing.

All paths below use `$MSG_DIR` to mean that exact confirmed directory.

## Protocol

- Write Claude messages to `$MSG_DIR/claude.response.<timestamp>`.
- Expect Codex messages at `$MSG_DIR/codex.response.<timestamp>`.
- Use `date +%s` for new timestamps unless the user specifies another format.
- Treat the timestamp as ordering metadata only. Prefer file modification time (`mtime`) when discovering the newest response, because filenames are only a convention.
- Keep an explicit ledger of Codex response files already read during the current collaboration. Never rely on memory of a single filename.
- Before saying there is no new response, re-list all matching files in `$MSG_DIR` by mtime and compare them against the read ledger.
- Never reprocess an older response as if it were new.
- When the collaboration is finished, create `$MSG_DIR/claude.done`. The file may be empty.
- Do not treat writing a Claude response as completion unless that response is explicitly final and `$MSG_DIR/claude.done` has been created. If the response asks Codex for work, review, fixes, tests, or clarification, immediately continue polling for Codex's next response.
- When the user asks to "read/respond to Codex" in an existing collaboration, that is a request to continue the loop, not a one-shot file write, unless the user explicitly says to only write one response and stop.

## Liveness and Deadlock Avoidance (MOST COMMON FAILURE — read this)

The dominant failure mode is a **mutual-wait deadlock**: both agents believe they are "actively
polling" while each is actually waiting for the other, so nothing ever happens. It is caused by
non-self-contained messages and by misreading the peer's state. These rules prevent it and take
priority over the "keep polling" guidance below.

- **Deliver what you promise, in the SAME message.** Never write "I'll send the diff/patch/output in
  my next message" and then send a different message. If a message says it contains an artifact, that
  artifact — or an explicit, verified on-disk path plus the words "act on this now; no further message
  is coming" — MUST be in that same message. A promise of a future artifact makes the peer wait for it
  forever. This exact mistake (promising a diff, then sending only a file list) has caused a multi-hour
  stall.
- **Paste or attach the REAL artifact.** When handing off code, run the command and include the actual
  `git diff` (or exact, verified file paths) in the message. Do not describe an artifact you did not
  include.
- **End every handoff with an explicit turn marker.** State plainly whose turn it is and the exact next
  action: `OVER TO YOU: review <paths> now and reply with findings`, or `WAITING ON YOU: I need X
  before I can proceed`. Ambiguity about whose turn it is is what stalls the loop.
- **Never infer the peer's state from its private files.** Bookkeeping the peer maintains (e.g. a
  `codex.read-ledger`, or any non-`*.response.*` file) is NOT part of the protocol and may be stale.
  Only the peer's `*.response.*` files are signal. The **absence** of a new response is AMBIGUOUS — it
  often means the peer has already read you and is waiting on YOU. Never conclude "the peer hasn't read
  my message" from a missing response or a stale ledger.
- **When you have been waiting, suspect a deadlock and re-read YOUR OWN last outgoing message.** Ask:
  did it deliver everything I promised? Does it end with an unambiguous, actionable request and a turn
  marker? If not, immediately RE-SEND a corrected, self-contained message instead of waiting longer.
  Most stalls are fixed by resending a complete message, not by waiting.
- **Never BUSY-wait inside one turn; register a durable wake-up instead.** A `sleep`-based poll loop
  only runs while the current turn is active (and Bash caps at ~10 min), so it can NEVER span the gap
  between turns — the moment your turn ends you go idle and stop checking. Do a short bounded in-turn
  poll (a few minutes) to catch a fast reply, and if the peer is still silent, do ONE liveness action
  (the re-read/re-send above). Then, rather than escalating immediately, set up event-driven
  re-invocation so the loop survives unattended — see **Unattended long-running loops** below. Escalate
  to the human only when you are genuinely blocked/ambiguous (e.g. the peer needs a human decision, or
  MSG_DIR was wiped), or when the long poll deadline elapses. Repeatedly relaunching in-turn hour-scale
  background watchers is still the failure — the fix is a scheduled wake-up, not silent watching.

### Unattended long-running loops (durable scheduled wake-ups)

When the user wants the collaboration to keep making progress while they are away (overnight, over a
weekend) WITHOUT having to come back and manually re-kick either agent, do NOT try to hold a turn open
with `sleep` loops — an agent only reasons while a turn is running, and no in-turn loop can span the
idle gap between turns. Use an EXTERNAL scheduler to re-invoke yourself:

- **Register a durable recurring wake-up (`CronCreate` with `durable: true`).** Each firing re-invokes
  you while the REPL is idle, so you re-check MSG_DIR on a cadence without a human. Durable jobs persist
  to `.claude/scheduled_tasks.json` and resume on restart. (Note: recurring cron auto-expires after
  7 days; jobs only fire while the session process is running — tell the user their process must stay
  up, or the job resumes only on next launch.)
- **Make the tick STATELESS where possible.** Decide "is there unprocessed peer input?" by comparing
  `mtime(newest peer *.response.*)` vs `mtime(newest of your own *.response.*)`: peer-newer ⇒ take the
  turn; otherwise it is a quiet tick (you already replied; you are waiting on the peer). This needs no
  per-message ledger that could corrupt across dozens of unattended firings.
- **Back off to bound cost.** Every wake reloads context uncached, which is real token spend over a
  long window. Poll tight when the exchange is active (e.g. ~5 min if either side wrote within the last
  30 min) and relax when quiet (e.g. ~20–30 min). If you implement backoff by changing the cron
  cadence, mutate robustly: CREATE the new-cadence job FIRST, then delete the old one(s) — never leave
  zero pollers. In steady state (cadence unchanged) do NOT touch the job, so a logic error can never
  kill the loop.
- **Set a hard deadline and honor it.** Persist an absolute stop time OUTSIDE MSG_DIR (MSG_DIR is often
  `/tmp`, which can be wiped); at each tick, if past the deadline, do one final round if needed, delete
  the polling cron(s), and give the user a status summary. Also self-abort (delete crons + notify) if
  MSG_DIR itself has been wiped.
- **This is a two-sided loop.** Your durable poller only completes round-trips if the PEER also
  re-wakes itself on your new `*.response.*` files. If the peer only runs when the human prompts it,
  say so plainly — your side will always have a verified reply staged, but the human still nudges the
  peer each hop.
- **Only finalize on genuine completion.** A quiet tick is never `claude.done`. Write `claude.done` and
  delete the crons only when the task is actually complete and independently verified.

### Turn divergence — both sides "waiting" (the second deadlock class)

Even a perfectly self-contained handoff can deadlock if the two sessions disagree about whose turn it
is: you think you handed the turn to the peer; the peer thinks it already handed the turn to you and is
waiting on your response. Each does unrelated side work, "not blocked," and neither produces the next
artifact. This actually happened after the first fix was in place, so it needs its own rules.

- **The shared MSG_DIR files are the ONLY source of truth for turn state — not your memory, not the
  peer's report.** If you (or the peer, via the human) believe "X was requested" or "Y was delivered"
  but no corresponding `*.response.*` file exists in MSG_DIR, then it was NOT exchanged. Reconcile to
  the files, not to either side's narrative.
- **"I'm not blocked / I'll do side work" does NOT relieve you of confirming the peer took the turn.**
  Whenever you hand off (write a response ending "OVER TO YOU"), set a definite checkpoint to verify
  the peer actually produced the expected next artifact. Doing side work is fine, but you MUST return
  to that checkpoint — an unbounded "I'll fold it in whenever it lands" is how the turn silently drops.
- **Detect the symptom.** If the newest file in MSG_DIR is one of YOUR OWN responses that asked for
  peer action, and the bounded window has passed with no new `codex.response.*`, assume possible
  turn-divergence. Do not keep doing unrelated work indefinitely: re-read MSG_DIR, and if the peer's
  latest on-disk message PRE-DATES your handoff, the peer likely never ingested it — re-send a short,
  explicit "your turn: I need <X>; your last file on disk is <ts>, which predates my <ts>" ping.
- **When the human relays that the peer thinks it's your turn, reconcile immediately.** Diff what the
  peer claims against MSG_DIR; re-post whatever artifact is actually missing on disk; state explicitly
  which file now holds the ball. The human is the tie-breaker for turn state — use that signal at once.
- **Prefer explicit receipt.** A handoff is safest when the receiver's next file acknowledges it took
  the turn (even one line). If the peer's protocol doesn't do that, the SENDER must verify receipt by
  checking that the peer's newest file post-dates the handoff before assuming it is "working."

## Starting A Loop

When the user asks to begin a Claude/Codex collaboration:

1. Establish `MSG_DIR` (see **Message Location (Required)**) — ask for the exact location if it was not given.
2. Inspect the repo or task context enough to write a useful first message.
3. Write the first prompt to `$MSG_DIR/claude.response.<timestamp>`.
4. Tell the user which file was written, including the full path.
5. Poll for the newest unread `$MSG_DIR/codex.response.<timestamp>` file.

The first prompt should include:

- The goal and current repo state.
- The specific work requested from Codex.
- Any constraints, tests, or style requirements.
- The expected response format.
- A reminder that Codex should write `$MSG_DIR/codex.response.<timestamp>` when done.

## Polling

Poll with bounded, low-noise commands that sort by mtime, always scoped to `$MSG_DIR`.
Prefer `ls -1t` for the response files because it is portable and matches what users
commonly run:

```bash
ls -1t "$MSG_DIR"/codex.response.* 2>/dev/null | head -20
```

If you need timestamps for reporting, use:

```bash
ls -altr "$MSG_DIR"/codex.response.* "$MSG_DIR"/codex.done 2>/dev/null
```

Do not rely on GNU `find -printf` alone. In some environments it can produce
stale or incomplete output through tool wrappers. If `ls` output and `find`
output disagree, trust `ls` and read the newest unread file shown by `ls`.

For maximum robustness, especially before saying "no new response", cross-check
with Python's filesystem APIs (reads the exact directory from `MSG_DIR`):

```bash
python3 - <<'PY'
import os
from pathlib import Path
msg_dir = Path(os.environ["MSG_DIR"])
for p in sorted(msg_dir.glob('codex.response.*'), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
    print(f"{p.stat().st_mtime:.6f} {p}")
PY
```

Polling rules:

- Maintain a local list of exact paths already read, for example `$MSG_DIR/codex.response.1782321184`.
- From the `ls -1t` or Python mtime-sorted list, choose the first path that is not in the read ledger.
- If no unread response exists, wait briefly and poll again.
- Before concluding that no new response arrived, run both `ls -altr "$MSG_DIR"/codex.response.* "$MSG_DIR"/codex.done 2>/dev/null` and the Python mtime listing above, then compare both outputs against the read ledger.
- Never say there is no new response if either listing shows an unread `$MSG_DIR/codex.response.*` file.
- In the status you report to the user, include the newest matching file from `ls -altr`, its mtime if visible, and whether it was already read.
- If a `$MSG_DIR/codex.done` file appears, still read the newest unread `$MSG_DIR/codex.response.*` before treating Codex as complete.
- If the user asks for status while polling, report the latest state and continue unless they ask to stop.

## Responding To Codex

For each unread Codex response:

1. Read the newest unread file in `$MSG_DIR`.
2. Verify claims against the filesystem, tests, diffs, or command output when possible.
3. Decide whether more Codex work is needed.
4. If more work is needed, write a new `$MSG_DIR/claude.response.<timestamp>` with targeted feedback.
5. After writing non-final feedback, **immediately start active continuous polling**: Check for new responses every 10-30 seconds using the Python mtime check. Do NOT poll once and wait - poll repeatedly until Codex responds or the user interrupts.
6. If the work is complete, write a final `$MSG_DIR/claude.response.<timestamp>` summarizing verification and create `$MSG_DIR/claude.done`.

Do not accept Codex's claim of completion without local verification when commands or files can be checked.

**ACTIVE POLLING REQUIREMENT:** "Keep polling" means run the Python mtime check repeatedly (every 10-30 seconds) in a loop, not "check once and stop." After writing any non-final Claude response, you MUST continue polling until one of:
- A new unread Codex response appears
- `$MSG_DIR/codex.done` appears
- The user explicitly interrupts
- **Your bounded wait elapses with no peer activity.** Then run the Liveness and Deadlock Avoidance
  steps: re-read your own last message, re-send it self-contained if it was not, and if the peer is
  still silent, escalate to the user with an explicit blocker status. This is the required exit from an
  otherwise-infinite poll — "keep polling" is NOT a license to watch silently for hours.

Never sit idle after writing a response - always be actively checking for the next Codex message, but
"actively checking" for a long silence means running the liveness/escalation steps, not spinning a
background watcher indefinitely.

**CRITICAL: Before proceeding to any next phase (like CodeRabbit review), ALWAYS poll one more time to ensure no new Codex response arrived.** Even after an "approval" message, check again - Codex may have found an issue after sending approval and written a follow-up. The pattern:
1. Read Codex approval
2. Write Claude response
3. **Poll again before starting next phase**
4. If new Codex response found, handle it
5. Only proceed to next phase if no unread responses exist

## Avoiding Premature Stops

- If Claude's latest response file contains requests for Codex to implement, inspect, test, or answer something, the collaboration is still active. Poll for a newer unread `$MSG_DIR/codex.response.*` file before returning to the user.
- If a user asks whether the skill is running or asks for status, report the latest file state briefly in a non-final progress update and then continue polling unless they explicitly ask to pause or stop. Do not answer in the final channel while the collaboration is still active.
- A one-turn handoff is only allowed when the user explicitly requests a single response file and no autonomous continuation, or when Claude writes `$MSG_DIR/claude.done`.
- Before any final user-facing response during a collaboration, check whether `$MSG_DIR/claude.done` exists for the current loop or whether there is outstanding Codex-directed work in the latest Claude response. If there is outstanding work, do not finalize; poll.
- A lack of new files is not completion and is not a reason to write `claude.done` or declare the task finished. But it IS a reason to run the Liveness and Deadlock Avoidance steps: after a bounded wait, re-read and (if needed) re-send your last message self-contained, then escalate to the user with an explicit blocker status. That escalation is a non-final progress update, not a completion — the loop stays open, but a human is now looped in instead of you watching silently for hours. Do not confuse "the task isn't done" with "I must keep waiting in silence."

## Review Discipline

- Keep task scope explicit. Distinguish required fixes from optional polish.
- Prefer concrete file paths, commands, failures, and expected behavior.
- Tell Codex what was verified and what still fails.
- Avoid recounting every iteration in final artifacts unless the user asks; summarize the end state.
- Do not let stale timestamps, similarly named files, files outside `$MSG_DIR`, or prior collaboration turns drive the current loop.

## Completion Criteria

Finish the collaboration only when:

- The user-requested task is handled or clearly blocked.
- Codex has no outstanding required action from Claude.
- Claude has independently verified the relevant final state.
- `$MSG_DIR/claude.done` has been created.
