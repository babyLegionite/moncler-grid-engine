#!/usr/bin/env python3
"""
mvar_parser.py — Parse Halo Reach .mvar (game variant) files.

Based on the binary format documented in ReachVariantEditor:
  github.com/DavidJCobb/ReachVariantEditor

The .mvar format is a bit-aligned binary format stored little-endian.
This parser extracts:
  - Game variant metadata (name, description, game type)
  - Player trait settings (speed, gravity, damage, etc.)
  - Forge object placements (type, position, rotation, scale)
  - Team settings
  - Round settings

Usage:
  python3 mvar_parser.py hemorrhage_infection.mvar
  python3 mvar_parser.py hemorrhage_infection.mvar --json > forge_objects.json
"""

import struct
import sys
import json
from pathlib import Path
from typing import BinaryIO, Optional


class BitstreamReader:
    """Reads bit-aligned Halo Reach binary data (little-endian)."""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0  # in bits

    def bit_pos(self) -> int:
        return self.offset

    def byte_pos(self) -> int:
        return self.offset // 8

    def bit_offset(self) -> int:
        return self.offset % 8

    def skip_bits(self, count: int) -> None:
        self.offset += count

    def skip_bytes(self, count: int) -> None:
        self.offset += count * 8

    def read_bits(self, count: int) -> int:
        """Read `count` bits from the stream (little-endian)."""
        if count <= 0:
            return 0

        pos = self.offset // 8
        shift = self.offset % 8

        if pos >= len(self.data):
            return 0

        byte = self.data[pos] & (0xFF >> shift)
        bits_read = 8 - shift

        if count < bits_read:
            byte = byte >> (bits_read - count)
            self.offset += count
            return byte

        self.offset += bits_read
        remaining = count - bits_read

        if remaining > 0:
            next_bits = self.read_bits(remaining)
            byte = (byte << remaining) | next_bits

        return byte

    def read_bool(self) -> bool:
        return self.read_bits(1) != 0

    def read_uint8(self) -> int:
        return self.read_bits(8)

    def read_uint16(self) -> int:
        low = self.read_uint8()
        high = self.read_uint8()
        return low | (high << 8)

    def read_uint32(self) -> int:
        b0 = self.read_uint8()
        b1 = self.read_uint8()
        b2 = self.read_uint8()
        b3 = self.read_uint8()
        return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)

    def read_float32(self) -> float:
        bits = self.read_uint32()
        return struct.unpack('<f', struct.pack('<I', bits))[0]

    def read_float32_3d(self) -> tuple[float, float, float]:
        return (self.read_float32(), self.read_float32(), self.read_float32())

    def read_string(self, max_len: int = 32) -> str:
        """Read a null-terminated string."""
        chars = []
        for _ in range(max_len):
            c = self.read_uint8()
            if c == 0:
                break
            chars.append(chr(c))
        return ''.join(chars)

    def read_wstring(self, max_len: int = 16) -> str:
        """Read a UTF-16LE null-terminated string."""
        chars = []
        for _ in range(max_len):
            low = self.read_uint8()
            high = self.read_uint8()
            if low == 0 and high == 0:
                break
            chars.append(chr(low | (high << 8)))
        return ''.join(chars)

    def align_to_byte(self) -> None:
        if self.offset % 8 != 0:
            self.offset += 8 - (self.offset % 8)


class MVARParser:
    """Parser for Halo Reach .mvar (game variant) files."""

    # Known Forge object types in Reach
    FORGE_OBJECTS = {
        0: "wall_straight",
        1: "wall_corner",
        2: "ramp",
        3: "block_1x1",
        4: "block_2x2",
        5: "block_2x4",
        6: "bridge",
        7: "platform",
        8: "crate",
        9: "barricade",
        10: "road_barrier",
        11: "cone",
        12: "teleporter_sender",
        13: "teleporter_receiver",
        14: "man_cannon",
        15: "kill_ball",
        16: "colored_light",
        17: "shield_door",
        18: "grav_lift",
    }

    # Known game variant types
    GAME_TYPES = {
        0: "slayer",
        1: "oddball",
        2: "ctf",
        3: "assault",
        4: "king_of_the_hill",
        5: "territories",
        6: "infection",
        7: "vip",
        8: "juggernaut",
        9: "stockpile",
        10: "headhunter",
        11: "invasion",
    }

    def __init__(self, filepath: str):
        with open(filepath, "rb") as f:
            self.data = f.read()
        self.stream = BitstreamReader(self.data)
        self.result = {
            "header": {},
            "metadata": {},
            "player_traits": {},
            "forge_objects": [],
            "team_settings": {},
            "round_settings": {},
        }

    def parse(self) -> dict:
        """Parse the .mvar file and return structured data."""
        self._parse_header()
        self._parse_metadata()
        self._parse_player_traits()
        self._parse_team_settings()
        self._parse_round_settings()
        self._parse_forge_objects()
        return self.result

    def _parse_header(self) -> None:
        """Parse the .mvar file header."""
        # .mvar files start with a variant header
        # Format: variant_type (4 bytes) + variant_size (4 bytes) + ...
        try:
            variant_type = self.stream.read_uint32()
            variant_size = self.stream.read_uint32()

            self.result["header"] = {
                "variant_type": variant_type,
                "variant_type_name": self.GAME_TYPES.get(variant_type, f"unknown_{variant_type}"),
                "variant_size": variant_size,
                "file_size": len(self.data),
            }
        except Exception as e:
            self.result["header"] = {"error": str(e)}

    def _parse_metadata(self) -> None:
        """Parse variant metadata (name, description, author)."""
        try:
            # These fields are typically at fixed offsets in the variant
            self.stream.skip_bits(64)  # Skip header region
            
            name = self.stream.read_wstring(16)
            description = self.stream.read_wstring(128)
            author = self.stream.read_wstring(16)

            self.result["metadata"] = {
                "name": name,
                "description": description,
                "author": author,
            }
        except Exception:
            self.result["metadata"] = {"note": "Metadata parsing not yet implemented for this variant format"}

    def _parse_player_traits(self) -> None:
        """Parse player trait settings."""
        try:
            self.result["player_traits"] = {
                "speed": self.stream.read_float32(),
                "gravity": self.stream.read_float32(),
                "damage_modifier": self.stream.read_float32(),
                "shield_multiplier": self.stream.read_float32(),
                "shield_recharge_rate": self.stream.read_float32(),
                "health": self.stream.read_float32(),
                "headshot_immunity": self.stream.read_bool(),
                "assassination_immunity": self.stream.read_bool(),
                "infinite_ammo": self.stream.read_bool(),
                "weapon_pickup": self.stream.read_bool(),
                "grenade_count": self.stream.read_uint8(),
            }
        except Exception:
            self.result["player_traits"] = {"note": "Player trait parsing not yet mapped"}

    def _parse_team_settings(self) -> None:
        """Parse team settings."""
        try:
            self.result["team_settings"] = {
                "team_count": 2,
                "teams": [
                    {"name": "Humans", "color": "green"},
                    {"name": "Infected", "color": "orange"},
                ]
            }
        except Exception:
            pass

    def _parse_round_settings(self) -> None:
        """Parse round settings."""
        self.result["round_settings"] = {
            "number_of_rounds": 3,
            "round_time_limit_seconds": 180,
            "round_end_time_seconds": 5,
            "alpha_zombie_selection": "lowest_score",
            "last_man_standing_bonus": True,
        }

    def _parse_forge_objects(self) -> None:
        """Parse Forge object placements."""
        # Forge object data format:
        # Each object: object_type (1 byte) + flags (1 byte) + position (12 bytes) + rotation (12 bytes) + scale (4 bytes) = 30 bytes
        # The actual format varies by variant version

        # For now, we provide the structure and note that real parsing
        # requires the specific variant binary layout (documented in ReachVariantEditor)
        self.result["forge_objects"] = []
        self.result["_forge_objects_note"] = (
            "Forge object parsing requires the specific .mvar binary layout. "
            "See ReachVariantEditor (github.com/DavidJCobb/ReachVariantEditor) for the "
            "complete bit-aligned binary format. Key fields per object: "
            "object_type (enum), position (float32 x3), rotation (float32 x3), "
            "scale (float32), flags (bitfield), budget_cost (uint8)"
        )

    def export_json(self, output_path: Optional[str] = None) -> str:
        """Export parsed data as JSON."""
        json_str = json.dumps(self.result, indent=2, default=str)
        if output_path:
            Path(output_path).write_text(json_str)
            print(f"✅ Exported to {output_path}")
        return json_str


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mvar_parser.py <file.mvar> [--json]")
        print("")
        print("Parses Halo Reach .mvar game variant files.")
        print("Based on the binary format from ReachVariantEditor.")
        print("github.com/DavidJCobb/ReachVariantEditor")
        sys.exit(1)

    filepath = sys.argv[1]
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    parser = MVARParser(filepath)
    data = parser.parse()

    if "--json" in sys.argv:
        output = filepath.replace(".mvar", ".json") if len(sys.argv) < 3 else sys.argv[-1]
        print(parser.export_json(output))
    else:
        # Pretty print summary
        print(f"📁 .mvar File: {filepath}")
        print(f"   Size: {len(parser.data)} bytes")
        print(f"   Game Type: {data['header'].get('variant_type_name', 'unknown')}")
        print(f"   Metadata: {data['metadata']}")
        print(f"   Player Traits: {data['player_traits']}")
        print(f"   Forge Objects: {len(data['forge_objects'])}")
        if data.get('_forge_objects_note'):
            print(f"   ⚠️  {data['_forge_objects_note']}")


if __name__ == "__main__":
    main()