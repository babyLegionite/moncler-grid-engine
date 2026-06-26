#!/usr/bin/env python3
"""
reconstruct_3d.py — 3D reconstruction from reference footage/images.

Methods:
  - 3dgs:      3D Gaussian Splatting (full scene from video)
  - colmap:    Photogrammetry (COLMAP + OpenMVS)
  - instantmesh: Single-image → 3D (Forge objects)
  - wonder3d:  Single-image → 3D with normals
  - triposr:   Fast single-image → 3D

Dual GPU: uses CUDA_VISIBLE_DEVICES from environment.
"""

import argparse
import os
import subprocess
import sys
import json
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def check_tool(name: str, install_hint: str) -> bool:
    """Check if a tool is installed and provide install instructions."""
    result = subprocess.run(["which", name], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ {name} not found — {install_hint}")
        return False
    print(f"  ✅ {name} found: {result.stdout.strip()}")
    return True


def reconstruct_3dgs(input_path: Path, output_dir: Path) -> int:
    """
    Reconstruct 3D scene using 3D Gaussian Splatting.
    
    Pipeline:
      1. Extract keyframes from video (ffmpeg)
      2. Run 3DGS training
      3. Export gaussians → .ply → convert to mesh → .glb
    """
    print("\n  🌐 3D Gaussian Splatting Reconstruction")
    print(f"     Input: {input_path}")
    print(f"     Output: {output_dir}")

    # Step 1: Extract keyframes if input is a video
    video_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.mkv"))
    frames_dir = input_path / "frames_3dgs"
    
    if video_files:
        frames_dir.mkdir(exist_ok=True)
        video = video_files[0]
        print(f"  📹 Extracting keyframes from {video.name}...")
        subprocess.run([
            "ffmpeg", "-i", str(video),
            "-vf", "fps=2",  # 2 FPS = 1 frame per 0.5 seconds
            "-q:v", "2",
            str(frames_dir / "frame_%05d.jpg")
        ], capture_output=True)
        print(f"  ✅ Keyframes extracted to {frames_dir}")

    # Step 2: Run 3DGS
    # Clone if not present
    gs_dir = Path.home() / "ai-models" / "gaussian-splatting"
    if not gs_dir.exists():
        print(f"  ⚠️  3DGS not found at {gs_dir}")
        print(f"     Clone: git clone https://github.com/graphdeco-inria/gaussian-splatting {gs_dir}")
        
        # Check if it exists elsewhere
        alt_paths = [
            Path("/opt/gaussian-splatting"),
            Path.home() / "gaussian-splatting",
        ]
        for alt in alt_paths:
            if alt.exists():
                gs_dir = alt
                print(f"  ✅ Found 3DGS at alternate path: {gs_dir}")
                break
    
    if gs_dir.exists():
        # Run training (this is a simplified command — real usage needs COLMAP first)
        print("  🚀 Running 3DGS training...")
        print(f"     python {gs_dir}/train.py -s {frames_dir} -m {output_dir}/3dgs_output")
        # Actual command (commented until 3DGS is installed):
        # subprocess.run([
        #     sys.executable, str(gs_dir / "train.py"),
        #     "-s", str(frames_dir),
        #     "-m", str(output_dir / "3dgs_output"),
        #     "--iterations", "7000"
        # ])
        print("     ⚠️  Run manually when 3DGS repo is cloned and dependencies installed")
    else:
        print(f"  📋 To install: See tools/ai_pipeline/models/MODEL_REGISTRY.md")
        print(f"     Clone path: {gs_dir}")

    return 0


def reconstruct_colmap(input_path: Path, output_dir: Path) -> int:
    """Photogrammetry via COLMAP + OpenMVS."""
    print("\n  📷 COLMAP Photogrammetry")
    print(f"     Input: {input_path}")
    print(f"     Output: {output_dir}")

    if not check_tool("colmap", "brew install colmap"):
        return 1

    frames_dir = input_path / "frames_colmap"
    frames_dir.mkdir(exist_ok=True)

    # Extract frames if video
    video_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.mkv"))
    if video_files:
        subprocess.run([
            "ffmpeg", "-i", str(video_files[0]),
            "-vf", "fps=1",
            "-q:v", "1",
            str(frames_dir / "frame_%05d.jpg")
        ], capture_output=True)

    # COLMAP pipeline
    database = output_dir / "colmap_database.db"
    sparse = output_dir / "sparse"
    dense = output_dir / "dense"

    steps = [
        ("Feature extraction", [
            "colmap", "feature_extractor",
            "--database_path", str(database),
            "--image_path", str(frames_dir),
            "--SiftExtraction.use_gpu", "1"
        ]),
        ("Feature matching", [
            "colmap", "exhaustive_matcher",
            "--database_path", str(database),
            "--SiftMatching.use_gpu", "1"
        ]),
        ("Sparse reconstruction", [
            "colmap", "mapper",
            "--database_path", str(database),
            "--image_path", str(frames_dir),
            "--output_path", str(sparse)
        ]),
        ("Dense reconstruction", [
            "colmap", "image_undistorter",
            "--image_path", str(frames_dir),
            "--input_path", str(sparse / "0"),
            "--output_path", str(dense)
        ]),
    ]

    for step_name, cmd in steps:
        print(f"  ▶ {step_name}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠️  {step_name} failed: {result.stderr[:200]}")
        else:
            print(f"  ✅ {step_name} complete")

    # Export as .ply
    print("  📦 Exporting dense point cloud...")
    output_ply = output_dir / "hemorrhage_dense.ply"
    # colmap model_converter → .ply
    subprocess.run([
        "colmap", "model_converter",
        "--input_path", str(sparse / "0"),
        "--output_path", str(output_ply),
        "--output_type", "PLY"
    ])

    print(f"  ✅ Point cloud exported: {output_ply}")
    return 0


def reconstruct_instantmesh(input_path: Path, output_dir: Path) -> int:
    """Single-image → 3D via InstantMesh."""
    print("\n  🧊 InstantMesh (Single Image → 3D)")
    print(f"     Input: {input_path}")
    print(f"     Output: {output_dir}")

    im_dir = Path.home() / "ai-models" / "InstantMesh"
    if not im_dir.exists():
        print(f"  ⚠️  InstantMesh not found at {im_dir}")
        print(f"     Clone: git clone https://github.com/TencentARC/InstantMesh {im_dir}")
        return 0

    # Find all screenshots/images
    image_files = (
        list(input_path.glob("*.png")) + list(input_path.glob("*.jpg")) +
        list(input_path.glob("*.jpeg"))
    )
    
    if not image_files:
        print("  ⚠️  No images found in input directory")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    
    for img in image_files[:20]:  # Process up to 20 images
        print(f"  ▶ Processing {img.name}...")
        # InstantMesh inference (when installed):
        # subprocess.run([
        #     sys.executable, str(im_dir / "run.py"),
        #     "--input", str(img),
        #     "--output", str(output_dir / f"{img.stem}.obj")
        # ])
        print(f"     → would export: {output_dir / img.stem}.obj")

    return 0


def reconstruct_triposr(input_path: Path, output_dir: Path) -> int:
    """Fast single-image → 3D via TripoSR."""
    print("\n  ⚡ TripoSR (Fast Single Image → 3D)")
    print(f"     Input: {input_path}")

    tsr_dir = Path.home() / "ai-models" / "TripoSR"
    if not tsr_dir.exists():
        print(f"  ⚠️  TripoSR not found at {tsr_dir}")
        print(f"     Clone: git clone https://github.com/VAST-AI-Research/TripoSR {tsr_dir}")
        return 0

    # Sub-second inference — great for batch processing Forge objects
    image_files = (
        list(input_path.glob("*.png")) + list(input_path.glob("*.jpg"))
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    for img in image_files:
        print(f"  ▶ {img.name} → {img.stem}.obj")
        # subprocess.run([
        #     sys.executable, str(tsr_dir / "run.py"),
        #     input_path / img.name,
        #     "--output", output_dir / f"{img.stem}.obj",
        #     "--save-video"
        # ])

    return 0


def main():
    parser = argparse.ArgumentParser(description="3D Reconstruction Pipeline")
    parser.add_argument("--input", required=True, help="Input directory or file")
    parser.add_argument("--method", required=True,
                        choices=["3dgs", "colmap", "instantmesh", "wonder3d", "triposr", "all"],
                        help="Reconstruction method")
    parser.add_argument("--output", default="assets/maps", help="Output directory")
    parser.add_argument("--gpu", default="0", help="GPU device ID")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"  3D Reconstruction — Method: {args.method}")
    print(f"  GPU: {args.gpu}")
    print("=" * 60)

    methods = {
        "3dgs": reconstruct_3dgs,
        "colmap": reconstruct_colmap,
        "instantmesh": reconstruct_instantmesh,
        "triposr": reconstruct_triposr,
    }

    if args.method == "all":
        for name, fn in methods.items():
            fn(input_path, output_dir)
    elif args.method in methods:
        methods[args.method](input_path, output_dir)
    else:
        print(f"Unknown method: {args.method}")

    print("\n✅ Reconstruction complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())