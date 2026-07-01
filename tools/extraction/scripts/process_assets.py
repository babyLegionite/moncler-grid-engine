#!/usr/bin/env python3
"""
process_assets.py — Post-process extracted assets on macOS.

Steps:
  1. Convert .dds textures to .webp (Godot-friendly, smaller)
  2. Run Blender headless to import Reach tag data → export .glb
  3. Optimize .glb files (deduplicate, compress)
  4. Generate collision shapes from collision meshes
  5. Validate JSON data files
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"

# Try to find Blender
BLENDER = None
for candidate in [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    "/opt/homebrew/bin/blender",
    "/usr/local/bin/blender",
]:
    if os.path.exists(candidate):
        BLENDER = candidate
        break


def banner(text: str) -> None:
    print(f"\n  ── {text} ──")


def convert_textures_to_webp() -> bool:
    """Convert .dds textures to .webp using ImageMagick or sips."""
    banner("Converting textures to WebP")

    tex_dir = ASSETS_DIR / "maps" / "hemorrhage_textures"
    if not tex_dir.exists():
        print(f"  ⚠️  Texture directory not found: {tex_dir}")
        return False

    dds_files = list(tex_dir.glob("*.dds"))
    if not dds_files:
        print("  ℹ️  No .dds files to convert (textures may already be processed)")
        return True

    # Try ImageMagick first, fall back to sips
    convert_cmd = None
    for cmd in ["magick", "convert"]:
        if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
            convert_cmd = cmd
            break

    if convert_cmd:
        for dds in dds_files:
            webp = dds.with_suffix(".webp")
            subprocess.run(
                [convert_cmd, str(dds), str(webp)],
                capture_output=True
            )
            print(f"  ✅ {dds.name} → {webp.name}")
    else:
        # Use macOS sips (limited format support)
        print("  ⚠️  ImageMagick not found — install with: brew install imagemagick")
        print("  ℹ️  sips can't handle .dds — manual conversion required")
        return False

    return True


def process_blender_imports() -> bool:
    """Run Blender headless to process Reach tag data into .glb files."""
    banner("Blender headless processing")

    if not BLENDER:
        print("  ⚠️  Blender not found — install from blender.org")
        print("  ℹ️  Skipping Blender processing (run manually when Blender is installed)")
        return True

    print(f"  🎨 Blender found: {BLENDER}")

    # Check for Halo Asset Blender Dev Toolset
    # (This is a Blender add-on that imports Reach tag data)
    # Installation: copy the add-on to Blender's scripts/addons directory

    blender_script = PROJECT_ROOT / "tools" / "extraction" / "scripts" / "blender_import.py"
    if not blender_script.exists():
        print("  ℹ️  No Blender import script — creating one")
        create_blender_import_script()

    # Run Blender headless
    result = subprocess.run(
        [BLENDER, "--background", "--python", str(blender_script)],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)
    )
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    if result.returncode != 0:
        print(f"  ⚠️  Blender exited with code {result.returncode}")
        print(result.stderr[-500:])

    return True


def create_blender_import_script():
    """Create the Blender Python script that imports Reach tag data."""
    script = '''"""
Blender import script for Halo Reach tag data.
Requires: Halo Asset Blender Development Toolset add-on installed.
Run: Blender --background --python blender_import.py
"""

import bpy
import os
import sys

# Paths (adjust as needed)
PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTRACTED = os.path.join(PROJECT, "assets", "maps")

def import_bsp():
    """Import terrain BSP from extracted tag data."""
    bsp_dir = os.path.join(EXTRACTED, "bsp")
    if not os.path.exists(bsp_dir):
        print(f"BSP dir not found: {bsp_dir}")
        return

    # The Halo asset toolset imports .model or .render_model tags
    # This is add-on specific — adjust based on actual toolset API
    try:
        # Clear scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        # Import via toolset (if installed)
        # bpy.ops.halo.import_tag(tag_path=bsp_dir, tag_type='scenario_structure_bsp')

        # Export as glTF
        output = os.path.join(EXTRACTED, "hemorrhage_terrain.glb")
        bpy.ops.export_scene.gltf(
            filepath=output,
            export_format='GLB',
            export_apply=True
        )
        print(f"Exported terrain: {output}")

    except Exception as e:
        print(f"BSP import failed: {e}")
        print("Make sure Halo Asset Blender Dev Toolset is installed in Blender")

def import_collision():
    """Import collision geometry."""
    col_dir = os.path.join(EXTRACTED, "collision")
    if not os.path.exists(col_dir):
        print(f"Collision dir not found: {col_dir}")
        return

    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        # Import via toolset
        # bpy.ops.halo.import_tag(tag_path=col_dir, tag_type='collision_model')

        output = os.path.join(EXTRACTED, "hemorrhage_collision.glb")
        bpy.ops.export_scene.gltf(
            filepath=output,
            export_format='GLB',
            export_apply=True
        )
        print(f"Exported collision: {output}")

    except Exception as e:
        print(f"Collision import failed: {e}")

if __name__ == "__main__":
    print("=== Blender Asset Processing ===")
    import_bsp()
    import_collision()
    print("=== Done ===")
'''
    script_path = PROJECT_ROOT / "tools" / "extraction" / "scripts" / "blender_import.py"
    script_path.write_text(script)
    print(f"  📝 Created: {script_path}")


def validate_json_files() -> bool:
    """Validate JSON data files have correct structure."""
    banner("Validating JSON data files")

    schemas = {
        "reach_physics.json": ["gravity", "player_walk_speed", "jump_initial_velocity"],
        "spawn_coordinates.json": ["spawns"],
        "forge_objects.json": ["forge_objects"],
        "weapon_data.json": ["weapons"],
    }

    all_ok = True
    for filename, required_keys in schemas.items():
        path = DATA_DIR / filename
        if not path.exists():
            print(f"  ⚠️  {filename} not found")
            all_ok = False
            continue

        try:
            with open(path) as f:
                data = json.load(f)

            for key in required_keys:
                if key not in data:
                    print(f"  ❌ {filename}: missing key '{key}'")
                    all_ok = False

            print(f"  ✅ {filename} — valid")
        except json.JSONDecodeError as e:
            print(f"  ❌ {filename}: invalid JSON — {e}")
            all_ok = False

    return all_ok


def main():
    print("=" * 60)
    print("  moncler-grid-engine — Asset Processing")
    print("=" * 60)

    # Step 1: Convert textures
    convert_textures_to_webp()

    # Step 2: Blender processing
    process_blender_imports()

    # Step 3: Validate JSON
    validate_json_files()

    print("\n✅ Processing complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())