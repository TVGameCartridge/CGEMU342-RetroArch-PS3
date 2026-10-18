#!/usr/bin/env python3
"""Prepare upstream libretro-fceumm for the PS3 core build.

Mapper 301 is intentionally selectable: the custom 8157 interpretation
and the upstream K-3003 interpretation are different hardware.
This script performs source checks; it does not test PS3/ROM behavior.
"""
import argparse
from pathlib import Path
import re
import shutil

EXPECTED = (264, 287, 301, 315, 344, 358, 393, 395)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fceumm", type=Path, help="Cloned libretro-fceumm directory")
    parser.add_argument("--mapper301", choices=("8157", "upstream"), default="8157")
    args = parser.parse_args()

    root = args.fceumm.resolve()
    ines = root / "src" / "ines.c"
    board301 = root / "src" / "boards" / "301.c"
    if not ines.is_file() or not board301.is_file():
        parser.error("Expected src/ines.c and src/boards/301.c from libretro-fceumm")

    text = ines.read_text(encoding="utf-8")
    ids = {int(i) for i in re.findall(
        r'INES_BOARD\s*\(\s*"[^"]*"\s*,\s*(\d+)\s*,', text
    )}
    missing = [i for i in EXPECTED if i not in ids]
    if missing:
        parser.error(f"Upstream mapping table missing IDs: {missing}")

    if args.mapper301 == "8157":
        source = Path(__file__).resolve().parents[1] / "compat" / "mapper301_8157.c"
        if not source.is_file():
            parser.error("Missing compat/mapper301_8157.c")
        # Replace, not add: Makefile.common compiles every src/boards/*.c.
        shutil.copyfile(source, board301)
        if "Mapper301_Init" not in board301.read_text(encoding="utf-8"):
            parser.error("Missing Mapper301_Init in compatibility source")

    print("FCEUmm mapping entries verified:", ", ".join(map(str, EXPECTED)))
    print("Mapper 301 hardware mode:", args.mapper301)
    print("CAUTION: These are source checks, not evidence of ROM compatibility")


if __name__ == "__main__":
    main()
