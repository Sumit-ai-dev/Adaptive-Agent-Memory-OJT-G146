#!/usr/bin/env python3
"""
Generate PNG icons for AEMA Chrome Extension (Manifest V3)
using standard library zlib and struct.
"""

import struct
import zlib
from pathlib import Path


def create_png(width: int, height: int, pixels: bytes) -> bytes:
    """Create a valid RGBA PNG file from raw pixel bytes."""
    # PNG signature
    png = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    png += struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)

    # IDAT chunk (scanline filtered with 0x00)
    raw_scanlines = bytearray()
    for y in range(height):
        raw_scanlines.append(0)  # filter type 0: None
        start = y * width * 4
        end = start + width * 4
        raw_scanlines.extend(pixels[start:end])

    compressed = zlib.compress(bytes(raw_scanlines), 9)
    idat_crc = zlib.crc32(b"IDAT" + compressed)
    png += struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)

    # IEND chunk
    iend_crc = zlib.crc32(b"IEND")
    png += struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    return png


def generate_aema_icon(size: int) -> bytes:
    """Generate an obsidian badge icon with cyan glowing core for AEMA."""
    pixels = bytearray(size * size * 4)
    cx, cy = size / 2.0, size / 2.0
    radius = size * 0.44

    for y in range(size):
        for x in range(size):
            idx = (y * size + x) * 4
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > radius:
                # Transparent outside circle
                pixels[idx : idx + 4] = b"\x00\x00\x00\x00"
            elif dist > radius - 1.5:
                # Border outline (subtle cyan border)
                alpha = int(255 * (radius - dist) / 1.5)
                pixels[idx : idx + 4] = bytes([56, 189, 248, alpha])
            else:
                # Inner obsidian body with radial glow
                norm_d = dist / radius
                # Dark obsidian base (#0a0a0c) transitioning to center core
                r = int(10 + (1.0 - norm_d) * 20)
                g = int(12 + (1.0 - norm_d) * 35)
                b = int(16 + (1.0 - norm_d) * 60)
                # Draw stylized AE symbol glyph in center
                nx = (x - cx) / radius
                ny = (y - cy) / radius

                # Simple geometric AE glyph
                is_glyph = False
                # Left vertical bar of A
                if -0.45 <= nx <= -0.32 and -0.45 <= ny <= 0.45:
                    is_glyph = True
                # Top horizontal bar
                if -0.45 <= nx <= 0.35 and -0.45 <= ny <= -0.32:
                    is_glyph = True
                # Middle bar
                if -0.45 <= nx <= 0.25 and -0.06 <= ny <= 0.07:
                    is_glyph = True
                # Bottom horizontal bar
                if -0.45 <= nx <= 0.35 and 0.32 <= ny <= 0.45:
                    is_glyph = True
                # Central diagonal / cross of A
                if -0.15 <= nx <= -0.02 and -0.45 <= ny <= 0.45:
                    is_glyph = True

                if is_glyph:
                    # Glowing cyan/white glyph
                    pixels[idx : idx + 4] = b"\x38\xbd\xf8\xff"
                else:
                    pixels[idx : idx + 4] = bytes([r, g, b, 255])

    return create_png(size, size, bytes(pixels))


def main():
    icons_dir = Path("extension/icons")
    icons_dir.mkdir(parents=True, exist_ok=True)

    sizes = [16, 48, 128]
    for s in sizes:
        png_data = generate_aema_icon(s)
        icon_path = icons_dir / f"icon{s}.png"
        icon_path.write_bytes(png_data)
        print(f"Generated {icon_path} ({len(png_data)} bytes)")


if __name__ == "__main__":
    main()
