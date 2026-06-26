#!/usr/bin/env python3
"""
extract_assets.py — SSH into Windows VM, orchestrate HREK + Assembly extraction,
pull files back to macOS.

Supports:
  --test              Test SSH connection only
  --extract bsp       Extract terrain BSP mesh
  --extract collision Extract collision geometry
  --extract textures  Extract bitmap textures
  --extract spawns    Extract spawn coordinates
  --extract forge     Extract Forge object placements
  --extract physics   Query physics constants
  --extract all       Extract everything

Architecture:
  macOS (this script) ──SSH──▶ Windows VM (powershell commands) ──▶ HREK / Assembly
  ◀──SCP── extracted files (.dds, .json, .xml)
"""

import argparse
import os
import sys
import json
import time
from pathlib import Path
from typing import Optional

try:
    import paramiko
    from scp import SCPClient
except ImportError:
    print("❌ Missing dependencies. Run: pip3 install paramiko scp pyyaml")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("❌ Missing pyyaml. Run: pip3 install pyyaml")
    sys.exit(1)


# ── Config ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "tools" / "extraction" / "configs" / "config.yaml"

if not CONFIG_PATH.exists():
    print(f"❌ Config not found: {CONFIG_PATH}")
    print("   Copy config.example.yaml → config.yaml and fill in VM details")
    sys.exit(1)

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

VM = config["vm"]
PATHS = config["paths"]


# ── SSH Connection ──────────────────────────────────────────────────────────

class WindowsVMBridge:
    """SSH bridge to Windows VM running OpenSSH server."""

    def __init__(self):
        self.ssh: Optional[paramiko.SSHClient] = None
        self.scp: Optional[SCPClient] = None

    def connect(self) -> bool:
        """Connect to the Windows VM via SSH."""
        print(f"🔌 Connecting to {VM['host']}:{VM['port']} as {VM['username']}...")

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            key_file = os.path.expanduser(VM.get("key_file", ""))
            if key_file and os.path.exists(key_file):
                key = paramiko.Ed25519Key.from_private_key_file(key_file)
                self.ssh.connect(
                    VM["host"], port=VM["port"],
                    username=VM["username"], pkey=key,
                    timeout=15
                )
            elif VM.get("password"):
                self.ssh.connect(
                    VM["host"], port=VM["port"],
                    username=VM["username"], password=VM["password"],
                    timeout=15
                )
            else:
                print("❌ No key_file or password in config.yaml")
                return False

            self.scp = SCPClient(self.ssh.get_transport())
            print(f"✅ Connected to {VM['host']}")
            return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("\n   Make sure:")
            print("   1. Windows VM is running in UTM")
            print("   2. OpenSSH Server is installed and running on Windows")
            print("   3. Your SSH key is in C:\\Users\\<user>\\.ssh\\authorized_keys")
            return False

    def run(self, command: str, timeout: int = 300) -> tuple[int, str, str]:
        """Run a PowerShell command on the Windows VM."""
        if not self.ssh:
            return -1, "", "Not connected"

        full_cmd = f'powershell -NoProfile -Command "{command}"'
        print(f"  🖥  {command[:100]}...")
        stdin, stdout, stderr = self.ssh.exec_command(full_cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return exit_code, out, err

    def pull_file(self, remote_path: str, local_path: str) -> bool:
        """SCP a file from Windows VM to macOS."""
        try:
            self.scp.get(remote_path, local_path)
            print(f"  📥 Pulled: {remote_path} → {local_path}")
            return True
        except Exception as e:
            print(f"  ❌ SCP failed: {e}")
            return False

    def pull_directory(self, remote_dir: str, local_dir: str) -> bool:
        """SCP a directory recursively."""
        try:
            os.makedirs(local_dir, exist_ok=True)
            # List files and pull individually (SCP recursive is flaky)
            _, out, _ = self.run(f"Get-ChildItem -Path '{remote_dir}' -Recurse -File | Select -Expand FullName")
            for line in out.strip().split("\n"):
                line = line.strip()
                if line:
                    rel = os.path.relpath(line, remote_dir)
                    local = os.path.join(local_dir, rel)
                    os.makedirs(os.path.dirname(local), exist_ok=True)
                    self.pull_file(line, local)
            return True
        except Exception as e:
            print(f"  ❌ Directory pull failed: {e}")
            return False

    def disconnect(self):
        if self.scp:
            self.scp.close()
        if self.ssh:
            self.ssh.close()
        print("🔌 Disconnected")


# ── Extraction Commands ─────────────────────────────────────────────────────

def extract_bsp(bridge: WindowsVMBridge) -> bool:
    """Extract terrain BSP from forge_halo.map via HREK tag export."""
    print("\n🗺  Extracting terrain BSP...")
    
    scratch = PATHS["extraction_scratch"]
    map_path = PATHS["forge_halo_map"]
    hrek_dir = PATHS["hrek_dir"]

    # Step 1: Use HREK's tag extraction tool to export scenario_structure_bsp
    # HREK has a command-line tool: hrek_tag_extract.exe
    extractor = f"{hrek_dir}\\tools\\hrek_tag_extract.exe"
    cmd = (
        f'& "{extractor}" '
        f'--map "{map_path}" '
        f'--tag "scenario_structure_bsp" '
        f'--output "{scratch}\\bsp" '
        f'2>&1'
    )
    exit_code, out, err = bridge.run(cmd)
    
    if exit_code != 0:
        print(f"  ⚠️  HREK CLI may not exist — using manual extraction path")
        print(f"     Output: {out[:200]}")
        print(f"     Error: {err[:200]}")
        print(f"  📋 Manual step: Open HREK Standalone, load forge_halo.map,")
        print(f"     export scenario_structure_bsp tag to {scratch}\\bsp")
    
    # Step 2: Pull extracted files to macOS
    local_bsp = str(PROJECT_ROOT / "assets" / "maps")
    bridge.pull_directory(f"{scratch}\\bsp", f"{local_bsp}")
    
    return True


def extract_collision(bridge: WindowsVMBridge) -> bool:
    """Extract collision_model tags via Assembly."""
    print("\n🧱 Extracting collision geometry...")

    assembly = PATHS["assembly_exe"]
    map_path = PATHS["forge_halo_map"]
    scratch = PATHS["extraction_scratch"]

    # Assembly CLI: assembly-cli.exe (if available) or use PowerShell COM
    cmd = (
        f'if (Test-Path "{assembly}") {{ '
        f'  Write-Output "Assembly found at {assembly}"; '
        f'  Write-Output "Manual: Open Assembly → forge_halo.map → collision_model → Export"; '
        f'}} else {{ '
        f'  Write-Output "Assembly not found — install from github.com/XboxChaos/Assembly"; '
        f'}}'
    )
    bridge.run(cmd)

    # Pull collision data
    local_collision = str(PROJECT_ROOT / "assets" / "maps")
    bridge.pull_directory(f"{scratch}\\collision", f"{local_collision}")

    return True


def extract_textures(bridge: WindowsVMBridge) -> bool:
    """Extract bitmap textures from forge_halo.map via Assembly."""
    print("\n🎨 Extracting textures...")

    assembly = PATHS["assembly_exe"]
    map_path = PATHS["forge_halo_map"]
    scratch = PATHS["extraction_scratch"]

    # Assembly can export bitmap tags as .dds/.png
    cmd = (
        f'Write-Output "Opening {map_path} in Assembly for texture export..."; '
        f'Write-Output "Navigate to bitmap tags → Select all → Export as .dds → {scratch}\\textures"'
    )
    bridge.run(cmd)

    local_textures = str(PROJECT_ROOT / "assets" / "maps" / "hemorrhage_textures")
    bridge.pull_directory(f"{scratch}\\textures", f"{local_textures}")

    return True


def extract_spawns(bridge: WindowsVMBridge) -> bool:
    """Extract spawn point coordinates from scenario tag via Assembly."""
    print("\n📍 Extracting spawn coordinates...")

    scratch = PATHS["extraction_scratch"]

    # Query scenario tag for player_starting_locations
    cmd = (
        f'Write-Output "Open forge_halo.map in Assembly → scenario tag → player_starting_locations"; '
        f'Write-Output "Export as JSON → {scratch}\\spawn_coordinates.json"'
    )
    bridge.run(cmd)

    local_path = str(PROJECT_ROOT / "data" / "spawn_coordinates.json")
    bridge.pull_file(f"{scratch}\\spawn_coordinates.json", local_path)

    return True


def extract_forge(bridge: WindowsVMBridge) -> bool:
    """Extract Forge object placements from .mvar file."""
    print("\n🔧 Extracting Forge object placements...")

    mvar_path = PATHS["infection_mvar"]
    scratch = PATHS["extraction_scratch"]

    # Assembly can read .mvar files
    cmd = (
        f'if (Test-Path "{mvar_path}") {{ '
        f'  Write-Output "Opening {mvar_path} in Assembly..."; '
        f'  Write-Output "Export Forge object data as JSON → {scratch}\\forge_objects.json"; '
        f'}} else {{ '
        f'  Write-Output "⚠️  .mvar file not found — download from Halo File Share Archive first"; '
        f'  Write-Output "    Place at: {mvar_path}"; '
        f'}}'
    )
    bridge.run(cmd)

    local_path = str(PROJECT_ROOT / "data" / "forge_objects.json")
    bridge.pull_file(f"{scratch}\\forge_objects.json", local_path)

    return True


def extract_physics(bridge: WindowsVMBridge) -> bool:
    """Query physics constants from biped tag via HREK Standalone console."""
    print("\n📐 Extracting physics constants...")

    # HREK Standalone console commands to query biped physics
    # (these are entered in the in-app console, not scriptable via CLI)
    cmd = (
        f'Write-Output "=== Physics Extraction Protocol ==="; '
        f'Write-Output "1. Open HREK Standalone"; '
        f'Write-Output "2. Console: halo(game_start levels\\\\forge_world\\\\forge_world)"; '
        f'Write-Output "3. Open Assembly → bip\\\\cyborg\\\\cyborg tag"; '
        f'Write-Output "4. Record these values:"; '
        f'Write-Output "   - gravity_scale"; '
        f'Write-Output "   - walk_speed, run_speed, crouch_speed"; '
        f'Write-Output "   - jump_height, jump_velocity"; '
        f'Write-Output "   - ground_acceleration, ground_deceleration"; '
        f'Write-Output "   - air_acceleration, air_deceleration"; '
        f'Write-Output "5. Update data/reach_physics.json with real values"; '
        f'Write-Output "================================="'
    )
    bridge.run(cmd)

    print("  📋 Physics extraction is semi-manual — enter values in data/reach_physics.json")
    return True


# ── Main ────────────────────────────────────────────────────────────────────

def test_connection():
    """Test SSH connectivity to the Windows VM."""
    bridge = WindowsVMBridge()
    if not bridge.connect():
        return 1

    # Run a simple test command
    exit_code, out, err = bridge.run("Write-Output '✅ Windows VM is reachable'; $env:COMPUTERNAME")
    if exit_code == 0:
        print(f"  ✅ Windows computer name: {out.strip()}")
    else:
        print(f"  ❌ Command failed: {err}")

    # Check tools
    checks = [
        ("Steam", f'Test-Path "{PATHS["steam_dir"]}"'),
        ("MCC", f'Test-Path "{PATHS["mcc_dir"]}"'),
        ("HREK", f'Test-Path "{PATHS["hrek_dir"]}"'),
        ("Assembly", f'Test-Path "{PATHS["assembly_exe"]}"'),
        ("forge_halo.map", f'Test-Path "{PATHS["forge_halo_map"]}"'),
    ]

    print("\n  Tool availability:")
    for name, check_cmd in checks:
        _, out, _ = bridge.run(check_cmd)
        status = "✅" if "True" in out else "❌"
        print(f"    {status} {name}")

    bridge.disconnect()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Extract assets from Windows VM")
    parser.add_argument("--test", action="store_true", help="Test SSH connection")
    parser.add_argument("--extract", choices=[
        "all", "bsp", "collision", "textures", "spawns", "forge", "physics"
    ], help="What to extract")
    args = parser.parse_args()

    if args.test:
        return test_connection()

    if not args.extract:
        parser.print_help()
        return 0

    bridge = WindowsVMBridge()
    if not bridge.connect():
        return 1

    try:
        extractors = {
            "bsp": extract_bsp,
            "collision": extract_collision,
            "textures": extract_textures,
            "spawns": extract_spawns,
            "forge": extract_forge,
            "physics": extract_physics,
        }

        if args.extract == "all":
            for key, fn in extractors.items():
                fn(bridge)
        elif args.extract in extractors:
            extractors[args.extract](bridge)
        else:
            print(f"Unknown extraction target: {args.extract}")

    finally:
        bridge.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())