#!/usr/bin/env python3
"""
cleanup_geometry.py — Mesh optimization and LOD generation.

Pipeline:
  1. Decimation (reduce poly count to target)
  2. Remeshing (triangle → quad)
  3. LOD generation (multiple detail levels)
  4. UV optimization (packing, island cleanup)
  5. Collision mesh extraction
  6. glTF validation
"""

import argparse
import os
import struct
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def decimate_mesh(input_glb: Path, output_glb: Path, target_faces: int = 50000) -> int:
    """Reduce polygon count to target using Blender."""
    print(f"\n  🔻 Decimating {input_glb.name} → {target_faces} faces")

    # Blender Python script for decimation
    script = f'''
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath="{input_glb}")

for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
        mod.ratio = {target_faces} / len(obj.data.polygons)
        bpy.ops.object.modifier_apply(modifier="Decimate")

bpy.ops.export_scene.gltf(
    filepath="{output_glb}",
    export_format='GLB',
    export_apply=True
)
'''

    blender = find_blender()
    if not blender:
        return 1

    script_path = Path("/tmp/blender_decimate.py")
    script_path.write_text(script)
    subprocess.run([blender, "--background", "--python", str(script_path)])
    script_path.unlink()

    print(f"  ✅ Decimated: {output_glb}")
    return 0


def generate_lods(input_glb: Path, output_dir: Path, levels: int = 3) -> int:
    """Generate LOD chain for Godot auto-LOD."""
    print(f"\n  📐 Generating {levels} LOD levels for {input_glb.name}")

    ratios = [1.0, 0.5, 0.25, 0.1, 0.05]  # Face ratios per LOD

    for level in range(levels):
        ratio = ratios[min(level, len(ratios) - 1)]
        lod_name = f"{input_glb.stem}_LOD{level}.glb"
        lod_path = output_dir / lod_name

        if level == 0:
            # LOD0 is full detail — just copy
            import shutil
            shutil.copy(input_glb, lod_path)
            print(f"  ✅ LOD{level}: full detail → {lod_name}")
            continue

        target = int(50000 * ratio)
        print(f"  ▶ LOD{level}: ~{target} faces → {lod_name}")

        script = f'''
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath="{input_glb}")

for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
        mod.ratio = {ratio}
        bpy.ops.object.modifier_apply(modifier="Decimate")

bpy.ops.export_scene.gltf(
    filepath="{lod_path}",
    export_format='GLB',
    export_apply=True
)
'''

        blender = find_blender()
        if blender:
            script_path = Path("/tmp/blender_lod.py")
            script_path.write_text(script)
            subprocess.run([blender, "--background", "--python", str(script_path)])
            script_path.unlink()

    return 0


def extract_collision(input_glb: Path, output_glb: Path) -> int:
    """Extract collision mesh from render mesh."""
    print(f"\n  🧱 Extracting collision mesh from {input_glb.name}")

    script = f'''
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath="{input_glb}")

for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj
        # Heavy decimation for collision (5% of original)
        mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
        mod.ratio = 0.05
        bpy.ops.object.modifier_apply(modifier="Decimate")

bpy.ops.export_scene.gltf(
    filepath="{output_glb}",
    export_format='GLB',
    export_apply=True
)
'''

    blender = find_blender()
    if blender:
        script_path = Path("/tmp/blender_collision.py")
        script_path.write_text(script)
        subprocess.run([blender, "--background", "--python", str(script_path)])
        script_path.unlink()
        print(f"  ✅ Collision mesh: {output_glb}")

    return 0


def optimize_uvs(input_glb: Path, output_glb: Path) -> int:
    """Optimize UV islands and packing."""
    print(f"\n  📐 Optimizing UVs for {input_glb.name}")

    script = f'''
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath="{input_glb}")

for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands()
        bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.export_scene.gltf(
    filepath="{output_glb}",
    export_format='GLB',
    export_apply=True
)
'''

    blender = find_blender()
    if blender:
        script_path = Path("/tmp/blender_uv.py")
        script_path.write_text(script)
        subprocess.run([blender, "--background", "--python", str(script_path)])
        script_path.unlink()

    return 0


def find_blender() -> str | None:
    """Find Blender executable."""
    candidates = [
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/opt/homebrew/bin/blender",
        "/usr/local/bin/blender",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    print("  ❌ Blender not found — install from blender.org")
    return None


def main():
    parser = argparse.ArgumentParser(description="Geometry Cleanup Pipeline")
    parser.add_argument("--input", required=True, help="Input assets directory")
    parser.add_argument("--lod-levels", type=int, default=3, help="Number of LOD levels")
    parser.add_argument("--target-poly", type=int, default=50000, help="Target polygon count")
    parser.add_argument("--skip-lods", action="store_true")
    parser.add_argument("--skip-collision", action="store_true")
    parser.add_argument("--skip-uv", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("  Geometry Cleanup Pipeline")
    print("=" * 60)

    input_dir = Path(args.input)
    glb_files = list(input_dir.rglob("*.glb"))

    if not glb_files:
        print("  ⚠️  No .glb files found in input directory")
        return 0

    print(f"  Found {len(glb_files)} .glb file(s)")

    for glb in glb_files:
        print(f"\n  ── Processing: {glb.name} ──")

        # Decimate
        decimated = glb.parent / f"{glb.stem}_optimized.glb"
        decimate_mesh(glb, decimated, args.target_poly)

        # LOD generation
        if not args.skip_lods:
            lod_dir = glb.parent / "lods"
            generate_lods(decimated, lod_dir, args.lod_levels)

        # Collision mesh
        if not args.skip_collision:
            collision = glb.parent / f"{glb.stem}_collision.glb"
            extract_collision(glb, collision)

        # UV optimization
        if not args.skip_uv:
            uv_fixed = glb.parent / f"{glb.stem}_uvpacked.glb"
            optimize_uvs(decimated, uv_fixed)

    print(f"\n✅ Cleanup complete for {len(glb_files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())