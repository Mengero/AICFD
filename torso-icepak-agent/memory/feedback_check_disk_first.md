---
name: feedback-check-disk-first
description: "When an API path fails or returns nothing, look at what's actually on disk before debugging the API further"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

When the "official" API path for extracting data silently fails or returns
no values, **STOP debugging the API and look at what is actually on disk
in the result/output folder.** Most simulation tools (Icepak, ANSYS Fluent,
COMSOL, CFD-style codes) write residuals, monitor histories, profile logs,
and field summaries as plain-text or simple-binary files alongside the
project. These are often readable directly without going through the
flaky scripting layer.

**Why:** User pushback 2026-05-19 — I burned ~2 hours fighting AEDT's
`FieldSummary.export_csv` and direct `ExportFieldsSummary` while
`outputs/iter_NN/<name>.aedtresults/<design>.results/*MON*.sd` and
`*.profile` files sitting next to it contained final monitor values
(Temperature, MassFlow, VolumeFlow), per-iteration residual history
(Continuity, XVelocity, YVelocity, ZVelocity, Energy), and convergence
data in plain text. User said: "you should always check those physics
numbers. Why you don't check them before."

**How to apply:**
1. The very first time an extraction returns None / empty / silent
   failure, **inventory the result directory on disk** (`ls`, `find`,
   `grep` for the quantities you want).
2. Before writing a parser, **read one of the files** to see its
   structure — `.sd` files for AEDT/Icepak are
   `<iteration_number> Quantity1(value1)Quantity2(value2)...` per line.
3. Prefer a disk-parsing path that doesn't depend on the API being
   healthy. The API can be a *complement*, not the *only* source.
4. This applies to non-AEDT tools too — when fighting any external
   tool's scripting interface, check the output directory first.
