# AI Asset Reconstruction Pipeline

Dual RTX 4090-powered pipeline for reconstructing game assets with exactness.

## Architecture

```
Reference Game (Xbox/MCC/YouTube)
        │
        ▼
┌─ CAPTURE ─────────────────────────────────────────┐
│  OBS Studio → 4K/120fps gameplay footage           │
│  Screenshot tool → per-texture reference images     │
│  Console capture card → raw HDMI feed              │
└────────────────────┬───────────────────────────────┘
                     │ video + screenshots
                     ▼
┌─ RECONSTRUCT ─────────────────────────────────────┐
│  ┌─ 3D Gaussian Splatting → point cloud → mesh    │
│  ├─ InstantMesh/TripoSR → single-image → 3D mesh  │
│  ├─ Zero-1-to-3 → multi-view → consistent mesh    │
│  ├─ Wonder3D → normal + color from single image   │
│  └─ COLMAP → photogrammetry from video frames     │
└────────────────────┬───────────────────────────────┘
                     │ .glb meshes
                     ▼
┌─ ENHANCE ─────────────────────────────────────────┐
│  ┌─ Real-ESRGAN / SUPIR → 4x texture upscaling    │
│  ├─ Stable Diffusion + ControlNet → texture gen   │
│  ├─ DeepBump → normal/roughness from albedo       │
│  ├─ Materialize → full PBR material estimation    │
│  └─ StyleGAN-NADA → texture style matching        │
└────────────────────┬───────────────────────────────┘
                     │ .glb + .webp textures
                     ▼
┌─ CLEANUP ─────────────────────────────────────────┐
│  ┌─ QuadRemesher → automatic retopology           │
│  ├─ Simplygon → LOD generation                    │
│  ├─ Instant Meshes → field-aligned remeshing      │
│  └─ MeshLab → decimation + hole filling           │
└────────────────────┬───────────────────────────────┘
                     │ optimized .glb
                     ▼
              Godot 4.7 Import
```

## Model Selection

See [models/MODEL_REGISTRY.md](models/MODEL_REGISTRY.md) for the complete catalogue
of selected models, their strengths, and when to use each.

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Capture gameplay reference (Windows — OBS required)
python3 scripts/capture_gameplay.py --game "Halo Reach" --map "Hemorrhage" --duration 300

# Reconstruct 3D geometry from captured footage
python3 scripts/reconstruct_3d.py --input captures/hemorrhage_walkthrough.mp4 --method 3dgs

# Enhance textures
python3 scripts/enhance_textures.py --input assets/maps/textures/ --scale 4x --model supir

# Run the full pipeline
python3 ai_orchestrate.py --all --game "Halo Reach" --map "Hemorrhage"
```

## GPU Requirements

| Model | VRAM Needed | Dual 4090 Strategy |
|-------|------------|-------------------|
| 3D Gaussian Splatting | 8-16 GB | GPU 0: training, GPU 1: rendering |
| SUPIR (texture upscale) | 12-24 GB | GPU 0: diffusion, GPU 1: VAE |
| TripoSR (image→3D) | 8 GB | GPU 0: inference, GPU 1: idle/free |
| Real-ESRGAN (upscale) | 4-8 GB | GPU 0: inference, GPU 1: batch parallel |
| Stable Diffusion + CN | 8-16 GB | GPU 0: UNet, GPU 1: ControlNet |
| COLMAP (photogrammetry) | CPU only | Both GPUs free for other tasks |

## Pipeline Stages

### Stage 1: Capture (Windows)
- Record reference gameplay at 4K/120fps via OBS + NVENC
- Capture per-texture screenshots with known camera angles
- Extract keyframes for photogrammetry
- Record console feed via capture card for original hardware reference

### Stage 2: Reconstruct
- Photogrammetry: video keyframes → COLMAP → dense point cloud → mesh
- 3DGS: video → gaussian splats → extracted mesh
- Single-image: reference screenshots → TripoSR/Wonder3D → mesh
- Multi-view: multi-angle shots → Zero-1-to-3 → consistent geometry

### Stage 3: Enhance
- Texture upscaling: 4x/8x with Real-ESRGAN or SUPIR
- Normal/roughness generation from albedo via DeepBump
- Full PBR material estimation via inverse rendering
- Style matching: generated textures matched to reference via StyleGAN

### Stage 4: Cleanup
- Automatic retopology (QuadRemesher)
- LOD generation (Simplygon)
- Mesh decimation and optimization
- UV unwrapping and packing
- Collision mesh extraction