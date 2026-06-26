#!/usr/bin/env python3
"""
ai_orchestrate.py — AI-powered asset reconstruction pipeline.

Single command to run the full AI pipeline:
  python3 ai_orchestrate.py --all --game "Halo Reach" --map "Hemorrhage"

Stages:
  1. CAPTURE   — Record reference gameplay (OBS + capture card)
  2. RECONSTRUCT — 3DGS/NeRF/InstantMesh → .glb
  3. ENHANCE   — SUPIR/ESRGAN texture upscale + material generation
  4. CLEANUP   — Retopology, LOD, mesh optimization

Dual RTX 4090 aware: distributes work across both GPUs.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AI_DIR = PROJECT_ROOT / "tools" / "ai_pipeline"
SCRIPTS_DIR = AI_DIR / "scripts"
CONFIGS_DIR = AI_DIR / "configs"
MODELS_DIR = AI_DIR / "models"

# GPU detection
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_COUNT = pynvml.nvmlDeviceGetCount()
    GPUS = []
    for i in range(GPU_COUNT):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        name = pynvml.nvmlDeviceGetName(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        GPUS.append({
            "index": i,
            "name": name,
            "vram_total_gb": round(mem.total / (1024**3), 1),
            "vram_free_gb": round(mem.free / (1024**3), 1),
        })
    HAS_GPU = GPU_COUNT > 0
except ImportError:
    HAS_GPU = False
    GPU_COUNT = 0
    GPUS = []
    print("⚠️  pynvml not installed — GPU detection disabled")
    print("   pip3 install nvidia-ml-py")


def banner(text: str, char: str = "─") -> None:
    width = 72
    print(f"\n{char * width}")
    print(f"  {text}")
    print(f"{char * width}\n")


def run_step(name: str, script: str, args: list = None, gpu: int = 0) -> int:
    """Run a pipeline step, optionally pinned to a specific GPU."""
    banner(f"STAGE: {name}")

    cmd = [sys.executable, str(SCRIPTS_DIR / script)]
    if args:
        cmd.extend(args)

    env = os.environ.copy()
    if gpu is not None and HAS_GPU:
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
        print(f"  🎮 Pinned to GPU {gpu}")

    print(f"  ▶ {' '.join(cmd)}")
    start = time.time()
    result = subprocess.run(cmd, env=env, cwd=str(PROJECT_ROOT))
    elapsed = time.time() - start

    status = "✅" if result.returncode == 0 else "❌"
    print(f"\n  {status} {name} completed in {elapsed:.1f}s (exit {result.returncode})")
    return result.returncode


def parallel_gpu_stages(stages: list[tuple]) -> int:
    """Run two stages in parallel, one on each GPU."""
    import threading

    results = {}

    def worker(name, script, args, gpu):
        results[gpu] = run_step(name, script, args, gpu)

    threads = []
    for name, script, args, gpu in stages:
        t = threading.Thread(target=worker, args=(name, script, args, gpu))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return sum(results.values())


def stage_capture(args) -> int:
    """Capture reference gameplay footage."""
    return run_step(
        "Capture Gameplay",
        "capture_gameplay.py",
        [
            "--game", args.game,
            "--map", args.map,
            "--duration", str(args.duration),
            "--output", str(PROJECT_ROOT / "tools" / "ai_pipeline" / "capture" / "sessions")
        ],
        gpu=None  # OBS doesn't need CUDA
    )


def stage_reconstruct_3dgs(args) -> int:
    """Reconstruct 3D geometry via 3D Gaussian Splatting."""
    input_dir = PROJECT_ROOT / "tools" / "ai_pipeline" / "capture" / "sessions" / args.map
    return run_step(
        "3D Reconstruction (3DGS)",
        "reconstruct_3d.py",
        [
            "--input", str(input_dir),
            "--method", "3dgs",
            "--output", str(PROJECT_ROOT / "assets" / "maps"),
            "--gpu", "0"
        ],
        gpu=0  # GPU 0: 3DGS training
    )


def stage_reconstruct_instantmesh(args) -> int:
    """Reconstruct Forge objects via InstantMesh."""
    input_dir = PROJECT_ROOT / "tools" / "ai_pipeline" / "capture" / "sessions" / args.map / "screenshots"
    return run_step(
        "Forge Object Reconstruction (InstantMesh)",
        "reconstruct_3d.py",
        [
            "--input", str(input_dir),
            "--method", "instantmesh",
            "--output", str(PROJECT_ROOT / "assets" / "forge_pieces"),
            "--gpu", "1"  # GPU 1 while GPU 0 does 3DGS
        ],
        gpu=1
    )


def stage_enhance_textures(args) -> int:
    """Enhance textures with SUPIR + Real-ESRGAN."""
    return run_step(
        "Texture Enhancement",
        "enhance_textures.py",
        [
            "--input", str(PROJECT_ROOT / "assets" / "maps" / "hemorrhage_textures"),
            "--scale", "4x",
            "--model", args.texture_model,
            "--gpu", "1"
        ],
        gpu=1  # GPU 1: texture work while GPU 0 does reconstruction
    )


def stage_generate_materials(args) -> int:
    """Generate PBR materials from enhanced textures."""
    return run_step(
        "Material Generation",
        "enhance_textures.py",
        [
            "--input", str(PROJECT_ROOT / "assets" / "maps" / "hemorrhage_textures"),
            "--mode", "pbr",
            "--gpu", "1"
        ],
        gpu=1
    )


def stage_cleanup_geometry(args) -> int:
    """Clean up and optimize reconstructed meshes."""
    return run_step(
        "Geometry Cleanup",
        "cleanup_geometry.py",
        [
            "--input", str(PROJECT_ROOT / "assets"),
            "--lod-levels", "3",
            "--target-poly", "50000"
        ],
        gpu=None  # CPU-bound
    )


def stage_validate_all(args) -> int:
    """Run all validation checks."""
    return run_step(
        "Validation",
        "../extraction/scripts/validate_assets.py",
        [],
        gpu=None
    )


def main():
    parser = argparse.ArgumentParser(
        description="moncler-grid-engine AI Asset Reconstruction Pipeline"
    )
    parser.add_argument("--all", action="store_true",
                        help="Run the complete AI pipeline")
    parser.add_argument("--game", default="Halo Reach",
                        help="Game to reconstruct assets for")
    parser.add_argument("--map", default="Hemorrhage",
                        help="Map/variant to target")
    parser.add_argument("--duration", type=int, default=300,
                        help="Gameplay capture duration in seconds")
    parser.add_argument("--texture-model", default="supir",
                        choices=["supir", "esrgan", "both"],
                        help="Texture enhancement model")
    parser.add_argument("--skip-capture", action="store_true",
                        help="Skip gameplay capture (use existing footage)")
    parser.add_argument("--skip-cleanup", action="store_true",
                        help="Skip geometry cleanup")
    parser.add_argument("--stage", choices=[
        "capture", "reconstruct", "enhance", "cleanup", "validate"
    ], help="Run a single stage")

    args = parser.parse_args()

    # ── GPU info ─────────────────────────────────────────────────────────
    banner("GPU DETECTION", "═")
    if HAS_GPU:
        print(f"  Found {GPU_COUNT} GPU(s):")
        for gpu in GPUS:
            print(f"    GPU {gpu['index']}: {gpu['name']} — {gpu['vram_total_gb']} GB VRAM")
    else:
        print("  ⚠️  No CUDA GPUs detected — some stages will fail")

    # ── Pipeline ─────────────────────────────────────────────────────────
    if args.all:
        banner("FULL AI PIPELINE", "═")
        print(f"  Game: {args.game}")
        print(f"  Map:  {args.map}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        exit_code = 0

        # Stage 1: Capture (Windows, no GPU)
        if not args.skip_capture:
            exit_code |= stage_capture(args)

        # Stage 2: Reconstruct (parallel GPU 0 + GPU 1)
        banner("PARALLEL RECONSTRUCTION (Dual GPU)")
        # Run 3DGS on GPU 0 and InstantMesh on GPU 1 simultaneously
        exit_code |= parallel_gpu_stages([
            ("3DGS Scene Reconstruction", "reconstruct_3d.py",
             ["--input", str(PROJECT_ROOT / "tools" / "ai_pipeline" / "capture" / "sessions" / args.map),
              "--method", "3dgs",
              "--output", str(PROJECT_ROOT / "assets" / "maps")], 0),
            ("Forge Object Reconstruction", "reconstruct_3d.py",
             ["--input", str(PROJECT_ROOT / "tools" / "ai_pipeline" / "capture" / "sessions" / args.map / "screenshots"),
              "--method", "instantmesh",
              "--output", str(PROJECT_ROOT / "assets" / "forge_pieces")], 1),
        ])

        # Stage 3: Enhance textures + materials (GPU 1)
        exit_code |= stage_enhance_textures(args)
        exit_code |= stage_generate_materials(args)

        # Stage 4: Cleanup (CPU)
        if not args.skip_cleanup:
            exit_code |= stage_cleanup_geometry(args)

        # Stage 5: Validate
        exit_code |= stage_validate_all(args)

        banner("PIPELINE COMPLETE", "═")
        if exit_code == 0:
            print("  🎉 All stages passed. Assets ready for Godot 4.7 import.")
        else:
            print(f"  ⚠️  Pipeline completed with exit code {exit_code}")
        
        return exit_code

    # ── Single stage ─────────────────────────────────────────────────────
    stage_map = {
        "capture": stage_capture,
        "reconstruct": lambda a: stage_reconstruct_3dgs(a),
        "enhance": stage_enhance_textures,
        "cleanup": stage_cleanup_geometry,
        "validate": stage_validate_all,
    }

    if args.stage in stage_map:
        return stage_map[args.stage](args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())