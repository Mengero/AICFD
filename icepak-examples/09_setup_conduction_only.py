#!/usr/bin/env python3
"""
09_setup_conduction_only.py -- create an Icepak steady-state solution setup that
solves CONDUCTION ONLY (energy equation only, no flow, no gravity, no radiation).

Use this when the model has no fluid domain to speak of: a board/package stack
where every heat path is solid conduction plus lumped network/source boundaries.
It is dramatically cheaper and more robust than a flow solve, and it is the right
choice for a design that has no Region, no openings, no grilles and no fans --
solving flow there would be meaningless.

>>> THE FOUR SWITCHES THAT MAKE IT CONDUCTION-ONLY <<<
    "Include Temperature:=", True     # solve energy
    "Include Flow:=",        False    # <-- no momentum/continuity
    "Include Gravity:=",     False    # no buoyancy (nothing to buoy)
    "Radiation Model:=",     "Off"    # no surface-to-surface radiation
Everything else in the argument list below is the AEDT default and is kept
verbatim so the setup matches what the GUI writes.

Note "Flow Regime:=", "Laminar" is still present -- it is inert while
Include Flow is False. Don't read it as "a laminar flow solve".

>>> WHERE THIS ARGUMENT LIST CAME FROM <<<  It is a GUI recording (Tools >
Record Script) from AEDT 2026.1, i.e. ground truth rather than a guess. Prefer
recording the GUI over hand-assembling native argument arrays -- Icepak's
InsertSetup array is long and order/name sensitive.

The recording is emitted as an IronPython macro (`import ScriptEnv;
ScriptEnv.Initialize(...)`). Do NOT run it that way on this cluster --
ScriptEnv.Initialize raises a null-method error under `-RunScriptAndExit`.
Drive the same native call through a PyAEDT gRPC session instead, as below.

    $PY 09_setup_conduction_only.py --project M.aedt --design IcepakDesign1
    $PY 09_setup_conduction_only.py --project M.aedt --design IcepakDesign1 --name Setup1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def conduction_only_args(name="Setup1", max_iterations=100, energy_criterion="1e-12"):
    """The recorded IcepakSteadyState argument array, conduction-only."""
    return [
        f"NAME:{name}",
        "Enabled:=", True,
        ["NAME:MeshLink", "ImportMesh:=", False],
        "Flow Regime:=", "Laminar",            # inert while Include Flow is False
        "Include Temperature:=", True,         # <-- solve energy
        "Include Flow:=", False,               # <-- CONDUCTION ONLY
        "Include Gravity:=", False,
        "Include Solar:=", False,
        "Solution Initialization - X Velocity:=", "0m_per_sec",
        "Solution Initialization - Y Velocity:=", "0m_per_sec",
        "Solution Initialization - Z Velocity:=", "0m_per_sec",
        "Solution Initialization - Temperature:=", "AmbientTemp",
        "Solution Initialization - Turbulent Kinetic Energy:=", "1m2_per_s2",
        "Solution Initialization - Turbulent Dissipation Rate:=", "1m2_per_s3",
        "Solution Initialization - Specific Dissipation Rate:=", "1diss_per_s",
        "Solution Initialization - Use Model Based Flow Initialization:=", False,
        "Convergence Criteria - Flow:=", "0.001",
        "Convergence Criteria - Energy:=", energy_criterion,
        "Convergence Criteria - Turbulent Kinetic Energy:=", "0.001",
        "Convergence Criteria - Turbulent Dissipation Rate:=", "0.001",
        "Convergence Criteria - Specific Dissipation Rate:=", "0.001",
        "Convergence Criteria - Discrete Ordinates:=", "1e-06",
        "Convergence Criteria - Joule Heating:=", "1e-07",
        "GPU Convergence Criteria - Flow:=", "0.001",
        "GPU Convergence Criteria - Energy:=", "1e-05",
        "GPU Convergence Criteria - Turbulent Kinetic Energy:=", "0.001",
        "GPU Convergence Criteria - Turbulent Dissipation Rate:=", "0.001",
        "GPU Convergence Criteria - Specific Dissipation Rate:=", "0.001",
        "GPU Convergence Criteria - Discrete Ordinates:=", "1e-05",
        "GPU Convergence Criteria - Joule Heating:=", "1e-07",
        "IsEnabled:=", False,
        "Radiation Model:=", "Off",            # <-- no radiation
        "Solar Radiation Model:=", "Solar Radiation Calculator",
        "Solar Enable Participating Solids:=", False,
        "Solar Radiation - Scattering Fraction:=", "0",
        "Solar Radiation - Day:=", 1,
        "Solar Radiation - Month:=", 1,
        "Solar Radiation - Hours:=", 0,
        "Solar Radiation - Minutes:=", 0,
        "Solar Radiation - GMT:=", "0",
        "Solar Radiation - Latitude:=", "0",
        "Solar Radiation - Latitude Direction:=", "North",
        "Solar Radiation - Longitude:=", "0",
        "Solar Radiation - Longitude Direction:=", "East",
        "Solar Radiation - Ground Reflectance:=", "0.2",
        "Solar Radiation - Sunshine Fraction:=", "1",
        "Solar Radiation - North X:=", "0",
        "Solar Radiation - North Y:=", "1",
        "Solar Radiation - North Z:=", "0",
        "Under-relaxation - Pressure:=", "0.3",
        "Under-relaxation - Momentum:=", "0.7",
        "Under-relaxation - Temperature:=", "1",
        "Under-relaxation - Turbulent Kinetic Energy:=", "0.8",
        "Under-relaxation - Turbulent Dissipation Rate:=", "0.8",
        "Under-relaxation - Specific Dissipation Rate:=", "0.8",
        "Under-relaxation - Joule Heating:=", "1",
        "Under-relaxation - Body Force:=", "1",
        "Under-relaxation - Turbulent Viscosity:=", "1",
        "Discretization Scheme - Pressure:=", "Standard",
        "Discretization Scheme - Momentum:=", "First",
        "Discretization Scheme - Temperature:=", "First",
        "Secondary Gradient:=", False,
        "Discretization Scheme - Turbulent Kinetic Energy:=", "First",
        "Discretization Scheme - Turbulent Dissipation Rate:=", "First",
        "Discretization Scheme - Specific Dissipation Rate:=", "First",
        "Discretization Scheme - Discrete Ordinates:=", "First",
        "Linear Solver Type - Pressure:=", "V",
        "Linear Solver Type - Momentum:=", "flex",
        "Linear Solver Type - Temperature:=", "F",
        "Linear Solver Type - Turbulent Kinetic Energy:=", "flex",
        "Linear Solver Type - Turbulent Dissipation Rate:=", "flex",
        "Linear Solver Type - Specific Dissipation Rate:=", "flex",
        "Linear Solver Type - Joule Heating:=", "F",
        "Linear Solver Termination Criterion - Pressure:=", "0.1",
        "Linear Solver Termination Criterion - Momentum:=", "0.1",
        "Linear Solver Termination Criterion - Temperature:=", "1e-06",
        "Linear Solver Termination Criterion - Turbulent Kinetic Energy:=", "0.1",
        "Linear Solver Termination Criterion - Turbulent Dissipation Rate:=", "0.1",
        "Linear Solver Termination Criterion - Specific Dissipation Rate:=", "0.1",
        "Linear Solver Termination Criterion - Joule Heating:=", "1e-09",
        "Linear Solver Residual Reduction Tolerance - Pressure:=", "0.1",
        "Linear Solver Residual Reduction Tolerance - Momentum:=", "0.1",
        "Linear Solver Residual Reduction Tolerance - Temperature:=", "1e-06",
        "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy:=", "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate:=", "0.1",
        "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate:=", "0.1",
        "Linear Solver Residual Reduction Tolerance - Joule Heating:=", "1e-09",
        "Maximum Cycles:=", "30",
        "Linear Solver Stabilization - Pressure:=", "None",
        "Linear Solver Stabilization - Temperature:=", "None",
        "Linear Solver Stabilization - Joule Heating:=", "None",
        "Coupled pressure-velocity formulation:=", False,
        "Turn off auto-pairing for grid interface creation:=", False,
        "Enable Hybrid precision for GPU:=", True,
        "Partition method:=", "Metis",
        "2D Profile Interpolation Method:=", "Inverse Distance Weighted",
        "Frozen Flow Simulation:=", False,
        "TEC Coupling:=", False,
        "Sequential Solve of Flow and Energy Equations:=", False,
        "Convergence Criteria - Max Iterations:=", max_iterations,
    ]


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--name", default="Setup1", help="setup name (default Setup1)")
    ap.add_argument("--max-iterations", type=int, default=100)
    ap.add_argument("--energy-criterion", default="1e-12")
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        existing = [s.name for s in ipk.setups]
        print(f"    existing setups: {existing or '(none)'}")
        if args.name in existing:
            print(f"    [skip] '{args.name}' already exists -- delete it first "
                  f"or pass a different --name")
            return

        module = ipk.odesign.GetModule("AnalysisSetup")
        module.InsertSetup("IcepakSteadyState", conduction_only_args(
            args.name, args.max_iterations, args.energy_criterion))

        # Verify -- don't assume. Read the setup back off the design.
        names = [s.name for s in ipk.setups]
        print(f"    setups now: {names}")
        if args.name not in names:
            print(f"    [FAIL] '{args.name}' was not created")
            return
        props = dict(ipk.setups[names.index(args.name)].props)
        for k in ("Include Temperature", "Include Flow", "Include Gravity",
                  "Radiation Model", "Convergence Criteria - Max Iterations",
                  "Convergence Criteria - Energy"):
            print(f"      {k} = {props.get(k)}")
        if props.get("Include Flow"):
            print("    [WARN] Include Flow is True -- this is NOT conduction-only")

    print(">>> done. Validate, then run the pre-solve checklist before solving.")


if __name__ == "__main__":
    main()
