# AI Model Registry — Asset Reconstruction

Curated selection of open-weight models for exact game asset recreation.
All tested/selected for dual RTX 4090 (48GB total VRAM).

---

## ⬡ Geometry Reconstruction

### 3D Gaussian Splatting (3DGS)
- **Repo:** github.com/graphdeco-inria/gaussian-splatting
- **VRAM:** 16-24 GB
- **Input:** Multi-view video or images (50-300 frames)
- **Output:** .ply point cloud → mesh extraction
- **Use:** Reconstructing entire map geometry from walkthrough footage
- **Strength:** Highest quality scene reconstruction. Captures fine detail, transparency, reflections
- **When:** Primary method for terrain/BSP reconstruction from reference gameplay

### COLMAP + OpenMVS (Photogrammetry)
- **Repo:** github.com/colmap/colmap + github.com/cdcseacave/openMVS
- **VRAM:** CPU + GPU (8 GB)
- **Input:** High-resolution image sets (100-1000 images)
- **Output:** Dense point cloud → textured mesh
- **Use:** Alternative when 3DGS produces too many artifacts on simple geometry
- **Strength:** Battle-tested. Works on any scene type

### TripoSR (Single Image → 3D)
- **Repo:** github.com/VAST-AI-Research/TripoSR
- **VRAM:** 8 GB
- **Input:** Single RGB image (1024×1024)
- **Output:** .obj mesh with texture
- **Use:** Quick reconstruction of individual Forge pieces from screenshots
- **Strength:** Sub-second inference. Good for simple geometric shapes

### Wonder3D (Single Image → 3D with Normals)
- **Repo:** github.com/xxlong0/Wonder3D
- **VRAM:** 12 GB
- **Input:** Single image or text prompt
- **Output:** Mesh with normal map
- **Use:** Forge objects with complex surface detail
- **Strength:** Produces high-quality normals crucial for PBR materials

### InstantMesh (Single Image → 3D, Highest Quality)
- **Repo:** github.com/TencentARC/InstantMesh
- **VRAM:** 10 GB
- **Input:** Single image
- **Output:** High-quality textured mesh
- **Use:** Primary single-image method for Forge objects
- **Strength:** State-of-the-art single-image reconstruction as of mid-2024

### Zero-1-to-3 (Multi-view Generation)
- **Repo:** github.com/cvlab-columbia/zero123
- **VRAM:** 12 GB
- **Input:** Single image + camera pose
- **Output:** Novel view synthesis
- **Use:** Generate missing viewpoints for photogrammetry
- **Strength:** Can synthesize 360° views from a single reference shot

---

## 🎨 Texture Enhancement

### SUPIR (Practical Image Restoration)
- **Repo:** github.com/Fanghua-Yu/SUPIR
- **VRAM:** 20-24 GB
- **Input:** Low-res/dirty texture (512×512 → 2048×2048)
- **Output:** 4x/8x upscaled texture
- **Use:** Primary method for upscaling extracted game textures
- **Strength:** SOTA for real-world image restoration. Handles compression artifacts

### Real-ESRGAN (General Purpose Upscaling)
- **Repo:** github.com/xinntao/Real-ESRGAN
- **VRAM:** 4-8 GB
- **Input:** Any resolution texture
- **Output:** 4x upscaled
- **Use:** Batch processing large texture sets quickly
- **Strength:** Fast, proven, handles game textures well

### ESRGAN with Game-Specific Models
- **Repo:** github.com/xinntao/ESRGAN
- **VRAM:** 4-8 GB
- **Input:** Game textures
- **Output:** 4x upscaled
- **Use:** Could be fine-tuned on Halo Reach textures specifically
- **Strength:** Trainable on domain-specific data for better results

### Stable Diffusion + ControlNet (Texture Generation)
- **Repo:** github.com/lllyasviel/ControlNet
- **VRAM:** 8-16 GB
- **Input:** Low-res texture + text prompt
- **Output:** Generated high-res texture
- **Use:** Generating missing textures or filling gaps in texture atlases
- **Strength:** Creative gap-filling when extraction fails

---

## 🪨 Material Generation

### DeepBump (Normal Map from Albedo)
- **Repo:** github.com/HugoTini/DeepBump
- **VRAM:** 4 GB
- **Input:** Albedo/diffuse texture
- **Output:** Normal map + Height map
- **Use:** Generating PBR maps from extracted diffuse textures
- **Strength:** Fast, Blender-integrated

### StableMaterial (Full PBR from Single Image)
- **Concept:** SD + ControlNet-based PBR estimation
- **Input:** Single texture image
- **Output:** Albedo, Normal, Roughness, Metallic, AO, Height
- **Use:** Complete material generation when extraction only yields diffuse
- **Strength:** Generates all PBR channels from one input

### Materialize (Non-AI PBR Tool)
- **Repo:** boundingboxsoftware.com/materialize
- **Input:** Diffuse texture
- **Output:** Full PBR texture set
- **Use:** Manual refinement when AI methods produce artifacts
- **Strength:** Deterministic, artist-friendly, no GPU required

---

## 📐 Mesh Optimization

### QuadRemesher (Auto-Retopology)
- **Tool:** exoside.com/quadremesher
- **Input:** Dense triangle mesh (>100K faces)
- **Output:** Clean quad mesh (~5K faces)
- **Use:** Reducing AI-generated meshes to game-ready topology
- **Strength:** Industry standard for auto-retopology

### Simplygon (LOD Generation)
- **Tool:** simplygon.com (free for indie)
- **Input:** High-poly mesh
- **Output:** Multiple LOD levels
- **Use:** Generating LOD chain for Godot's automatic LOD system
- **Strength:** Preserves UVs and materials across LODs

### Instant Meshes (Field-Aligned Remeshing)
- **Repo:** github.com/wjakob/instant-meshes
- **Input:** Triangle mesh
- **Output:** Clean quad mesh
- **Use:** Free alternative to QuadRemesher
- **Strength:** Open source, works on Linux headless

---

## 🔄 Dual RTX 4090 Parallelization Strategy

```
Pipeline Stage Distribution:

GPU 0 (Primary):
  ┌─ 3DGS training ───────────────┐
  ├─ SUPIR texture upscaling ─────┤
  ├─ TripoSR/InstantMesh ─────────┤
  └─ ControlNet inference ────────┘
  
GPU 1 (Secondary):
  ┌─ 3DGS rendering/export ───────┐
  ├─ Real-ESRGAN batch processing ─┤
  ├─ DeepBump material generation ─┤
  └─ COLMAP/OpenMVS processing ───┘

Idle GPU handles next queued task — no dead time.
```