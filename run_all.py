"""
run_all.py
==========
Master pipeline — runs all parts in sequence.

Usage:
    python run_all.py                  # run everything
    python run_all.py --parts 1 2 3    # run specific parts
    python run_all.py --skip-download  # skip data download
    python run_all.py --bonus          # also run bonus scripts
    python run_all.py --draft          # fast low-DPI mode
"""

import sys
import time
import argparse
import traceback
from pathlib import Path

# Add project root so all sub-modules resolve correctly
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.utils.config import ensure_dirs

PARTS = {
    1: ("Part 1 — Projections", "scripts.parts.part1_projections"),
    2: ("Part 2 — Choropleth", "scripts.parts.part2_choropleth"),
    3: ("Part 3 — Proportional Symbols", "scripts.parts.part3_proportional"),
    4: ("Part 4 — Flow Map", "scripts.parts.part4_flow"),
    5: ("Part 5 — Contour/Isopleth", "scripts.parts.part5_contour"),
    6: ("Part 6 — Cartogram", "scripts.parts.part6_cartogram"),
    7: ("Part 7 — Scenarios", "scripts.parts.part7_scenarios"),
}

BONUS = {
    "animation": ("Bonus — Animation", "scripts.bonus.bonus_animation"),
    "morans_i": ("Bonus — Moran's I", "scripts.bonus.bonus_morans_i"),
}


def run_module(module_path: str, label: str) -> bool:
    """
    Dynamically import and execute a module's run() function.

    Args:
        module_path (str): The dot-separated Python import path of the module.
        label (str): Human-readable name of the module for terminal output.

    Returns:
        bool: True if the module executed successfully without exceptions, False otherwise.
    """
    import importlib

    print(f"\n{'=' * 60}")
    print(f"   {label}")
    print(f"{'=' * 60}")
    t0 = time.time()
    try:
        mod = importlib.import_module(module_path)
        mod.run()
        elapsed = time.time() - t0
        print(f"\n   {label} completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        print(f"\n   {label} FAILED: {e}")
        traceback.print_exc()
        return False


def main():
    """
    Main entry point for the GeoViz Master Pipeline.

    Parses command-line arguments to determine which parts of the project
    to execute, sets up global configuration states (like draft mode),
    and orchestrates the sequential execution of data downloading, 
    preprocessing, mapping parts, and bonus scripts.
    """
    parser = argparse.ArgumentParser(description="GeoViz Project Pipeline")
    parser.add_argument("--parts", nargs="+", type=int, help="Parts to run (1-7)")
    parser.add_argument(
        "--skip-download", action="store_true", help="Skip dataset download"
    )
    parser.add_argument(
        "--skip-preprocess", action="store_true", help="Skip preprocessing"
    )
    parser.add_argument("--bonus", action="store_true", help="Also run bonus scripts")
    parser.add_argument("--draft", action="store_true", help="Low DPI draft mode")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  GeoViz Project — Master Pipeline")
    print("=" * 60)
    print(f"  Root: {ROOT}")

    # Apply draft mode globally
    if args.draft:
        import scripts.utils.config as cfg

        cfg.STYLE["dpi_final"] = 150
        print("   Draft mode: 150 DPI")

    # Ensure directories
    ensure_dirs()

    results = {}
    t_start = time.time()

    # ─── Step 1: Download data ────────────────────────────
    if not args.skip_download:
        import importlib

        loader = importlib.import_module("scripts.utils.data_loader")
        print(f"\n{'=' * 60}")
        print("   Data Download")
        print(f"{'=' * 60}")
        loader.download_all()

    # ─── Step 2: Preprocess ───────────────────────────────
    if not args.skip_preprocess:
        ok = run_module("scripts.utils.preprocess", "Data Preprocessing")
        results["preprocess"] = ok
        if not ok:
            print("\n Preprocessing failed. Cannot continue.")
            sys.exit(1)

    # ─── Step 3: Parts ────────────────────────────────────
    parts_to_run = args.parts if args.parts else list(PARTS.keys())

    for part_num in parts_to_run:
        if part_num not in PARTS:
            print(f"    Unknown part: {part_num}")
            continue
        label, module_path = PARTS[part_num]
        ok = run_module(module_path, label)
        results[f"part{part_num}"] = ok

    # ─── Step 4: Bonus ────────────────────────────────────
    if args.bonus:
        for key, (label, module_path) in BONUS.items():
            ok = run_module(module_path, label)
            results[f"bonus_{key}"] = ok

    # ─── Summary ──────────────────────────────────────────
    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE  ({elapsed:.0f}s total)")
    print(f"{'=' * 60}")

    passed = sum(v for v in results.values())
    failed = len(results) - passed

    for step, ok in results.items():
        icon = "" if ok else ""
        print(f"  {icon}  {step}")

    print(f"\n  {passed}/{len(results)} steps passed")
    if failed:
        print(f"    {failed} step(s) failed — check output above.")
        sys.exit(1)
    else:
        print("\n  All outputs saved to outputs/")
        print(
            "  Run: python scripts/bonus/bonus_dashboard.py  for interactive dashboard"
        )


if __name__ == "__main__":
    main()
