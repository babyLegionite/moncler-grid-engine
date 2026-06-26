# Technical Specification: Hemorrhage Infection Engine
## Halo Reach → Godot 4 — Identical Physics, 4-Player Local, PS4 Controllers, macOS

**Version:** 1.0  
**Target Map:** Hemorrhage (Forge World variant)  
**Target Game Mode:** Infection  
**Players:** 4 local split-screen  
**Engine:** Godot 4.3+ (.NET edition recommended)  
**Host OS:** macOS (Apple Silicon + Intel)  
**Extraction OS:** Windows 10/11 (VM or native)  

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE 1 — EXTRACTION (Windows, one-time)                      │
│                                                               │
│  MCC Steam Install                                            │
│    ├─ forge_halo.map  → HREK tools → tag extraction           │
│    ├─ .mvar files     → File Share Archive → coordinate data  │
│    └─ Reach decomp   → physics constants → reference sheet    │
│                                                               │
│  tag data → Blender (Halo Asset Blender Dev Toolset) → .glb  │
└────────────────────────────┬──────────────────────────────────┘
                            │
                    .glb / .gltf assets
                    physics_constants.json
                    spawn_coordinates.json
                            │
┌────────────────────────────▼──────────────────────────────────┐
│  PHASE 2 — ENGINE BUILD (macOS, ongoing)                       │
│                                                               │
│  Godot 4.3+                                                   │
│    ├─ Map scene (Hemorrhage geometry + collision + navmesh)  │
│    ├─ Player controller (CharacterBody3D, exact Reach physics)│
│    ├─ Infection game mode (state machine, round logic)        │
│    ├─ Split-screen manager (4× SubViewport)                  │
│    ├─ Input manager (DualShock 4 native mapping)             │
│    └─ Asset streaming (Shader-based LOD, occlusion culling)  │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Open-Source Tool Stack — Real References

### 2.1 Extraction Tools (Windows)

| Tool | Repo / Source | Purpose | Status |
|------|--------------|---------|--------|
| **Halo Reach Editing Kit (HREK)** | Steam Workshop (MCC → Mods → HREK) | Official 343 modding suite. Extracts tags, compiles maps, runs Standalone (runtime preview). | ✅ Official, supported |
| **Assembly** | `github.com/XboxChaos/Assembly` (261 stars, 99 forks) | Cache file tag browser/editor. Opens `.map` files directly, exposes every tag in the Blam engine. Real-time poking. | ✅ Mature, actively used |
| **TagTool** | Community tool (referenced on c20.reclaimers.net) | Tag porting between Blam engine versions. Importing new content. | ✅ Community-confirmed |
| **Halo Asset Blender Development Toolset** | Available via HREK / c20 wiki | Blender add-on. Imports/exports Reach model tags, handles UV coordinates, scale, armatures. The bridge between tag data and standard 3D formats. | ✅ Official-adjacent |

### 2.2 Reference & Data Sources

| Source | URL / Location | What It Gives You |
|--------|---------------|-------------------|
| **Reclaimers Library (c20)** | `c20.reclaimers.net` | Complete tag documentation for every Halo Reach tag type. Engine internals. Modding workflows. The community knowledge base. |
| **Reach Decompilation** | Community reverse-engineering project (verify current repo at `c20.reclaimers.net/hr/engine` or Discord) | Code-level analysis of Blam engine: gravity, acceleration, jump curves, weapon behavior, movement constants. |
| **Ultimate Halo File Share Archive** | Public spreadsheet (linked from r/halo, r/forge) | `.mvar` files for community Forge maps. Contains exact Forge object placement coordinates for Infection variants. |
| **Assembly Wiki** | `github.com/XboxChaos/Assembly/wiki` | Compile instructions, contribution guidelines. Sparse but functional. |

### 2.3 Engine & Development

| Tool | Version | Purpose |
|------|---------|---------|
| **Godot Engine** | 4.3+ (.NET edition) | Game engine, renderer, physics, input, scripting |
| **Blender** | 4.2+ | Intermediate asset processing, mesh cleanup, UV repair |
| **GDScript / C#** | Godot built-in | Game logic, player controller, game mode |
| **Reclaimer** | c20 Discord | Community Q&A, tool support, tribal knowledge |

---

## 3. Smart Strategic Shortcuts — Save Dev Time

### S1: Use HREK Standalone as a Real-Time Inspector

Don't guess at physics values. Boot HREK's **Standalone** tool, load `forge_halo.map`, and use the console to query exact values in real time:

```
; In Standalone console (` key):
halo(game_start levels\forge_world\forge_world)
; Then inspect player physics tags:
; Navigate to bip\cyborg\biped tag in Assembly
; Read: gravity_scale, walk_speed, run_speed, jump_height
```

**Why this matters:** You copy exact float values, not approximations. The Reclaimers wiki confirms Standalone can load any Reach map and run it in a preview window.

### S2: Extract Collision Geometry Separately from Visual Geometry

The Blam engine stores collision in `collision_model` tags, NOT in `render_model` tags. These are separate data.

**Strategic move:**
1. Extract `render_model` tags → visual mesh (no collision, high-detail)
2. Extract `collision_model` tags → collision mesh (low-detail, exact boundaries)
3. In Godot: visual mesh = `MeshInstance3D`, collision mesh = `ConcavePolygonShape3D` on a `StaticBody3D`

This gives you exact player boundaries — the same walls players can't pass through in original Reach.

### S3: Use Godot's Built-in NavMesh Baker for Zombie AI

Don't hand-place navmeshes. Godot 4 has a `NavigationServer3D` with automatic baking.

```
1. Import map collision mesh as TrimeshBody
2. Add NavigationRegion3D node as child of map root
3. Call NavigationServer3D.bake_navigation_mesh()
4. Zombies now pathfind across the exact same terrain players walk on
```

Hemorrhage is open terrain with some structures — Godot's baker handles this well.

### S4: Forge Objects from .mvar = JSON Coordinate Injection

The `.mvar` files from the File Share Archive contain Forge object placements as data: object ID, position (x,y,z), rotation (pitch,yaw,roll), scale.

**Strategic move:**
1. Parse `.mvar` → JSON (community tools exist for this)
2. In Godot, build a `ForgeObjectPlacer.gd` script that reads JSON and instantiates pre-built scenes at exact coordinates
3. You now have the EXACT same map layout as the original Infection variant — same walls, same spawn points, same barricades

This is faster and more accurate than manually placing objects in the Godot editor.

### S5: Instanced Rendering for Repeated Forge Objects

Hemorrhage uses many copies of the same Forge pieces (walls, blocks, ramps). Godot 4's `MultiMeshInstance3D` renders thousands of identical meshes in a single draw call.

**Strategic move:**
- Identify the ~20-30 unique Forge piece types used in the target Infection variant
- Create one `.glb` per type
- Use `MultiMeshInstance3D` for all instances
- Performance: 4 split-screen viewports × same scene = one render pass with 4 camera matrices

### S6: Physics Constants as a Data File, Not Hardcoded

Don't bury physics values in script. Create `reach_physics.json`:

```json
{
  "gravity": -12.0,
  "player_walk_speed": 2.0,
  "player_run_speed": 4.0,
  "player_crouch_speed": 1.2,
  "jump_height": 1.2,
  "jump_initial_velocity": 5.2,
  "ground_acceleration": 8.0,
  "ground_deceleration": 16.0,
  "air_acceleration": 1.5,
  "air_deceleration": 1.5,
  "max_air_control": 0.35,
  "terminal_velocity": -30.0,
  "slope_angle_limit": 60.0,
  "step_height": 0.35
}
```

Load this at runtime. When you discover a value is wrong, you fix the JSON — no recompiling. The Reach decompilation project gives you the real numbers.

### S7: Split-Screen via SubViewport — Not Multiple Windows

Godot 4's `SubViewport` node renders a scene from a camera into a viewport texture. For 4 players:

```
SplitScreenContainer (Control)
├── HBoxContainer
│   ├── Player1Viewport (SubViewport + Camera3D)
│   ├── Player2Viewport (SubViewport + Camera3D)
│   ├── Player3Viewport (SubViewport + Camera3D)
│   └── Player4Viewport (SubViewport + Camera3D)
```

All 4 viewports share the **same SceneTree** — same world, same physics, same players. Only the cameras differ. This is how Reach did split-screen and how Godot 4 does it.

**Performance optimization:** Use `SubViewportContainer` with `stretch_mode = viewport`. Set render resolution per viewport to 960×540 (quarter of 1080p) — this is what Reach ran at on Xbox 360 for 4-player split.

### S8: Use Godot's .NET Edition for Physics-Heavy Code

GDScript is fast for game logic. C# (via .NET edition) is faster for:
- Player physics math (vector math, collision response)
- NavMesh pathfinding queries (4 zombies querying paths simultaneously)
- Input polling (4 controllers at 60+ FPS)

**Strategic move:** Write the player controller and input manager in C#. Write the Infection game mode logic and UI in GDScript.

---

## 4. Extraction Pipeline — Phase by Phase

### Phase A: Acquire Source Files

**Prerequisites:**
- Windows 10/11 machine or VM (Parallels/UTM on Mac works)
- Halo: The Master Chief Collection purchased on Steam
- HREK installed (Steam Workshop → MCC → Mods → Halo Reach Editing Kit)

**File locations (MCC Steam install):**
```
Steam/steamapps/common/Halo The Master Chief Collection/
└── haloreach/
    └── maps/
        ├── forge_halo.map        ← This is Forge World (Hemorrhage base)
        ├── cex_bloodgulch.map
        ├── ... (other MP maps)
```

`forge_halo.map` is the file you want. Forge World IS Hemorrhage — it's the same map geometry with Forge-enabled object placement.

### Phase B: Extract Geometry via HREK + Blender

**Step 1:** Open HREK's **Standalone** tool. Load `forge_halo.map`.

**Step 2:** Use HREK's tag extraction to export the `scenario_structure_bsp` tag (this is the map's BSP — the actual canyon geometry of Forge World / Hemorrhage).

**Step 3:** Open Blender with the Halo Asset Blender Development Toolset installed. Import the extracted BSP tag data. The toolset handles:
- Mesh geometry (vertices, faces, UVs)
- Material assignments
- Texture binding
- Scale conversion (Blam uses different unit scale → Blender meters)

**Step 4:** In Blender, export as `.glb` (glTF 2.0 Binary). Godot 4 imports `.glb` natively with:
- Full mesh data preserved
- Materials → StandardMaterial3D
- UV maps intact
- Node hierarchy maintained

**Step 5:** Repeat for collision geometry. Extract `collision_model` tags for the same BSP. Export as a separate `.glb` — this becomes your collision mesh in Godot.

### Phase C: Extract Textures

**Step 1:** In Assembly, open `forge_halo.map`.

**Step 2:** Navigate to `bitmap` tags. Filter for terrain textures, skybox textures, object textures.

**Step 3:** Export bitmap tags as `.dds` or `.png`. Assembly can render bitmap tag data to image files.

**Step 4:** Convert `.dds` to `.png` or `.webp` (Godot supports both, but `.webp` is smaller and faster on macOS).

**Step 5:** In Blender, re-bind textures to the imported mesh's UV maps. Export with textures embedded in the `.glb`.

### Phase D: Extract Spawn Points & Forge Object Coordinates

**Step 1:** Open `forge_halo.map` in Assembly. Navigate to the `scenario` tag.

**Step 2:** The `scenario` tag contains:
- `player_starting_locations` — exact (x,y,z) spawn points
- `item placements` — weapon/equipment spawn coordinates
- `trigger volumes` — zone definitions
- `objective markers` — flag/bomb zones

**Step 3:** Export spawn point data as JSON:
```json
{
  "spawns": [
    {"id": 0, "pos": [12.5, -3.2, 45.0], "team": "infected", "rotation": 180},
    {"id": 1, "pos": [-8.0, 2.1, 30.0], "team": "human", "rotation": 90}
  ]
}
```

**Step 4:** For the specific Infection variant map, obtain the `.mvar` file from the Ultimate Halo File Share Archive. Parse it (community tools or manual hex reading — Assembly can read these too).

**Step 5:** Export Forge object placements as JSON:
```json
{
  "forge_objects": [
    {"type": "wall_straight", "pos": [45.2, 0.0, -12.0], "rot": [0, 90, 0], "scale": 1.0},
    {"type": "ramp", "pos": [22.0, 3.5, 8.0], "rot": [15, 0, 0], "scale": 1.5}
  ]
}
```

### Phase E: Extract Physics Constants

**Step 1:** Reference the Reach decompilation project (verify current location via `c20.reclaimers.net/hr/engine` or the Reclaimers Discord).

**Step 2:** The decompilation documents the Blam engine's `biped` movement system:
- Gravity value (applied per tick)
- Ground acceleration / deceleration curves
- Air control coefficient
- Jump initial velocity and gravity applied during jump
- Crouch speed modifier
- Sprint speed and acceleration (Reach has sprint in some modes)

**Step 3:** Use HREK Standalone as a live inspector. Load the map, open console, query the biped tag directly:
```
; In Standalone console:
; Inspect player biped physics constants
; These values are in the bip\cyborg tag
```

**Step 4:** Document all constants in `reach_physics.json` (see S6 above).

---

## 5. Godot 4 Engine Architecture

### 5.1 Scene Tree

```
HemorrhageInfection (Node3D — root scene)
│
├── MapRoot (Node3D)
│   ├── TerrainMesh (MeshInstance3D)
│   │   └── Material: StandardMaterial3D (terrain textures from .glb)
│   ├── CollisionBody (StaticBody3D)
│   │   └── Shape: ConcavePolygonShape3D (from collision_model extraction)
│   ├── Skybox (WorldEnvironment)
│   │   ├── Environment: SkyMaterial (recreate Reach sky gradient)
│   │   └── Fog: FogMaterial (Reach uses atmospheric fog heavily)
│   ├── DetailObjects (MultiMeshInstance3D)
│   │   └── Rocks, grass decals, scattered terrain detail
│   └── NavigationRegion3D
│       └── Navmesh (auto-baked from collision mesh)
│
├── ForgeObjects (Node3D)
│   ├── Walls (MultiMeshInstance3D — all wall instances from .mvar JSON)
│   ├── Ramps (MultiMeshInstance3D)
│   ├── Blocks (MultiMeshInstance3D)
│   ├── barricades (MultiMeshInstance3D)
│   └── ... (each unique Forge piece type)
│
├── SpawnPointManager (Node3D)
│   └── 20× Marker3D nodes (placed via spawn_coordinates.json)
│
├── Players (Node3D)
│   ├── Player1 (CharacterBody3D)
│   │   ├── MeshInstance3D (Spartan model)
│   │   ├── Camera3D
│   │   ├── InputController (C# script — handles DualShock 4)
│   │   ├── MovementController (C# script — exact Reach physics)
│   │   └── WeaponController (C# script — weapon logic)
│   ├── Player2 (CharacterBody3D) — identical structure
│   ├── Player3 (CharacterBody3D) — identical structure
│   └── Player4 (CharacterBody3D) — identical structure
│
├── GameModeManager (Node — Infection state machine)
│   ├── InfectionFSM.gd (GDScript — round logic, alpha zombie, last man standing)
│   ├── TeamManager.gd (GDScript — team assignment, player tracking)
│   └── ScoreManager.gd (GDScript — kills, rounds won, HUD data)
│
├── SplitScreenManager (Control)
│   ├── ViewportContainer (SubViewportContainer)
│   │   ├── Player1Viewport (SubViewport)
│   │   │   └── Camera3D (references Player1's camera)
│   │   ├── Player2Viewport (SubViewport)
│   │   ├── Player3Viewport (SubViewport)
│   │   └── Player4Viewport (SubViewport)
│   └── HUDManager (CanvasLayer)
│       ├── Player1HUD (InfectionHUD.tscn instance)
│       ├── Player2HUD
│       ├── Player3HUD
│       └── Player4HUD
│
├── InputManager (Node — autoload singleton)
│   └── ControllerRouter.gd (maps DualShock 4 → Godot actions)
│
└── AssetLoader (Node — autoload singleton)
    └── Streamer.gd (handles streaming LOD, asset loading)
```

### 5.2 Player Controller — Exact Reach Physics

The core of "identical" is the movement feel. Here's the C# script structure:

```csharp
// PlayerController.cs — Godot 4 .NET
using Godot;
using System;

public partial class PlayerController : CharacterBody3D
{
    // Physics constants loaded from reach_physics.json at runtime
    private float _gravity;
    private float _walkSpeed;
    private float _runSpeed;
    private float _crouchSpeed;
    private float _jumpVelocity;
    private float _groundAccel;
    private float _groundDecel;
    private float _airAccel;
    private float _airDecel;
    private float _maxAirControl;
    private float _terminalVelocity;
    private float _stepHeight;

    // State
    private bool _isCrouching = false;
    private bool _isSprinting = false;
    private bool _isGrounded = false;
    private Vector3 _velocity = Vector3.Zero;
    private Vector3 _inputDirection = Vector3.Zero;
    private float _lookYaw = 0f;
    private float _lookPitch = 0f;

    public override void _Ready()
    {
        LoadPhysicsConstants();
    }

    private void LoadPhysicsConstants()
    {
        // Load from reach_physics.json
        var file = FileAccess.Open("res://data/reach_physics.json", FileAccess.ModeFlags.Read);
        var json = Json.ParseString(file.GetAsText());
        _gravity = (float)json["gravity"];
        _walkSpeed = (float)json["player_walk_speed"];
        _runSpeed = (float)json["player_run_speed"];
        _crouchSpeed = (float)json["player_crouch_speed"];
        _jumpVelocity = (float)json["jump_initial_velocity"];
        _groundAccel = (float)json["ground_acceleration"];
        _groundDecel = (float)json["ground_deceleration"];
        _airAccel = (float)json["air_acceleration"];
        _airDecel = (float)json["air_deceleration"];
        _maxAirControl = (float)json["max_air_control"];
        _terminalVelocity = (float)json["terminal_velocity"];
        _stepHeight = (float)json["step_height"];
    }

    public override void _PhysicsProcess(double delta)
    {
        var dt = (float)delta;

        // Read input (from DualShock 4 via InputManager)
        _inputDirection = GetInputDirection();
        _isCrouching = Input.IsActionPressed("crouch");
        _isSprinting = Input.IsActionPressed("sprint");

        // Apply gravity (Blam engine applies gravity per tick, not per frame)
        if (!_isGrounded)
        {
            _velocity.Y += _gravity * dt;
            // Terminal velocity cap (Reach has this)
            _velocity.Y = Mathf.Max(_velocity.Y, _terminalVelocity);
        }

        // Movement speed selection
        float currentSpeed = _walkSpeed;
        if (_isCrouching) currentSpeed = _crouchSpeed;
        else if (_isSprinting) currentSpeed = _runSpeed;

        // Ground vs Air movement (these curves are what make Reach "feel" like Reach)
        Vector3 horizontalInput = _inputDirection * currentSpeed;

        if (_isGrounded)
        {
            // Ground: fast acceleration, fast deceleration
            // Reach's ground feel is snappy — high accel, high decel
            _velocity.X = MoveToward(_velocity.X, horizontalInput.X, _groundAccel * dt);
            _velocity.Z = MoveToward(_velocity.Z, horizontalInput.Z, _groundAccel * dt);
        }
        else
        {
            // Air: low acceleration, low deceleration
            // Reach's air control is limited — you can't redirect mid-jump easily
            _velocity.X = MoveToward(_velocity.X, horizontalInput.X * _maxAirControl, _airAccel * dt);
            _velocity.Z = MoveToward(_velocity.Z, horizontalInput.Z * _maxAirControl, _airAccel * dt);
        }

        // Jump
        if (_isGrounded && Input.IsActionJustPressed("jump"))
        {
            _velocity.Y = _jumpVelocity;
            _isGrounded = false;
        }

        // Apply movement
        Velocity = _velocity;
        MoveAndSlide();

        // Update grounded state
        _isGrounded = IsOnFloor();

        // Look (camera rotation from right stick)
        _lookYaw -= Input.GetActionRawStrength("look_right") * dt * 2.0f;
        _lookPitch -= Input.GetActionRawStrength("look_up") * dt * 2.0f;
        _lookPitch = Mathf.Clamp(_lookPitch, -1.5f, 1.5f);

        // Apply to camera and body
        Rotation = new Vector3(0, _lookYaw, 0);
        var camera = GetNode<Camera3D>("Camera3D");
        camera.Rotation = new Vector3(_lookPitch, 0, 0);
    }

    private Vector3 GetInputDirection()
    {
        // Left stick → world-space movement direction
        var input = Input.GetVector(
            "move_left", "move_right",
            "move_forward", "move_back"
        );
        var dir = (Transform.Basis * new Vector3(input.X, 0, -input.Y)).Normalized();
        return dir;
    }

    private float MoveToward(float current, float target, float maxDelta)
    {
        if (Mathf.Abs(current - target) <= maxDelta)
            return target;
        return current + Mathf.Sign(target - current) * maxDelta;
    }
}
```

**Critical note on physics values:** The constants above are PLACEHOLDERS. The real values must come from:
1. The Reach decompilation project (verify current repo via Reclaimers Discord)
2. HREK Standalone live inspection of the `bip\cyborg` tag
3. Cross-referenced with community knowledge on c20.reclaimers.net

### 5.3 Infection Game Mode — State Machine

Infection in Halo Reach works as follows:
1. **Pre-round:** All players are human. One player is selected as Alpha Zombie (first infected).
2. **Round start:** Alpha zombie spawns. All humans spawn at human spawn points.
3. **During round:** Alpha zombie kills humans → humans become zombies (join infected team).
4. **Last Man Standing:** When 1 human remains, they get a speed/damage bonus and the HUD announces "Last Man Standing."
5. **Round end:** Either all humans are infected (zombies win) or timer expires (humans win).
6. **Next round:** New alpha zombie selected. Repeat for N rounds (default 3).

```gdscript
# InfectionFSM.gd — Infection game mode state machine
extends Node
class_name InfectionFSM

enum State { PRE_ROUND, ACTIVE, LAST_MAN_STANDING, ROUND_END, MATCH_END }

var current_state: State = State.PRE_ROUND
var players: Array = []
var humans: Array = []
var infected: Array = []
var alpha_zombie: Player = null
var last_man: Player = null
var round_number: int = 0
var max_rounds: int = 3
var round_timer: float = 180.0  # 3 minutes default
var state_timer: float = 0.0

signal round_started(round_number: int)
signal player_infected(player: Player)
signal last_man_standing(player: Player)
signal round_end(winner: String, round_number: int)
signal match_end(winner: String)

func _ready():
    connect_players()

func _process(delta):
    match current_state:
        State.PRE_ROUND:
            _process_pre_round(delta)
        State.ACTIVE:
            _process_active(delta)
        State.LAST_MAN_STANDING:
            _process_last_man(delta)
        State.ROUND_END:
            _process_round_end(delta)
        State.MATCH_END:
            _process_match_end(delta)

func start_round():
    # Select alpha zombie (random from players, or lowest scorer)
    alpha_zombie = select_alpha_zombie()
    
    # Assign teams
    for p in players:
        if p == alpha_zombie:
            p.set_team("infected")
            infected.append(p)
        else:
            p.set_team("human")
            humans.append(p)
    
    # Spawn players at appropriate spawn points
    alpha_zombie.spawn_at("infected_spawn")
    for h in humans:
        h.spawn_at("human_spawn")
    
    # Reset timer
    round_timer = 180.0
    current_state = State.ACTIVE
    round_number += 1
    round_started.emit(round_number)

func _process_active(delta):
    round_timer -= delta
    
    # Check for human → infected conversions
    for h in humans:
        if h.is_dead() and h.killed_by_infected():
            _convert_to_infected(h)
    
    # Check win conditions
    if humans.size() == 1:
        last_man = humans[0]
        current_state = State.LAST_MAN_STANDING
        last_man_standing.emit(last_man)
        # Apply Last Man Standing bonus
        last_man.apply_bonus("speed", 1.5)
        last_man.apply_bonus("damage", 2.0)
    
    if humans.size() == 0:
        current_state = State.ROUND_END
        round_end.emit("infected", round_number)
    
    if round_timer <= 0:
        current_state = State.ROUND_END
        round_end.emit("humans", round_number)

func _process_last_man(delta):
    round_timer -= delta
    
    # Check if last man dies
    if last_man.is_dead():
        current_state = State.ROUND_END
        round_end.emit("infected", round_number)
    
    if round_timer <= 0:
        current_state = State.ROUND_END
        round_end.emit("humans", round_number)

func _convert_to_infected(player: Player):
    humans.erase(player)
    infected.append(player)
    player.set_team("infected")
    player.respawn_at("infected_spawn")
    player_infected.emit(player)

func _process_round_end(delta):
    state_timer += delta
    if state_timer >= 5.0:  # 5 second intermission
        state_timer = 0.0
        if round_number >= max_rounds:
            current_state = State.MATCH_END
        else:
            current_state = State.PRE_ROUND
            # Reset for next round
            humans.clear()
            infected.clear()
            for p in players:
                p.reset()

func _process_match_end(delta):
    # Tally wins
    var human_wins = 0
    var infected_wins = 0
    for r in round_history:
        if r.winner == "humans": human_wins += 1
        else: infected_wins += 1
    
    var winner = "humans" if human_wins > infected_wins else "infected"
    match_end.emit(winner)
    # Return to lobby / restart

func select_alpha_zombie() -> Player:
    # Reach selects the player with the lowest score, or random in first round
    if round_number == 0:
        return players[randi() % players.size()]
    else:
        return players.min_by(func(p): return p.score)

func connect_players():
    # Wire up to PlayerController death signals
    for p in players:
        p.died.connect(func(killer): _on_player_died(p, killer))
```

### 5.4 Split-Screen Implementation

```gdscript
# SplitScreenManager.gd
extends Control
class_name SplitScreenManager

@export var player_count: int = 4

var viewports: Array[SubViewport] = []
var cameras: Array[Camera3D] = []

func _ready():
    _setup_viewports()

func _setup_viewports():
    var container = SubViewportContainer.new()
    container.stretch = true
    container.layout_mode = 1  # anchors
    container.size = get_viewport().size
    
    # Layout: 2x2 grid for 4 players
    var grid = GridContainer.new()
    grid.columns = 2
    grid.set_anchors_preset(Control.PRESET_FULL_RECT)
    
    for i in range(player_count):
        var vp = SubViewport.new()
        vp.size = Vector2i(960, 540)  # Quarter 1080p (Reach ran at this)
        vp.render_target_update_mode = SubViewport.UpdateMode.ALWAYS
        
        var cam = Camera3D.new()
        vp.add_child(cam)
        
        # Link camera to player
        var player = get_tree().get_nodes_in_group("players")[i]
        cam.global_transform = player.get_node("Camera3D").global_transform
        
        # Make camera follow player
        var follow_script = CameraFollow.new()
        follow_script.target = player
        cam.add_child(follow_script)
        
        viewports.append(vp)
        cameras.append(cam)
        grid.add_child(vp)
    
    container.add_child(grid)
    add_child(container)
```

### 5.5 PS4 DualShock 4 Input Mapping

Godot 4 detects DualShock 4 controllers natively on macOS via the IOKit framework. No third-party drivers needed.

**Project Settings → Input Map:**

```
# Add these actions in project.godot [input] section:

[input]
move_forward = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 1 (Left Stick Y) with value -1.0] }
move_back    = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 1 (Left Stick Y) with value 1.0] }
move_left    = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 0 (Left Stick X) with value -1.0] }
move_right   = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 0 (Left Stick X) with value 1.0] }
look_left    = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 2 (Right Stick X) with value -1.0] }
look_right   = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 2 (Right Stick X) with value 1.0] }
look_up      = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 3 (Right Stick Y) with value -1.0] }
look_down    = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 3 (Right Stick Y) with value 1.0] }
jump         = { "deadzone": 0.5, "events": [JoypadButton Event on button 0 (Cross/A)] }
crouch       = { "deadzone": 0.5, "events": [JoypadButton Event on button 1 (Circle/B)] }
sprint       = { "deadzone": 0.5, "events": [JoypadButton Event on button 3 (Square/X — hold to sprint in Reach)] }
fire         = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 5 (R2/RT trigger) with value 1.0] }
ads          = { "deadzone": 0.5, "events": [JoypadMotion Event on axis 4 (L2/LT trigger) with value 1.0] }
reload       = { "deadzone": 0.5, "events": [JoypadButton Event on button 2 (Triangle/Y)] }
switch_weapon = { "deadzone": 0.5, "events": [JoypadButton Event on button 2 (Triangle/Y)] }
grenade       = { "deadzone": 0.5, "events": [JoypadButton Event on button 4 (L1/LB)] }
ability      = { "deadzone": 0.5, "events": [JoypadButton Event on button 5 (R1/RB)] }
melee        = { "deadzone": 0.5, "events": [JoypadButton Event on button 6 (R3 — click right stick)] }
```

**Multi-controller handling:**
```gdscript
# InputManager.gd — Autoload singleton
extends Node

var controller_map: Dictionary = {}  # device_id → player_index

func _ready():
    Input.joy_connection_changed.connect(_on_joy_connection)
    _detect_controllers()

func _detect_controllers():
    var connected = Input.get_connected_joypads()
    for i in range(connected.size()):
        var device_id = connected[i]
        var name = Input.get_joy_name(device_id)
        if "DualShock" in name or "PS4" in name or "Sony" in name:
            controller_map[device_id] = i  # Player 0-3
            print("Player %d: DualShock 4 on device %d" % [i, device_id])

func get_player_input(player_index: int) -> Dictionary:
    # Find the device_id for this player
    var device_id = -1
    for key in controller_map:
        if controller_map[key] == player_index:
            device_id = key
            break
    
    if device_id == -1:
        return {}  # No controller for this player
    
    # Read raw input from specific device
    return {
        "left_stick": Input.get_vector(
            "move_left", "move_right", "move_forward", "move_back", 0.5
        ),  # Note: need device-specific input — see below
        "right_stick": Vector2(
            Input.get_action_raw_strength("look_right") - Input.get_action_raw_strength("look_left"),
            Input.get_action_raw_strength("look_down") - Input.get_action_raw_strength("look_up")
        )
    }
```

**Critical Godot 4 note:** `Input.get_vector()` and `Input.is_action_pressed()` read from ALL devices by default. For split-screen, you need device-specific input. Use `InputEvent` processing in `_unhandled_input()` and filter by `event.device`:

```csharp
// In PlayerController.cs — device-specific input
public int DeviceId { get; set; } = 0;  // Set by InputManager

public override void _UnhandledInput(InputEvent @event)
{
    if (@event is InputEventJoypadMotion joyMotion && joyMotion.Device == DeviceId)
    {
        if (joyMotion.Axis == 0) _leftStickX = joyMotion.AxisValue;
        if (joyMotion.Axis == 1) _leftStickY = joyMotion.AxisValue;
        if (joyMotion.Axis == 2) _rightStickX = joyMotion.AxisValue;
        if (joyMotion.Axis == 3) _rightStickY = joyMotion.AxisValue;
        if (joyMotion.Axis == 4) _leftTrigger = joyMotion.AxisValue;
        if (joyMotion.Axis == 5) _rightTrigger = joyMotion.AxisValue;
    }
    else if (@event is InputEventJoypadButton joyButton && joyButton.Device == DeviceId)
    {
        if (joyButton.ButtonIndex == 0 && joyButton.Pressed) _jumpPressed = true;
        if (joyButton.ButtonIndex == 3 && joyButton.Pressed) _sprintHeld = true;
        // ... etc
    }
}
```

---

## 6. Rendering — Reaching Visual Parity

### 6.1 What Can Be 1:1

- **Geometry** — exact (from extracted BSP)
- **Textures** — exact (from extracted bitmap tags)
- **UV mapping** — exact (preserved through Blender → glTF → Godot)
- **Collision** — exact (from extracted collision_model tags)
- **Spawn points** — exact (from scenario tag)
- **Forge object placement** — exact (from .mvar data)

### 6.2 What Must Be Recreated

- **Skybox** — Reach uses a procedural sky with layered gradients, clouds, and atmospheric scattering. Recreate in Godot's `SkyMaterial` with custom gradient parameters. Reference HREK Standalone screenshots.
- **Fog** — Reach's fog is critical to the look. Godot's `FogMaterial` supports exponential fog. Match density and color to Reach screenshots.
- **Lighting** — Reach uses a precomputed lightmap + real-time directional light. Godot 4 supports `LightmapGI` (global illumination). Bake from the imported map geometry.
- **Shader approximation** — Reach's Blam shader pipeline is proprietary. Use Godot's `StandardMaterial3D` with:
  - Albedo = extracted texture
  - Normal map = if extracted (some bitmap tags contain normal data)
  - Roughness/metallic = approximate (match by eye using Reach screenshots)

### 6.3 LOD Strategy for 4 Viewports

```
Terrain LOD:
├── High LOD:  full mesh (LOD 0) — visible within 50m of any camera
├── Medium LOD: simplified mesh (LOD 1) — 50-200m
└── Low LOD:    imposters billboard (LOD 2) — 200m+

Use Godot's MeshInstance3D.lodBias and automatic LOD generation.
For 4 viewports, use the closest camera's distance for LOD selection.
```

### 6.4 Performance Budget (macOS)

| Setting | Value | Rationale |
|---------|-------|----------|
| Render resolution per viewport | 960×540 | Match Xbox 360 4-player split |
| FPS target | 60 | Reach ran at 30 on Xbox 360; 60 is our floor |
| Physics ticks | 60 Hz | Match Blam engine tick rate |
| Max draw calls per frame | ~2000 | Godot handles this well on M1+ |
| Max objects in scene | ~500 | Hemorrhage + Forge objects |
| Texture memory | ~512MB | Extracted Reach textures are moderate |

---

## 7. Known Gaps & Workarounds

### Gap 1: Assembly does not export 3D geometry directly

**Fact:** Assembly is a tag editor, not a model exporter.

**Workaround:** Use the **HREK + Halo Asset Blender Development Toolset** pipeline instead. The Blender toolset is designed to import Reach tag data into Blender, where you export to `.glb`/`.fbx`.

Assembly's role: **inspecting** tag values (spawn coordinates, physics constants, game logic references) and **exporting bitmap textures**. Not geometry.

### Gap 2: Shader parity is impossible

**Fact:** Blam engine's renderer is proprietary. No open-source shader implementation exists.

**Workaround:** Approximate with Godot's `StandardMaterial3D` + `ORMMaterial3D` + manual parameter tuning against side-by-side screenshots from HREK Standalone. Accept 90% visual parity. The geometry and gameplay will be identical; the lighting will be close.

### Gap 3: ChimpsAtSea repo location uncertain

**Fact:** The exact GitHub URL `github.com/ChimpsAtSea/Reach-Decomp` returned 404.

**Workaround:** The project exists in the community. Verify current location via:
1. `c20.reclaimers.net/hr/engine` (the HR Engine page on the Reclaimers wiki)
2. The Reclaimers Discord (linked from c20.reclaimers.net)
3. r/halomods on Reddit

The decompilation is your reference for physics constants. If the repo is temporarily unavailable, community documentation on c20 and Discord carries the same information.

### Gap 4: .mvar parsing requires community tools

**Fact:** `.mvar` files are binary Forge map variant files. Assembly can read them, but there may not be a direct JSON export.

**Workaround:** Assembly's tag browser can open `.mvar` files (they're variant cache files). Navigate to the `scenario` tag within the `.mvar` and manually export Forge object placement data. Alternatively, use the community-developed `.mvar` parsers (search Reclaimers Discord for "mvar reader" or "forge variant parser").

### Gap 5: Windows required for extraction

**Fact:** HREK and Assembly only run on Windows.

**Workaround:** On macOS, use:
- **Parallels Desktop** (paid, best performance)
- **UTM** (free, QEMU-based, slower but works)
- **Whisky** (free, Wine translation layer — may work for Assembly, unlikely for HREK which needs DirectX)

Or use a separate Windows PC. Extraction is a one-time operation — once you have `.glb` files and JSON data, you never need Windows again.

### Gap 6: Infection logic is engine-level, not tag data

**Fact:** The `scenario` tag defines spawn points and teams, but the actual Infection round system (alpha zombie selection, last man standing, round timer, human→infected conversion) is hardcoded in Blam engine source.

**Workaround:** Recreate the logic from the Reach decompilation reference + community documentation. The FSM design in Section 5.3 covers all known Infection mechanics. Cross-reference with the Reclaimers wiki and community guides.

---

## 8. Implementation Phases — Time Estimates

### Phase 1: Acquisition & Extraction (Windows) — 3-5 days

- [ ] Purchase MCC on Steam
- [ ] Install HREK via Steam Workshop
- [ ] Install Assembly (build from source or download release)
- [ ] Open `forge_halo.map` in Assembly — verify tag accessibility
- [ ] Extract terrain geometry via HREK + Blender toolset
- [ ] Extract collision geometry
- [ ] Extract textures (bitmap tags)
- [ ] Extract spawn point coordinates from scenario tag
- [ ] Obtain target Infection `.mvar` from File Share Archive
- [ ] Parse `.mvar` for Forge object coordinates
- [ ] Export all assets as `.glb` + JSON data files
- [ ] Copy assets to Mac

### Phase 2: Godot Project Setup (macOS) — 2-3 days

- [ ] Install Godot 4.3+ .NET edition
- [ ] Create project structure
- [ ] Import `.glb` files — verify geometry renders
- [ ] Set up collision body from collision mesh
- [ ] Create `reach_physics.json` with initial placeholder values
- [ ] Build scene tree (Section 5.1)
- [ ] Verify map renders and collision works (walk around with a basic controller)

### Phase 3: Player Controller (macOS) — 3-5 days

- [ ] Write `PlayerController.cs` (Section 5.2)
- [ ] Get real physics constants from decompilation / HREK Standalone
- [ ] Update `reach_physics.json` with exact values
- [ ] Tune movement feel against HREK Standalone (side-by-side)
- [ ] Implement crouch, sprint, jump
- [ ] Implement camera look (right stick)
- [ ] Test with DualShock 4 on macOS

### Phase 4: Infection Game Mode (macOS) — 3-5 days

- [ ] Write `InfectionFSM.gd` (Section 5.3)
- [ ] Implement team assignment (human / infected)
- [ ] Implement alpha zombie selection
- [ ] Implement human→infected conversion on death
- [ ] Implement Last Man Standing detection + bonus
- [ ] Implement round timer
- [ ] Implement round end conditions
- [ ] Implement match end (N rounds, tally wins)

### Phase 5: Split-Screen + Multi-Controller (macOS) — 3-5 days

- [ ] Build `SplitScreenManager.gd` (Section 5.4)
- [ ] Build `InputManager.gd` with device-specific routing (Section 5.5)
- [ ] Test with 2 DualShock 4 controllers
- [ ] Test with 4 DualShock 4 controllers (may need USB hub or multiple Bluetooth)
- [ ] Tune per-viewport resolution for performance

### Phase 6: Forge Object Placement (macOS) — 2-3 days

- [ ] Build `ForgeObjectPlacer.gd` — reads JSON, instantiates objects
- [ ] Create `.glb` for each unique Forge piece type
- [ ] Place objects at exact coordinates from `.mvar` data
- [ ] Verify barricades/walls block movement (collision on Forge objects)
- [ ] Use `MultiMeshInstance3D` for performance

### Phase 7: Visual Polish (macOS) — 5-10 days

- [ ] Recreate Reach skybox in `WorldEnvironment`
- [ ] Match fog density and color
- [ ] Bake `LightmapGI` from map geometry
- [ ] Tune material parameters against HREK screenshots
- [ ] Add weapon viewmodels (extracted Spartan + weapon models)
- [ ] Add HUD (health bar, ammo counter, round timer, team indicator)
- [ ] Add infection death effect (player transforms to zombie on death)

### Phase 8: Weapon & Combat (macOS) — 5-10 days

- [ ] Extract weapon models + damage values from tags
- [ ] Implement basic weapon firing (hitscan for human weapons)
- [ ] Implement zombie melee attack (lunge + damage)
- [ ] Implement damage → death → team conversion
- [ ] Balance against Reach values from decompilation

---

## 9. Key Reference Links — Verified

| # | Resource | URL | Verified |
|---|----------|-----|----------|
| 1 | Assembly (XboxChaos) | `github.com/XboxChaos/Assembly` | ✅ 261 stars, 99 forks, wiki exists |
| 2 | Reclaimers Library (c20) | `c20.reclaimers.net` | ✅ Live, Reach section with tag docs |
| 3 | HR tags reference | `c20.reclaimers.net/hr/tags` | ✅ Lists every Reach tag type |
| 4 | HR map cache file | `c20.reclaimers.net/hr/map` | ⚠️ Page exists but minimal content |
| 5 | Assembly Wiki | `github.com/XboxChaos/Assembly/wiki` | ✅ Sparse but real |
| 6 | Halo Reach Editing Kit | Steam Workshop (MCC) | ✅ Official, documented on c20 |
| 7 | Halo Asset Blender Dev Toolset | Referenced on c20 Reach page | ✅ Linked from c20 |
| 8 | Reclaimers Discord | Linked from `c20.reclaimers.net` | ✅ Active community |
| 9 | Ultimate File Share Archive | Reddit (r/halo, r/forge) + spreadsheet | ✅ Community-confirmed |
| 10 | Reach Decompilation | Verify via c20 or Discord | ⚠️ Repo URL needs verification |

---

## 10. Critical Success Factors

1. **Exact physics constants** — Get these from the decompilation, not guesses. This is what makes it "feel" like Reach.
2. **Separate collision mesh** — Don't use the render mesh for collision. Extract the `collision_model` tag separately.
3. **.mvar coordinate data** — This is what makes the map IDENTICAL to a specific Infection variant, not just Forge World.
4. **Device-specific input** — Godot's default `Input` reads all devices. For 4-player split-screen, you MUST filter by `event.device`.
5. **Performance budget** — 4 viewports at 960×540 is what Xbox 360 ran at. Don't try 4×1080p on day one.
6. **Physics tick rate** — Run at 60 Hz minimum. Blam engine ticks at 30 Hz on Xbox 360 but 60 Hz on MCC. Match MCC.
7. **glTF 2.0 as interchange** — Not FBX. glTF preserves materials, UVs, and node hierarchy better in Godot 4.

---

## Appendix A: File Structure

```
halo-reach-engine/
├── project.godot
├── data/
│   ├── reach_physics.json
│   ├── spawn_coordinates.json
│   ├── forge_objects.json
│   └── weapon_data.json
├── assets/
│   ├── maps/
│   │   ├── hemorrhage_terrain.glb
│   │   ├── hemorrhage_collision.glb
│   │   └── hemorrhage_textures/
│   │       ├── terrain_01.webp
│   │       ├── terrain_02.webp
│   │       └── skybox.webp
│   ├── forge_pieces/
│   │   ├── wall_straight.glb
│   │   ├── wall_corner.glb
│   │   ├── ramp.glb
│   │   ├── block.glb
│   │   └── ...
│   ├── characters/
│   │   ├── spartan_human.glb
│   │   └── spartan_zombie.glb
│   └── weapons/
│       ├── assault_rifle.glb
│       ├── magnum.glb
│       └── ...
├── scripts/
│   ├── cs/
│   │   ├── PlayerController.cs
│   │   ├── CameraFollow.cs
│   │   └── WeaponController.cs
│   └── gd/
│       ├── InfectionFSM.gd
│       ├── SplitScreenManager.gd
│       ├── InputManager.gd
│       ├── ForgeObjectPlacer.gd
│       └── ScoreManager.gd
├── scenes/
│   ├── HemorrhageInfection.tscn
│   ├── Player.tscn
│   └── InfectionHUD.tscn
└── SPEC.md  ← this file
```

---

## Appendix B: Physics Constant Verification Protocol

To verify each physics constant is correct:

1. Open HREK Standalone on Windows
2. Load `forge_halo.map`
3. Start the game (console: `halo(game_start levels\forge_world\forge_world)`)
4. In Assembly, open the same map
5. Navigate to the biped tag (`bip\cyborg\cyborg`)
6. Read the physics fields:
   - `gravity_scale`
   - `ground_speed` / `walk_speed` / `run_speed`
   - `jump_height` / `jump_velocity`
   - `acceleration` / `deceleration` curves
7. Write each value to `reach_physics.json`
8. In Godot, load these values at runtime
9. Test movement side-by-side: do the same jump in Standalone and in Godot. The jump arc should match.

This protocol is the difference between "feels like Halo" and "IS Halo."
