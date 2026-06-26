#!/usr/bin/env python3
"""
capture_gameplay.py — Record reference gameplay footage for AI reconstruction.

Runs on Windows (OBS + NVENC) or captures from console via capture card.

Modes:
  - obs:      Record MCC gameplay via OBS Studio automation
  - console:  Capture from Xbox 360/One via HDMI capture card
  - youtube:  Download reference footage from YouTube (for games you don't own)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def capture_obs(game: str, map_name: str, duration: int, output_dir: Path) -> int:
    """Automate OBS Studio recording on Windows."""
    print(f"\n  🎥 OBS Capture: {game} — {map_name}")
    print(f"     Duration: {duration}s")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{map_name}_{timestamp}.mkv"

    # OBS command line (when installed):
    # obs64.exe --startrecording --profile "Capture" --scene "Game Capture" 
    #           --portable --minimize-to-tray
    
    # OBS WebSocket API for precise control
    print(f"  📋 OBS recording setup:")
    print(f"     1. Install OBS Studio: https://obsproject.com/")
    print(f"     2. Install OBS WebSocket plugin (Tools → WebSocket Server Settings)")
    print(f"     3. Configure scene with Game Capture source (MCC window)")
    print(f"     4. Recording settings: NVENC AV1, 4K, 120fps, CQP 18")
    print(f"     5. Output: {output_file}")
    print(f"")
    print(f"  🤖 Automated capture via OBS WebSocket API:")
    print(f"     from obsws import OBSWS")
    print(f"     obs = OBSWS('localhost', 4455, 'password')")
    print(f"     obs.connect()")
    print(f"     obs.start_record()")
    print(f"     time.sleep({duration})")
    print(f"     obs.stop_record()")

    # Alternative: Simple hotkey + timer approach
    print(f"\n  🔑 Simplified approach: Run this, start recording manually,")
    print(f"     play for {duration}s, and the script tracks time:")
    print(f"     (Press Ctrl+C to stop early)")
    
    try:
        print(f"\n  ⏱  Recording... (0/{duration}s)", end="", flush=True)
        for i in range(duration):
            time.sleep(1)
            if i % 30 == 0:
                print(f"\r  ⏱  Recording... ({i}/{duration}s)", end="", flush=True)
        print(f"\r  ✅ Recording complete ({duration}s)         ")
    except KeyboardInterrupt:
        print(f"\n  ⏹  Recording stopped by user")

    return 0


def capture_console(map_name: str, duration: int, output_dir: Path) -> int:
    """Capture from Xbox 360/One via HDMI capture card."""
    print(f"\n  🎮 Console Capture: {map_name}")
    print(f"     Requires: Elgato 4K X or AverMedia Live Gamer 4K")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{map_name}_console_{timestamp}.mkv"

    # Check for capture device
    if sys.platform == "darwin":
        result = subprocess.run(
            ["system_profiler", "SPUSBDataType"],
            capture_output=True, text=True
        )
        if "Elgato" in result.stdout or "AVerMedia" in result.stdout:
            print("  ✅ Capture card detected via USB")
        else:
            print("  ⚠️  No capture card detected")

    # FFmpeg direct capture (when device path is known):
    print(f"  📋 Capture via FFmpeg:")
    print(f"     ffmpeg -f avfoundation -i 'Elgato 4K X' \\")
    print(f"            -c:v hevc_videotoolbox -b:v 50M \\")
    print(f"            -preset fast -t {duration} {output_file}")

    return 0


def download_youtube(url: str, output_dir: Path) -> int:
    """Download reference gameplay from YouTube."""
    print(f"\n  📥 YouTube Download: {url}")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    # yt-dlp for high quality download
    try:
        subprocess.run(
            ["yt-dlp", "-f", "bestvideo[height<=2160]+bestaudio",
             "-o", str(output_dir / "%(title)s.%(ext)s"),
             url],
            check=True
        )
        print("  ✅ Download complete")
    except FileNotFoundError:
        print("  ❌ yt-dlp not installed — pip3 install yt-dlp")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="Gameplay Capture Pipeline")
    parser.add_argument("--game", default="Halo Reach", help="Game name")
    parser.add_argument("--map", default="Hemorrhage", help="Map/variant name")
    parser.add_argument("--mode", default="manual",
                        choices=["manual", "obs", "console", "youtube"],
                        help="Capture mode")
    parser.add_argument("--duration", type=int, default=300,
                        help="Recording duration in seconds")
    parser.add_argument("--youtube-url", help="YouTube URL for download mode")
    parser.add_argument("--output", default="capture/sessions",
                        help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output) / args.map
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"  Gameplay Capture: {args.game} — {args.map}")
    print(f"  Mode: {args.mode}, Duration: {args.duration}s")
    print("=" * 60)

    if args.mode == "manual":
        print(f"\n  📋 Manual capture guide:")
        print(f"     Game:  {args.game}")
        print(f"     Map:   {args.map}")
        print(f"")
        print(f"  Walkthrough script to capture:")
        print(f"  1. Start at each human spawn point — pan 360° slowly")
        print(f"  2. Walk all major pathways — keep camera steady")
        print(f"  3. Approach each Forge barricade — orbit around it")
        print(f"  4. Capture from infected spawn points — same 360° pan")
        print(f"  5. Get close-ups of textures: ground, walls, rocks")
        print(f"  6. Record a full round of Infection gameplay")
        print(f"")
        print(f"  Camera settings: 4K, 120fps, motion blur OFF, film grain OFF")
        print(f"  Duration: {args.duration}s minimum")
        print(f"  Save to: {output_dir}/")
        return 0

    modes = {
        "obs": lambda: capture_obs(args.game, args.map, args.duration, output_dir),
        "console": lambda: capture_console(args.map, args.duration, output_dir),
        "youtube": lambda: download_youtube(args.youtube_url, output_dir) if args.youtube_url else 0,
    }

    return modes[args.mode]()


if __name__ == "__main__":
    sys.exit(main())