# Extraction Pipeline

Programmatic, reproducible asset extraction from Halo: Reach MCC via Windows VM.

## Architecture

```
macOS (moncler-grid-engine)
│
├── tools/extraction/
│   ├── orchestrate.py          ← MAIN: single command entry point
│   ├── config.yaml             ← VM connection + tool paths
│   ├── scripts/
│   │   ├── extract_assets.py   ← SSH into VM, run HREK/Assembly
│   │   ├── process_assets.py   ← Blender post-processing
│   │   └── validate_assets.py  ← Verify .glb + JSON correctness
│   ├── configs/
│   │   └── utm.plist           ← UTM VM configuration template
│   ├── vm/
│   │   └── windows_setup.ps1   ← Auto-configure Windows VM
│   └── requirements.txt
│
├── assets/                     ← Output: .glb + textures land here
├── data/                       ← Output: JSON data lands here
└── scenes/                     ← Godot scenes reference extracted assets
```

## Quick Start

```bash
# 1. Install macOS prerequisites
brew install --cask utm
pip3 install -r tools/extraction/requirements.txt

# 2. Create Windows 11 ARM VM in UTM
#    (manual step — download Windows 11 ARM ISO, create VM with 8GB+ RAM)

# 3. On the Windows VM, run the setup script
#    (Right-click windows_setup.ps1 → Run with PowerShell as Admin)
#    This installs: Steam, MCC, HREK, Assembly, SSH server, Python

# 4. Configure connection
cp tools/extraction/config.example.yaml tools/extraction/config.yaml
# Edit config.yaml with your VM's IP address

# 5. Extract everything
python3 tools/extraction/orchestrate.py --all
```

## What It Extracts

| Asset | Source | Output |
|-------|--------|--------|
| Terrain BSP mesh | `forge_halo.map` → HREK → Blender | `assets/maps/hemorrhage_terrain.glb` |
| Collision mesh | `forge_halo.map` → Assembly → collision_model tag | `assets/maps/hemorrhage_collision.glb` |
| Textures | `forge_halo.map` → Assembly → bitmap tags | `assets/maps/hemorrhage_textures/*.webp` |
| Spawn coordinates | `forge_halo.map` → Assembly → scenario tag | `data/spawn_coordinates.json` |
| Forge objects | `.mvar` file → Assembly → variant data | `data/forge_objects.json` |
| Physics constants | `forge_halo.map` → HREK Standalone → biped tag | `data/reach_physics.json` (verified values) |

## VM Requirements

- **Software**: UTM 4.7+ (free, open source)
- **OS**: Windows 11 ARM64
- **RAM**: 8-16 GB allocated
- **Storage**: 80 GB minimum (MCC is ~50 GB)
- **GPU**: Para-Virtualized Graphics (Apple Virtualization.framework)
- **Network**: Shared network (VM gets LAN IP accessible from macOS)
- **Steam**: MCC installed at `C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\`
- **HREK**: Installed via Steam Workshop (MCC → Mods)
- **Assembly**: Download from github.com/XboxChaos/Assembly
- **OpenSSH Server**: Enabled and configured for key-based auth
- **Blender**: Installed on macOS (runs natively, not in VM)

## Performance Notes (M4 Max, 128GB)

- Windows ARM x86 emulation overhead: ~15-20% on M4
- HREK Standalone: lightweight, runs fine under emulation
- Assembly: pure .NET/WPF, runs perfectly under emulation
- Blender: runs NATIVELY on macOS (no VM needed)
- Paravirtualized GPU: sufficient for HREK's 3D preview
- Total extraction time: ~2-4 hours (mostly Blender processing)