#!/usr/bin/env python3
"""
orchestrate.py — Single entry point for the full extraction pipeline.

Usage:
    python3 orchestrate.py --all              # Run everything
    python3 orchestrate.py --step extract     # Just extract from VM
    python3 orchestrate.py --step process     # Just post-process assets
    python3 orchestrate.py --step validate    # Just validate output
    python3 orchestrate.py --test-connection  # Test SSH to Windows VM
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools" / "extraction"
SCRIPTS_DIR = TOOLS_DIR / "scripts"


def banner(text: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def run_script(script_name: str, args: list = None) -> int:
    script = SCRIPTS_DIR / script_name
    if not script.exists():
        print(f"❌ Script not found: {script}")
        return 1

    cmd = [sys.executable, str(script)]
    if args:
        cmd.extend(args)

    print(f"▶ Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def step_test_connection() -> int:
    """Test SSH connection to the Windows VM."""
    banner("Testing Windows VM Connection")
    return run_script("extract_assets.py", ["--test"])


def step_extract() -> int:
    """Extract all assets from the Windows VM."""
    banner("Phase 1: Extracting Assets from Windows VM")
    
    steps = [
        ("Extracting terrain BSP", ["--extract", "bsp"]),
        ("Extracting collision geometry", ["--extract", "collision"]),
        ("Extracting textures", ["--extract", "textures"]),
        ("Extracting spawn coordinates", ["--extract", "spawns"]),
        ("Extracting Forge objects", ["--extract", "forge"]),
        ("Extracting physics constants", ["--extract", "physics"]),
    ]
    
    for label, args in steps:
        print(f"\n  ▶ {label}...")
        rc = run_script("extract_assets.py", args)
        if rc != 0:
            print(f"  ❌ Failed: {label}")
            return rc
    
    print("\n✅ Extraction complete. Assets pulled to macOS.")
    return 0


def step_process() -> int:
    """Post-process extracted assets (Blender, texture conversion, JSON)."""
    banner("Phase 2: Processing Assets")
    
    rc = run_script("process_assets.py")
    if rc != 0:
        print("❌ Asset processing failed")
        return rc
    
    print("\n✅ Asset processing complete.")
    return 0


def step_validate() -> int:
    """Validate extracted and processed assets."""
    banner("Phase 3: Validating Assets")
    
    rc = run_script("validate_assets.py")
    if rc != 0:
        print("❌ Asset validation failed")
        return rc
    
    print("\n✅ All assets validated. Ready for Godot import.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="moncler-grid-engine Extraction Pipeline"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run the complete pipeline (extract → process → validate)"
    )
    parser.add_argument(
        "--step", choices=["extract", "process", "validate", "test-connection"],
        help="Run a specific pipeline step"
    )
    parser.add_argument(
        "--test-connection", action="store_true",
        help="Test SSH connection to Windows VM"
    )
    args = parser.parse_args()

    # Determine what to run
    if args.test_connection or (args.step == "test-connection"):
        return step_test_connection()

    if args.all:
        banner("MONCLER-GRID-ENGINE — FULL EXTRACTION PIPELINE")
        
        rc = step_test_connection()
        if rc != 0:
            print("\n❌ Cannot connect to Windows VM. Check config.yaml and VM status.")
            return rc

        rc = step_extract()
        if rc != 0:
            return rc

        rc = step_process()
        if rc != 0:
            return rc

        rc = step_validate()
        if rc != 0:
            return rc

        banner("🎉 PIPELINE COMPLETE")
        print("Assets are in assets/ and data/ — open project.godot in Godot 4.7")
        return 0

    if args.step == "extract":
        return step_extract()
    elif args.step == "process":
        return step_process()
    elif args.step == "validate":
        return step_validate()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())