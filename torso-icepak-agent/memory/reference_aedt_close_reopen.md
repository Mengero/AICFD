---
name: reference-aedt-close-reopen
description: "AEDT 2025.2 + pyaedt 0.27 — closed Icepak project's solution context is unrecoverable after reopen"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

When PyAEDT releases a non-graphical Icepak desktop with
`close_projects=True`, the saved `.aedt` retains its `.aedtresults/`
sibling on disk, but **AEDT's COM/gRPC layer cannot re-attach the
solution context on reopen**. After reopen:

- `icepak.osolution.GetAvailableVariations("Setup1")` →
  `script macro error: solution 'setup1' was not found`.
- `icepak.odesign.EditFieldsSummarySetting(...)` → either silently no-ops
  (no exception, no CSV produced) or raises
  `GrpcApiError: Failed to execute gRPC AEDT command`.
- `icepak.odesign.AnalyzeRecover()` → same gRPC error.
- Higher-level `icepak.post.evaluate_object_quantity()` /
  `evaluate_boundary_quantity()` then fail at
  `FieldSummary.export_csv` (which itself has a separate bug on
  nominal-only projects: it calls
  `available_variations.variations(setup, True)[0]` and indexes an empty
  list).
- The AEDT GUI, however, *can* open the same `.aedt` and shows the
  solution normally. Only the headless COM/gRPC layer is degraded.

**Implication for any pyaedt mesh-study driver:** post-processing
(field summary export, field plot creation, fin-temperature loops)
must run inside the **same AEDT session that just solved** — never in
a follow-up "rerun_post" script that reopens the project. Save the
project exactly once at the end of that combined session.

**Recoverable info from a closed iteration .aedt:** geometry, boundary
list, design tree, and *visual* field plots that were created in-session
before close (they persist in the saved project). Not recoverable
programmatically: per-face / per-object field values.

**Worse: repeated reopens can DESTROY the solution data on disk.**
Observed 2026-05-19: after 4 PyAEDT probe sessions opened a previously
solved iter_01 .aedt and let `release_desktop(close_projects=True)`
save on close, the `.aedtresults/<design>.results/*.Field/fields.resd`
directory was wiped clean. AEDT's "save inconsistent state" logic
seems to discard field data it can no longer index. The .aedt shell
file remains valid; the actual solved field results are gone. **Never
reopen a closed iteration .aedt with PyAEDT for any purpose — not even
inspection.** Visualization must happen in the AEDT GUI. The original
unmodified baseline .aedt is unaffected (PyAEDT only operates on
copies in this project), but each per-iteration copy is single-use.

See [[reference-torso-project]] for the concrete project this was
discovered in (boundary `env` has 2 faces, etc.) and
[[reference-aedt-env]] for the install / package versions in play.
