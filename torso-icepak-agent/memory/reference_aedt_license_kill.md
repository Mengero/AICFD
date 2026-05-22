---
name: reference-aedt-license-kill
description: "Force-killing an AEDT solve leaks elec_solve_icepak floating licenses; subsequent solves fail in 4-6s with a misleading \"Error in Solving\" message"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

If you `Stop-Process -Force` an `ansysedt.exe` that is in the middle of
`analyze_setup`, the `elec_solve_icepak` license tokens checked out by
that process are NOT returned to the Ansys license server. Any
subsequent Icepak solve from any client (PyAEDT or GUI) on that
license pool then DENIES with:

```
elec_solve_icepak (Ansys Electronics Enterprise - Shared Web: 0 available of N needed)
```

PyAEDT mis-reports this as `Error in Solving Setup1` after 4-6 seconds,
which looks exactly like a mesh failure. The real diagnosis is in
`C:\Users\<u>\AppData\Local\Temp\.ansys\ansyscl.<hostname>.log` (search
for `DENIED elec_solve_icepak`).

**Recovery options (in order):**
1. Wait 10-30 min for the license server idle timeout to reap the
   orphaned checkout. Cheapest, always-available.
2. Restart the Ansys License Manager service (requires admin).
3. Have the licensing admin manually release the stuck checkout on
   the server side.

**Avoidance:** instead of `Stop-Process -Force` on a mid-solve AEDT,
use one of these graceful paths:
- `icepak.odesktop.AbortAndCloseProject()` from PyAEDT
- `icepak.release_desktop(close_projects=True, close_desktop=True)` —
  this also gracefully releases licenses, even on a non-converging solve
- File menu → Exit in the GUI

A 5-second "wait for graceful shutdown" is much cheaper than 10-30 min
of stuck licenses + having to re-acquire them. See also
[[feedback-monitor-dont-wait]] (for deciding *when* to abort), and
[[reference-aedt-close-reopen]] (for the OTHER AEDT pitfall — never
*reopen* a closed Icepak project either).
