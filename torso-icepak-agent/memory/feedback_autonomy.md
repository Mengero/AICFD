---
name: feedback-autonomy
description: "User wants Claude to just do common autonomous actions, not ask permission"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

User explicitly said "don't ask me just go and do it" when it comes to common
autonomous actions like `pip install`, running Python scripts, mkdir, listing
files, and reading/writing files inside a working project.

**Why:** The user is running long-form engineering tasks where stopping for
permission on routine ops breaks flow. Permission prompts should be reserved
for genuinely consequential decisions (destructive ops, scope changes,
sim results that need review).

**How to apply:** Use the [[allowlist-in-user-settings]] in `~/.claude/settings.json`
(already configured with broad allows for Read/Write/Edit/Glob/Grep, plus
Bash/PowerShell prefix rules for pip, python, mkdir, ls, cd, cp, mv, etc.).
If a new common verb starts triggering prompts, add it to the allow list
without asking. The only checkpoint that should pause is the one the user
explicitly named (e.g. after a sim solve produces results to review).

**Reinforced 2026-05-19:** when a multi-stage workflow has a defined next
step (e.g. "launch iter_02" after a code change), KICK IT OFF AUTOMATICALLY.
Do not pause and offer to launch — just launch and report status. The
user said verbatim: "burn it into your setting: don't ask me to kick it
off, you handle everything." Asking "want me to launch?" or "ready to
launch?" is unwanted friction. The only ask should be when the workflow
genuinely forks on a value the user must supply (e.g. which boundary is
the inlet) — and even then, prefer making the best guess and proceeding
with a clearly-flagged assumption.

**Re-reinforced 2026-05-19:** "if you have idea, just go for it, don't
ask my opinion. burn this into your setting as well." This applies to
*engineering judgment calls* too — picking the next mesh refinement
direction, choosing whether to fix a peripheral bug, deciding what to
diagnose first, etc. **Just decide, execute, report.** When the user
disagrees they will interrupt. AskUserQuestion is reserved for cases
where there is genuinely no defensible default (e.g. a destructive
operation that can't be undone, or a value only the user knows). Even
the "review checkpoint" after a solve is not a question — print the
summary and proceed to the next iteration; the user reads the summary
while the next solve runs, and interrupts if they disagree.
