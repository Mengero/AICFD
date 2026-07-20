"""
_session.py -- shared, dependency-free AEDT/Icepak connection helper.

Every example in this folder imports this so the connection lessons live in one
place and each script stays short:

  * attach vs headless. attach reuses an already-open GUI session (connect by
    project *stem*, new_desktop=False); headless opens a fresh non-graphical
    desktop by *absolute path* (non_graphical=True, new_desktop=True). Using the
    wrong one gives "connected but the project isn't there", or spawns a second
    empty desktop.
  * license reuse. Releasing does NOT close the desktop (except headless, which
    closes the one it started), so a chain of edits uses one license checkout.
  * stale locks. An earlier crash leaves .lock/.semaphore files that block the
    open; clean them ONLY when no ansysedt process is running.

Requires only `ansys.aedt.core` (PyAEDT). No project-specific toolkit.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from ansys.aedt.core import Icepak


def add_common_args(ap: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add the connection flags every example shares."""
    ap.add_argument("--project", required=True,
                    help="path to the .aedt (attach uses its stem; headless the abs path)")
    ap.add_argument("--design", required=True, help="design name, e.g. IcepakDesign1")
    ap.add_argument("--version", default="2026.1", help="AEDT version, e.g. 2026.1 / 2025.2")
    ap.add_argument("--headless", action="store_true",
                    help="fresh non-graphical session instead of attaching to the open GUI")
    ap.add_argument("--clean-locks", action="store_true",
                    help="remove stale .lock/.semaphore first (only if no ansysedt is running)")
    ap.add_argument("--no-save", action="store_true", help="do not save on exit (dry run)")
    return ap


def _ansysedt_running() -> bool:
    try:
        return subprocess.run(["pgrep", "-f", "ansysedt"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).returncode == 0
    except Exception:
        # If pgrep is unavailable, be conservative and assume a session exists.
        return True


def clean_stale_locks(aedt_file) -> list[str]:
    """Delete stale lock files under <project>.aedtresults, but only if no
    ansysedt process is running (never touch a live session's lock)."""
    p = Path(aedt_file).resolve()
    results = Path(str(p) + "results")  # foo.aedt -> foo.aedtresults
    if not results.exists() or _ansysedt_running():
        return []
    removed: list[str] = []
    for pat in ("*.lock", "*.semaphore", ".*.lock", ".*.semaphore"):
        for f in results.rglob(pat):
            try:
                f.unlink()
                removed.append(str(f))
            except OSError:
                pass
    return removed


class IcepakSession:
    """Context manager around an Icepak connection. See module docstring."""

    def __init__(self, args):
        self.project = Path(args.project).resolve()
        self.design = args.design
        self.version = args.version
        self.headless = bool(args.headless)
        self.clean_locks = bool(getattr(args, "clean_locks", False))
        self.save_on_exit = not bool(args.no_save)
        self.ipk: Icepak | None = None

    def __enter__(self) -> Icepak:
        if self.clean_locks:
            removed = clean_stale_locks(self.project)
            if removed:
                print(f"    cleaned {len(removed)} stale lock file(s)")

        if self.headless:
            print(f">>> launching headless AEDT, opening {self.project.name}")
            self.ipk = Icepak(project=str(self.project), design=self.design,
                              version=self.version, non_graphical=True, new_desktop=True)
        else:
            print(f">>> attaching to running AEDT (project {self.project.stem})")
            self.ipk = Icepak(project=self.project.stem, design=self.design,
                              version=self.version, non_graphical=False, new_desktop=False)
        print(f"    connected: design={self.design}, headless={self.headless}")
        return self.ipk

    def __exit__(self, exc_type, exc, tb):
        if self.ipk is None:
            return False
        try:
            # Only persist a clean run -- never save a state reached via exception.
            if self.save_on_exit and exc_type is None:
                self.ipk.save_project()
                print("    project saved")
        except Exception as e:
            print(f"    [warn] save_project failed: {e}")
        try:
            self.ipk.release_desktop(close_projects=False, close_desktop=self.headless)
            print(f"    released (close_desktop={self.headless})")
        except Exception as e:
            print(f"    [warn] release_desktop failed: {e}")
        self.ipk = None
        return False  # never swallow the exception
