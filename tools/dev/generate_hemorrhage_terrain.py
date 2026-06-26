#!/usr/bin/env python3
"""
generate_hemorrhage_terrain.py — Procedural Hemorrhage canyon terrain generator.

Creates a Hemorrhage-like canyon mesh in Blender and exports as .glb for Godot.
Hemorrhage (Forge World variant) is a large canyon with:
  - Two base structures at opposite ends
  - Open terrain with rolling hills
  - Rocky outcroppings along canyon walls
  - Central open area for vehicle combat
  - Elevated sniper perches

Usage:
  blender --background --python generate_hemorrhage_terrain.py
  python3 generate_hemorrhage_terrain.py  # standalone with numpy
"""

import math
import struct
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "assets" / "maps"

# Try to run in Blender
try:
    import bpy
    import bmesh
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False
    print("Not running in Blender — using numpy for mesh generation")
    try:
        import numpy as np
        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False
        print("numpy not installed — pip3 install numpy")


# ── Hemorrhage Layout Constants ──────────────────────────────────────────────

# Map dimensions (Reach world units)
MAP_WIDTH = 80.0   # X axis
MAP_LENGTH = 120.0  # Z axis
MAP_HEIGHT = 15.0   # Y axis (max terrain height)

# Canyon parameters
CANYON_WIDTH = 30.0
CANYON_DEPTH = 8.0
WALL_SLOPE = 2.5  # How steep the canyon walls are

# Base positions
BASE_RED = (-30.0, 0.0)   # Red base (x, z)
BASE_BLUE = (30.0, 0.0)   # Blue base

# Key terrain features
FEATURES = [
    # (name, x, z, radius, height, type)
    ("rock_outcrop_1", -20.0, -15.0, 4.0, 3.0, "hill"),
    ("rock_outcrop_2", 15.0, 20.0, 3.5, 2.5, "hill"),
    ("sniper_perch_east", 25.0, -10.0, 2.0, 5.0, "pillar"),
    ("sniper_perch_west", -25.0, 10.0, 2.0, 5.0, "pillar"),
    ("central_hill", 0.0, 5.0, 8.0, 2.0, "hill"),
    ("ravine_north", 0.0, -30.0, 6.0, -2.0, "ditch"),
    ("ravine_south", 0.0, 35.0, 5.0, -1.5, "ditch"),
    ("cave_entrance", -15.0, -25.0, 3.0, 0.0, "cave"),
    ("bunker_hill", 20.0, -20.0, 5.0, 4.0, "hill"),
]

# Forge object placements (approximate from known Infection variants)
FORGE_WALLS = [
    # Barricade walls (typical Infection layout)
    {"type": "wall_straight", "pos": (-28.0, 1.0, -5.0), "rot": (0, 0, 0)},
    {"type": "wall_straight", "pos": (-28.0, 1.0, -3.0), "rot": (0, 0, 0)},
    {"type": "wall_straight", "pos": (-28.0, 1.0, -1.0), "rot": (0, 0, 0)},
    {"type": "wall_straight", "pos": (-28.0, 1.0, 1.0), "rot": (0, 0, 0)},
    {"type": "wall_straight", "pos": (-28.0, 1.0, 3.0), "rot": (0, 0, 0)},
    {"type": "wall_straight", "pos": (28.0, 1.0, -5.0), "rot": (0, 180, 0)},
    {"type": "wall_straight", "pos": (28.0, 1.0, -3.0), "rot": (0, 180, 0)},
    {"type": "wall_straight", "pos": (28.0, 1.0, -1.0), "rot": (0, 180, 0)},
    {"type": "wall_straight", "pos": (28.0, 1.0, 1.0), "rot": (0, 180, 0)},
    {"type": "wall_straight", "pos": (28.0, 1.0, 3.0), "rot": (0, 180, 0)},
    # Central cover
    {"type": "wall_straight", "pos": (0.0, 1.0, 10.0), "rot": (0, 90, 0)},
    {"type": "wall_straight", "pos": (0.0, 1.0, -10.0), "rot": (0, 90, 0)},
    {"type": "block_2x2", "pos": (5.0, 0.5, 0.0), "rot": (0, 0, 0)},
    {"type": "block_2x2", "pos": (-5.0, 0.5, 0.0), "rot": (0, 0, 0)},
]

SPAWN_POINTS = [
    {"team": "human", "pos": (-28.0, 1.5, 0.0)},
    {"team": "human", "pos": (-26.0, 1.5, -4.0)},
    {"team": "human", "pos": (-26.0, 1.5, 4.0)},
    {"team": "human", "pos": (28.0, 1.5, 0.0)},
    {"team": "human", "pos": (26.0, 1.5, -4.0)},
    {"team": "human", "pos": (26.0, 1.5, 4.0)},
    {"team": "infected", "pos": (0.0, 1.5, 20.0)},
    {"team": "infected", "pos": (0.0, 1.5, -20.0)},
    {"team": "infected", "pos": (10.0, 1.5, 0.0)},
    {"team": "infected", "pos": (-10.0, 1.5, 0.0)},
]


def height_function(x: float, z: float) -> float:
    """Calculate terrain height at (x, z) for Hemorrhage canyon."""
    # Base canyon shape
    canyon_edge = CANYON_WIDTH / 2.0
    dist_from_center = abs(x)

    if dist_from_center < canyon_edge:
        # Inside canyon — flat-ish with slight undulation
        h = 0.0
        h += math.sin(z * 0.1) * 0.5  # Longitudinal waves
        h += math.cos(x * 0.15) * 0.3  # Lateral variation
    else:
        # Canyon walls — slope up
        wall_dist = dist_from_center - canyon_edge
        h = wall_dist * WALL_SLOPE
        h = min(h, MAP_HEIGHT)  # Cap at max height

    # Add terrain features (hills, rocks)
    for name, fx, fz, radius, height, ftype in FEATURES:
        dx = x - fx
        dz = z - fz
        dist = math.sqrt(dx * dx + dz * dz)
        if dist < radius:
            if ftype == "hill":
                falloff = 1.0 - (dist / radius)
                h += height * falloff * falloff
            elif ftype == "ditch":
                falloff = 1.0 - (dist / radius)
                h += height * falloff * falloff  # negative height = ditch
            elif ftype == "pillar":
                falloff = 1.0 - (dist / radius)
                falloff = max(0.0, falloff * 2.0 - 1.0)  # Steep pillar
                h += height * falloff
            elif ftype == "cave":
                if dist < radius * 0.5:
                    h -= 2.0  # Cave entrance depression

    # Base areas — slightly elevated
    if abs(x - BASE_RED[0]) < 10 and abs(z - BASE_RED[1]) < 10:
        h += 0.5
    if abs(x - BASE_BLUE[0]) < 10 and abs(z - BASE_BLUE[1]) < 10:
        h += 0.5

    return h


def generate_terrain_blender():
    """Generate terrain mesh in Blender."""
    print("=== Generating Hemorrhage Terrain in Blender ===")

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Grid resolution
    nx = 200  # X subdivisions
    nz = 300  # Z subdivisions
    dx = MAP_WIDTH / nx
    dz = MAP_LENGTH / nz

    # Create mesh
    mesh = bpy.data.meshes.new("Hemorrhage_Terrain")
    obj = bpy.data.objects.new("Hemorrhage_Terrain", mesh)
    bpy.context.collection.objects.link(obj)

    # Generate vertices
    verts = []
    faces = []
    for iz in range(nz + 1):
        for ix in range(nx + 1):
            x = -MAP_WIDTH / 2 + ix * dx
            z = -MAP_LENGTH / 2 + iz * dz
            y = height_function(x, z)
            verts.append((x, y, z))

    # Generate faces
    for iz in range(nz):
        for ix in range(nx):
            i = iz * (nx + 1) + ix
            faces.append((i, i + 1, i + nx + 2, i + nx + 1))

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    # Set as active
    bpy.context.view_layer.objects.active = obj

    # Add material
    mat = bpy.data.materials.new("Terrain")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.28, 0.18, 1.0)  # Desert/tan
    obj.data.materials.append(mat)

    # Export as .glb
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "hemorrhage_terrain_procedural.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format='GLB',
        export_apply=True
    )
    print(f"✅ Terrain exported: {output_path}")


def generate_collision_blender():
    """Generate collision mesh from terrain."""
    print("=== Generating Collision Mesh ===")

    # Duplicate terrain and decimate
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Re-generate at lower resolution for collision
    mesh = bpy.data.meshes.new("Hemorrhage_Collision")
    obj = bpy.data.objects.new("Hemorrhage_Collision", mesh)
    bpy.context.collection.objects.link(obj)

    nx = 50  # Lower res for collision
    nz = 75
    dx = MAP_WIDTH / nx
    dz = MAP_LENGTH / nz

    verts = []
    for iz in range(nz + 1):
        for ix in range(nx + 1):
            x = -MAP_WIDTH / 2 + ix * dx
            z = -MAP_LENGTH / 2 + iz * dz
            y = height_function(x, z)
            verts.append((x, y, z))

    faces = []
    for iz in range(nz):
        for ix in range(nx):
            i = iz * (nx + 1) + ix
            faces.append((i, i + 1, i + nx + 2, i + nx + 1))

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    output_path = OUTPUT_DIR / "hemorrhage_collision_procedural.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format='GLB',
        export_apply=True
    )
    print(f"✅ Collision exported: {output_path}")


def export_forge_json():
    """Export Forge object placements as JSON."""
    import json
    forge_data = {
        "_comment": "Procedurally generated Hemorrhage Infection Forge layout",
        "forge_objects": FORGE_WALLS,
    }
    output_path = PROJECT_ROOT / "data" / "forge_objects_procedural.json"
    output_path.write_text(json.dumps(forge_data, indent=2))
    print(f"✅ Forge objects exported: {output_path}")


def export_spawn_json():
    """Export spawn points as JSON."""
    import json
    spawn_data = {
        "_comment": "Procedurally generated Hemorrhage spawn points",
        "spawns": [
            {
                "id": i,
                "pos": s["pos"],
                "team": s["team"],
                "rot": 0.0,
                "label": f"{s['team']}_spawn_{i}"
            }
            for i, s in enumerate(SPAWN_POINTS)
        ]
    }
    output_path = PROJECT_ROOT / "data" / "spawn_coordinates_procedural.json"
    output_path.write_text(json.dumps(spawn_data, indent=2))
    print(f"✅ Spawn points exported: {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if IN_BLENDER:
        generate_terrain_blender()
        generate_collision_blender()
    else:
        print("Run this script inside Blender for mesh generation:")
        print("  blender --background --python generate_hemorrhage_terrain.py")
        print("")
        print("Exporting JSON data files (no Blender needed)...")
        export_forge_json()
        export_spawn_json()