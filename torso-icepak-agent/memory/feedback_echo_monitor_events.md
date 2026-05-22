---
name: feedback-echo-monitor-events
description: "When a watchdog/heartbeat Monitor event fires, parse and echo the data in the response — don't just acknowledge with \"OK\""
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

When a `Monitor` event arrives carrying live data from a long-running
process (heartbeat residuals, build progress, training metrics), the
agent response must **echo the key fields in a readable mini-summary,
not just acknowledge with "OK"**. The event content is delivered in
the Monitor's raw stdout format, often `||`-separated or otherwise
formatted to survive transport — the user reading the chat sees the
raw form and the agent's "OK" beside it, and the data feels lost.

**Why:** User pushback 2026-05-20 mid-sweep: "why the monitor event
only returns 'OK' I want to see the iter number, residual and
everything". They were watching a 6-case parametric sweep and needed
to see per-heartbeat the iter, residuals, and monitors at a glance,
not have to mentally parse the `||`-separated raw event each time.

**How to apply:**

1. When a heartbeat / watchdog event fires, **briefly parse the
   payload** and respond with a compact structured summary, e.g.:

   ```
   sweep 1/6, iter 4, 2/7 converged
     Continuity 4.71e-1  (target 1e-3, expected high at iter 4)
     K          1.08e-1
     Omega      1.15e-1
     MassFlow   0.48 g/s    T_mon 20.73 C
   ```

2. Flag the meaningful values: which residuals are above/below their
   targets, whether monitors are stable, whether anything spiked.

3. Keep it short — 4-8 lines is enough. Don't repeat unchanged
   context (e.g. "no spikes" can stay silent).

4. Echo the data even when nothing is wrong. The user wants to *see*
   that the solve is alive and where it is, not just know it didn't
   die.

5. Only the bare "OK" is acceptable for events the user has
   explicitly told you to mute (e.g. mid-meshing stage with no useful
   data). When in doubt, echo.

Related: [[feedback-monitor-dont-wait]] (the parent lesson about
active monitoring) and the AGENT_PROMPT.md `Live-solve monitoring
pattern` section.
