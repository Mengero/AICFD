---
name: feedback-convergence-rigor
description: There are two convergence bars (engineering vs numerical); pick the right one for the use case
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

For any CFD / FEA / iterative solve, distinguish two different
"converged" thresholds and don't push past the one the use case
actually needs:

1. **Engineering converged** — the *physical metrics you care about*
   (mass flow, ΔP, max temperature, peak stress, …) have stopped
   moving iter-to-iter within your error budget. Residuals may still
   oscillate or have bounded spikes; that's noise around the answer,
   not the answer changing. Enough for most design decisions, trade
   studies, mesh sensitivity, what-if exploration.

2. **Numerically converged** — every residual is monotonically below
   its target (typically 1e-3 for flow, 1e-6 for energy) with no
   spikes at the end. Required when you have to *defend* the result
   formally: acceptance criteria, regulatory filings, publication,
   safety-critical analysis, validation against measurements.

**Why:** User said verbatim 2026-05-20: "if you are targeting a
non-oscillates simulation, you don't need a fully clean run; but if
you want to make sure the simulation does converge and no spike at
the end, you need to run a fully one."

**STRICTER RULE on saying "done"** (reinforced same day, after I
prematurely declared the noduct fix complete on engineering-converged
bar): **the bar for claiming a task is "done" is bar 2 (numerically
clean), not bar 1.** Engineering convergence is sufficient for
"sufficient for the next decision" but NOT sufficient for "done."
User said verbatim: "I suggest you always double check before you say
'done'. At least you need to have a clean run to say that."

So the pattern is:
- Use engineering convergence as a CHECKPOINT — "looks like we're
  there, let's verify."
- Verify by running long enough / adjusting solver to get bar 2.
- Only THEN report "done."
- If bar 2 is genuinely unreachable in this configuration, escalate
  (Sequential Solve off, Coupled solver, Pseudo-Transient) before
  giving up; don't lower the bar.

**How to apply:**
1. Before pushing further on a stalled / oscillating solve, ask:
   *what is this solution being used for?* If the answer is design
   exploration, you're done as soon as the engineering metrics are
   stable.
2. If the user explicitly needs clean residuals (or it's regulated /
   formal work), keep pushing — escalate to coupled solver, lower
   URFs further, switch off sequential solve, pseudo-transient mode.
3. Capture both states distinctly in any report — "engineering
   converged with bounded residual noise" vs "fully numerically
   converged." Don't conflate them.
4. Engineering convergence is also enough for *mesh sensitivity*
   studies (we found this on the torso project — see
   [[reference-torso-project]]).

Related: [[feedback-monitor-dont-wait]] (knowing when to stop watching),
[[feedback-check-disk-first]] (extracting metrics from disk to verify
engineering convergence even when SOV doesn't write).
