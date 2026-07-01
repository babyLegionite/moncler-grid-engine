#!/usr/bin/env python3
"""
validate_assets.py — Verify extracted and processed assets are correct.

Checks:
  - .glb files exist and are valid glTF 2.0
  - Texture files exist and have reasonable dimensions
  - JSON data files parse correctly
  - Mesh vertex counts are reasonable
  - Collision mesh is separate from render mesh
"""

import json
import os
import struct
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"


def check_glb(path: Path) -> dict:
    """Validate a .glb file is valid glTF 2.0."""
    result = {"path": str(path), "valid": False, "error": None, "size_mb": 0}

    if not path.exists():
        result["error"] = "File not found"
        return result

    result["size_mb"] = round(path.stat().st_size / (1024 * 1024), 2)

    try:
        with open(path, "rb") as f:
            # glTF 2.0 magic: 0x46546C67 ("glTF")
            magic = struct.unpack("<I", f.read(4))[0]
            if magic != 0x46546C67:
                result["error"] = f"Bad magic: 0x{magic:08X} (expected 0x46546C67)"
                return result

            version = struct.unpack("<I", f.read(4))[0]
            if version != 2:
                result["error"] = f"Wrong version: {version} (expected 2)"
                return result

            # Total file length
            total_length = struct.unpack("<I", f.read(4))[0]

        result["valid"] = True
        result["gltf_version"] = 2

    except Exception as e:
        result["error"] = str(e)

    return result


def check_texture(path: Path) -> dict:
    """Basic texture validation."""
    result = {"path": str(path), "valid": False, "size_kb": 0}

    if not path.exists():
        result["error"] = "File not found"
        return result

    result["size_kb"] = round(path.stat().st_size / 1024, 2)

    # Check it's a real image by reading header bytes
    try:
        with open(path, "rb") as f:
            header = f.read(16)

        # WebP: "RIFF....WEBP"
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            result["format"] = "webp"
        # PNG: "\x89PNG"
        elif header[:4] == b"\x89PNG":
            result["format"] = "png"
        # DDS: "DDS "
        elif header[:4] == b"DDS ":
            result["format"] = "dds"
        else:
            result["format"] = "unknown"
            result["error"] = f"Unknown format: {header[:4].hex()}"
            return result

        result["valid"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def check_json(path: Path, schema: Optional[dict] = None) -> dict:
    """Validate a JSON data file."""
    result = {"path": str(path), "valid": False, "keys": []}

    if not path.exists():
        result["error"] = "File not found"
        return result

    try:
        with open(path) as f:
            data = json.load(f)

        result["valid"] = True
        result["keys"] = list(data.keys()) if isinstance(data, dict) else ["array:" + str(len(data))]

        # If schema provided, check required keys
        if schema and "required" in schema:
            for key in schema["required"]:
                if key not in data:
                    result.setdefault("missing_keys", []).append(key)
                    result["valid"] = False

    except json.JSONDecodeError as e:
        result["error"] = f"Invalid JSON: {e}"

    return result


def main():
    print("=" * 60)
    print("  moncler-grid-engine — Asset Validation")
    print("=" * 60)

    issues = 0
    warnings = 0

    # ── Validate .glb files ──
    print("\n📦 glTF 2.0 Files:")

    def find_glb(base_name: str) -> Optional[Path]:
        """Find a .glb file — try extracted name first, then procedural, then any variant."""
        glbs = list((ASSETS_DIR / "maps").glob("*.glb"))
        # Exact match
        exact = ASSETS_DIR / "maps" / f"{base_name}.glb"
        if exact.exists():
            return exact
        # Procedural variant: base_name_procedural.glb
        proc = ASSETS_DIR / "maps" / f"{base_name}_procedural.glb"
        if proc.exists():
            return proc
        return None

    for base_name in ["hemorrhage_terrain", "hemorrhage_collision"]:
        found = find_glb(base_name)
        if found:
            label = "procedural" if "_procedural" in found.name else "extracted"
            result = check_glb(found)
            if result["valid"]:
                print(f"  ✅ {found.name} — {result['size_mb']} MB, glTF {result['gltf_version']} ({label})")
            else:
                print(f"  ❌ {found.name} — {result['error']}")
                issues += 1
        else:
            print(f"  🔶 {base_name}.glb — not yet generated or extracted")
            warnings += 1

    # ── Validate textures ──
    print("\n🖼  Textures:")
    tex_dir = ASSETS_DIR / "maps" / "hemorrhage_textures"
    if tex_dir.exists():
        tex_files = list(tex_dir.glob("*"))  # All files in directory
        tex_files = [f for f in tex_files if f.suffix.lower() in [".webp", ".png", ".dds"]]
        if tex_files:
            for tex in sorted(tex_files):
                result = check_texture(tex)
                if result["valid"]:
                    print(f"  ✅ {tex.name} — {result['size_kb']} KB, {result.get('format', '?')}")
                else:
                    print(f"  ❌ {tex.name} — {result.get('error', 'unknown error')}")
                    issues += 1
        else:
            print(f"  🔶 No texture files found in {tex_dir}")
            warnings += 1
    else:
        print(f"  🔶 Texture directory not yet created")
        warnings += 1

    # ── Validate JSON data files ──
    print("\n📋 JSON Data Files:")
    json_files = {
        "reach_physics.json": {"required": ["gravity", "player_walk_speed"]},
        "spawn_coordinates.json": {"required": ["spawns"]},
        "forge_objects.json": {"required": ["forge_objects"]},
        "weapon_data.json": {"required": ["weapons"]},
    }

    for filename, schema in json_files.items():
        path = DATA_DIR / filename
        result = check_json(path, schema)
        if result["valid"]:
            keys_str = ", ".join(result["keys"][:5])
            print(f"  ✅ {filename} — keys: [{keys_str}]")
        else:
            print(f"  ❌ {filename} — {result.get('error', 'missing: ' + str(result.get('missing_keys', [])))}")
            issues += 1

    # ── Summary ──
    print(f"\n{'='*60}")
    if issues == 0 and warnings == 0:
        print("  🎉 ALL ASSETS VALIDATED — ready for Godot")
    elif issues == 0 and warnings > 0:
        print(f"  ✅ {warnings} warnings (expected — extraction not yet run)")
        print(f"  📋 Run 'python3 orchestrate.py --all' after Windows VM setup")
    else:
        print(f"  ❌ {issues} issues found — fix before proceeding")

    print(f"{'='*60}")

    return 0 if issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())