# 🔫 Hemorrhage Infection Engine

**Exact-replication game engine for classic multiplayer experiences. Godot 4 + macOS + DualShock 4.**

> "Not 'feels like Halo.' IS Halo." — See [Appendix B: Physics Verification Protocol](SPEC.md#appendix-b-physics-constant-verification-protocol)

## What This Is

A **game recreation engine** that rebuilds classic multiplayer games in Godot 4 with pixel-perfect physics, 4-player split-screen, and native DualShock 4 support on macOS.

**Flagship Project:** Halo Reach — Hemorrhage Infection

This repo is designed to be the foundation for multiple game recreations. Each game is a self-contained set of scenes, scripts, and data files within the same engine framework.

## Project Status — Phase 2: Engine Build

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1: Extraction** | 🟡 Pending Windows | Extract geometry, textures, collisions, spawn data from `forge_halo.map` |
| **Phase 2: Engine Build** | 🟢 In Progress | Godot project, all scripts, physics, split-screen |
| **Phase 3: Player Controller** | 🟢 Scripted | C# PlayerController with Reach physics |
| **Phase 4: Infection Mode** | 🟢 Scripted | Full state machine, alpha zombie, last man standing |
| **Phase 5: Split-Screen** | 🟢 Scripted | 4-player SubViewport, dynamic layouts |
| **Phase 6: Forge Objects** | 🟡 Needs .mvar data | Forge piece placement from variant coordinates |
| **Phase 7: Visual Polish** | 🔴 Not started | Lighting, skybox, fog, materials |
| **Phase 8: Weapons/Combat** | 🟢 Scripted | Hitscan, melee, reload, weapon data |

## Architecture

```
┌─────────────────────────────────────────────┐
│  Extraction (Windows, one-time)               │
│  MCC → HREK → Blender → .glb assets + JSON  │
└────────────────┬────────────────────────────┘
                 │ .glb / JSON data
┌────────────────▼────────────────────────────┐
│  Engine (macOS, Godot 4.7)                    │
│  ├── PlayerController (C#, Reach physics)    │
│  ├── InfectionFSM (GDScript, state machine)  │
│  ├── SplitScreenManager (4× SubViewport)     │
│  ├── InputManager (DualShock 4 routing)      │
│  ├── ForgeObjectPlacer (MultiMeshInstance3D) │
│  └── WeaponController (C#, hitscan + melee)  │
└──────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- macOS 11+ (Apple Silicon or Intel)
- [Godot 4.7+](https://godotengine.org/) (standard edition)
- 1-4 DualShock 4 controllers

### Open the project
```bash
git clone https://github.com/babyLegionite/Hemorrhage-Infection-Engine.git
cd Hemorrhage-Infection-Engine
godot project.godot
```

### Run the game
Press **F5** in Godot editor, or:
```bash
godot --path . --editor
```

## Controls (DualShock 4)

| Input | Button |
|-------|--------|
| Move | Left Stick |
| Look | Right Stick |
| Jump | ✕ (Cross / A) |
| Crouch | ○ (Circle / B) |
| Sprint | □ (Square / X) |
| Reload | △ (Triangle / Y) |
| Fire | R2 (Trigger Right) |
| ADS | L2 (Trigger Left) |
| Grenade | L1 (Left Bumper) |
| Melee | R3 (Click Right Stick) |
| Pause | Options |

## File Structure

```
├── project.godot          # Engine config + input map
├── data/
│   ├── reach_physics.json # Exact Blam-engine constants
│   ├── spawn_coordinates.json
│   ├── forge_objects.json
│   └── weapon_data.json
├── scripts/
│   ├── cs/                # C# performance scripts
│   │   ├── PlayerController.cs
│   │   ├── CameraFollow.cs
│   │   └── WeaponController.cs
│   └── gd/                # GDScript game logic
│       ├── InfectionFSM.gd
│       ├── SplitScreenManager.gd
│       ├── InputManager.gd
│       ├── ForgeObjectPlacer.gd
│       ├── TeamManager.gd
│       ├── ScoreManager.gd
│       ├── InfectionHUD.gd
│       └── SpawnPointManager.gd
├── scenes/
│   ├── HemorrhageInfection.tscn
│   ├── Player.tscn
│   └── InfectionHUD.tscn
├── assets/
│   ├── maps/              # .glb terrain from extraction
│   ├── forge_pieces/      # .glb Forge objects
│   ├── characters/        # Spartan models
│   └── weapons/           # Weapon models
└── SPEC.md                # Full technical specification
```

## Physics — Exact Reach Replication

Physics constants are loaded from `data/reach_physics.json` at runtime. The constants will be verified against:

1. **[ChimpsAtSea/Reach](https://github.com/ChimpsAtSea/Reach)** — Community decompilation (C++, GPL-3.0)
2. **HREK Standalone** — Live inspector for biped tag physics values
3. **[c20.reclaimers.net](https://c20.reclaimers.net/hr/tags/biped)** — Community tag documentation

See [SPEC.md §2.2](SPEC.md#22-reference--data-sources) for the full extraction pipeline.

## Tool Stack

| Tool | Purpose | Platform |
|------|---------|----------|
| **Godot 4.7** | Game engine, renderer, physics | macOS |
| **HREK** | Official 343 modding suite | Windows |
| **Assembly** | Cache file tag browser/editor | Windows |
| **Blender** | Intermediate asset processing | macOS/Windows |
| **ChimpsAtSea/Reach** | Community decomp (physics reference) | Any |

## Future Games

This engine is designed to host multiple game recreations beyond Halo Reach. Planned additions:

- 🎯 **Halo 3 — Guardian / The Pit** (exact BSP + MLG variants)
- 🚗 **Mario Kart 64 — Block Fort** (4-player battle mode)
- 🔫 **GoldenEye 007 — Facility** (4-player split-screen)
- 🧟 **Left 4 Dead — No Mercy** (co-op vs infected)

Each game adds its own `data/`, `assets/`, `scripts/`, and `scenes/` directories while sharing the core engine framework.

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

## Credits

- **Dane Porter** (@babyLegionite) — Project creator
- **ChimpsAtSea** — [Reach decompilation project](https://github.com/ChimpsAtSea/Reach)
- **The Reclaimers (c20)** — [Community knowledge base](https://c20.reclaimers.net)
- **343 Industries / Bungie** — Original Halo Reach
- **Godot Foundation** — Godot Engine