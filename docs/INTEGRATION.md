# Open-Source Integration Catalogue

Projects that accelerate moncler-grid-engine toward the Infection-Hemorrhage NorthStar.
Categorized by integration priority and impact.

---

## 🔴 TIER 1 — Direct Integration (Replace proprietary tools)

### Foundry — Blender Addon for Halo Reach/4/H2A
| | |
|---|---|
| **Repo** | [ILoveAGoodCrisp/Foundry](https://github.com/ILoveAGoodCrisp/Foundry) |
| **Stars** | 58 ★ |
| **License** | GPL-3.0 ✅ (compatible) |
| **Language** | C# (desktop app) + Python (Blender addon) |
| **Updated** | June 2026 — actively maintained |
| **What it does** | Import Halo Reach tags → Blender → export .glb. Full Blender addon with panels for materials, assets, lights, scenes, animations, cinematics. |
| **Replaces** | Halo Asset Blender Dev Toolset (proprietary, hard to find) |
| **How we use it** | Clone into `tools/foundry/`. Install Blender addon (`io_scene_foundry`). Import BSP tags, collision tags, render models. Export as .glb for Godot. |
| **Integration** | Drop-in replacement. No code changes needed. |

### Halo CR4B Tool — One-Click Game-Accurate Blender Import
| | |
|---|---|
| **Repo** | [PlasteredCrab/Halo-CR4B-Tool](https://github.com/PlasteredCrab/Halo-CR4B-Tool) |
| **Stars** | 30 ★ |
| **License** | None specified ⚠️ (verify before integration) |
| **Language** | Python (Blender addon) |
| **What it does** | Directly reads raw Halo tag files in binary. Pulls correct values, colors, scaling info. Sets up shader nodes for game-accurate materials. Supports H3/ODST now, Reach coming. |
| **How we use it** | Install alongside Foundry in Blender. Use for shader-accurate material setup. |
| **Integration** | Complementary to Foundry — handles the shader/material side. |

### ReachVariantEditor — .mvar File Parser
| | |
|---|---|
| **Repo** | [DavidJCobb/ReachVariantEditor](https://github.com/DavidJCobb/ReachVariantEditor) |
| **Stars** | 33 ★, 10 forks |
| **License** | GPL-3.0 ✅ (compatible) |
| **Language** | C++ (Qt5) |
| **What it does** | Reads AND edits Halo Reach game variants (.mvar files). Knows the binary format intimately. Also on NexusMods. |
| **How we use it** | Study the .mvar binary format parsing code. Build a JSON exporter that extracts Forge object coordinates from Infection variant .mvar files. |
| **Integration** | Reference implementation. We build a Python script that uses its format knowledge to extract Forge placements. |

---

## 🟡 TIER 2 — Study & Adapt (Architecture reference)

### HaloGD — Halo CE Multiplayer in Godot
| | |
|---|---|
| **Repo** | [BiggieCheese600/HaloGD](https://github.com/BiggieCheese600/HaloGD) |
| **Stars** | 0 ★ (new) |
| **License** | None specified |
| **Language** | GDScript |
| **What it does** | Open source Halo CE multiplayer recreation in Godot. RPC-based networking, weapon system, health/damage, animations. |
| **How we use it** | Study their approach to Halo physics in Godot, multiplayer RPC patterns, weapon implementation. Our C# controller is already more advanced, but this provides a GDScript comparison point. |
| **Integration** | Read-only reference. Don't fork — just learn from it. |

### Godot Multiplayer Lobby System
| | |
|---|---|
| **Repo** | [tngklp/godot-multiplayer-lobby-system](https://github.com/tngklp/godot-multiplayer-lobby-system) |
| **Stars** | 0 ★ (new) |
| **Language** | GDScript |
| **What it does** | Ready-to-use, server-authoritative multiplayer lobby for Godot 4.6 with ENet. |
| **How we use it** | Fork when we add online multiplayer. Provides lobby, matchmaking, host migration patterns. |
| **Integration** | Future — after local split-screen is solid. |

### ChimpsAtSea/Reach — Engine Decompilation
| | |
|---|---|
| **Repo** | [ChimpsAtSea/Reach](https://github.com/ChimpsAtSea/Reach) |
| **Stars** | 24 ★ |
| **License** | GPL-3.0 ✅ |
| **Language** | C++ |
| **What it does** | Reverse engineering of Halo Reach Blam engine. Function signatures, struct layouts, game logic flow. |
| **How we use it** | Already cloned at `/tmp/Reach-Decomp`. Reference for physics constants, weapon behavior, game mode logic. |
| **Integration** | Reference only. Used to verify our physics constants against actual engine code. |

---

## 🟢 TIER 3 — Ecosystem (Supporting infrastructure)

### GodotSteam
| | |
|---|---|
| **Repo** | [GodotSteam/GodotSteam](https://github.com/GodotSteam/GodotSteam) |
| **What it does** | Steamworks SDK integration for Godot 4 (GDExtension). Lobbies, networking, achievements, workshop. |
| **How we use it** | If we ever ship on Steam, this handles multiplayer matchmaking. |
| **Integration** | Future — requires Steamworks partner account. |

### XboxChaos/Assembly
| | |
|---|---|
| **Repo** | [XboxChaos/Assembly](https://github.com/XboxChaos/Assembly) |
| **Stars** | 261 ★ |
| **License** | MIT ✅ |
| **Language** | C# |
| **What it does** | Halo cache file (.map) tag browser/editor. Real-time poking, tag export, bitmap rendering. |
| **How we use it** | Primary tool on Windows VM for inspecting tags, exporting bitmaps, reading scenario data. |
| **Integration** | Already part of extraction pipeline (`tools/extraction/`). |

---

## 📋 Integration Priority Order

```
1. Foundry          ← Install NOW. Test BSP import from forge_halo.map → .glb
2. CR4B Tool        ← Install alongside Foundry. Handle shader/material setup.
3. ReachVariantEditor ← Study .mvar format. Build JSON exporter.
4. HaloGD           ← Study movement/physics approach. Compare to our C# controller.
5. Lobby System     ← Fork when online multiplayer phase begins.
6. GodotSteam       ← Integrate when shipping on Steam.
```

## 🔄 How These Replace the Original SPEC Pipeline

| Original SPEC | Replaced By | Improvement |
|--------------|-------------|-------------|
| Halo Asset Blender Dev Toolset | **Foundry** + **CR4B Tool** | Open source, actively maintained, GPL-compatible |
| Assembly for .mvar parsing | **ReachVariantEditor** | Actually knows the .mvar format, can extract coordinates |
| Manual physics constant guessing | **ChimpsAtSea/Reach** | Decompilation provides ground truth |
| Custom multiplayer from scratch | **HaloGD** (reference) + **Lobby System** | Battle-tested patterns |

## ⚠️ License Compatibility

Our project is **GPL-3.0**. License status of integration targets:
- ✅ GPL-3.0: Foundry, ReachVariantEditor, ChimpsAtSea/Reach
- ✅ MIT: Assembly
- ⚠️ None specified: CR4B Tool, HaloGD, Lobby System — verify before integrating code
- ✅ GPL-3.0 compatible: GodotSteam (MIT-style)