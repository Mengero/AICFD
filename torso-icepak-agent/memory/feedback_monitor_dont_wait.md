---
name: feedback-monitor-dont-wait
description: "Actively monitor long-running solves; don't just wait for them to finish"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

**Don't passively wait for a long-running simulation/solve/build to finish
before checking it.** Set up active monitoring that reads the live output
(residual files, log streams, profile data) and surfaces problems mid-run.

**Why:** User pushback 2026-05-20 after I launched the noduct convergence
fix and went quiet waiting for the harness notification. User said: "I
suggest your monitor keep monitoring the convergence. Don't wait till the
simulation is completely finished." A bad solve can be 1+ hours of wasted
compute that you'd kill at minute 10 if you were watching.

**How to apply:**
1. After launching anything long (>5 min expected), set up a watchdog
   alongside it that polls the live output (`.sd` for Icepak residuals,
   build logs for compiles, training metrics for ML jobs).
2. The watchdog reads from disk (no API calls into the live process —
   that risks corrupting state, see [[reference-aedt-close-reopen]]).
3. The watchdog should be QUIET when things are healthy and LOUD when
   they're not — emit warnings only on divergence / NaN / unexpected
   stops, plus a periodic heartbeat (every N min).
4. Kill the run early if the watchdog flags trouble — don't ride it out.
   Lost iterations are cheap; lost hours waiting for a doomed solve are
   not.
5. This applies broadly: long simulations, long CI runs, long training
   loops, long deploys — anywhere "fire and forget" leaves the user
   stranded if it goes wrong.

Related: [[feedback-check-disk-first]] (read the result folder, not the
API) and [[feedback-autonomy]] (just do the monitoring, don't ask).
