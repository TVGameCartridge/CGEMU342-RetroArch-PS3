#!/usr/bin/env python3
"""Initialize and refresh PSL1GHT RSX texture filtering from RetroArch video_smooth.

This intentionally touches only the PSL1GHT RSX video frontend, not the
CGEMU342 FCEUmm emulator. Works around an upstream RSX initialization gap:
rsx_t is zero-initialized, but rsx_init does not transfer video->smooth,
so first-time game textures default to nearest filtering until some menu
state change happens. Also re-sync each frame from current video settings,
making runtime bilinear toggle deterministic.
"""
import argparse
from pathlib import Path

def patch(source: str) -> str:
    init_anchor = "   rsx->video_info = *video;\n"
    init_insert = ("   rsx->video_info = *video;\n"
                   "   /* Match the incoming RetroArch bilinear setting at startup. */\n"
                   "   rsx->smooth = video->smooth;\n")
    frame_anchor = "   rsx_t *gcm                       = (rsx_t*)data;\n"
    frame_insert = (frame_anchor
                    + "   /* Update RSX texture filtering on every frame: supports live toggles. */\n"
                    + "   if (gcm && video_info)\n"
                    + "      gcm->smooth = video_info->video_smooth;\n")
    for desc, old, new in [
        ("rsx_init", init_anchor, init_insert),
        ("rsx_frame", frame_anchor, frame_insert),
    ]:
        if source.count(old) != 1:
            raise ValueError(f"Expected exactly one {desc} anchor, found {source.count(old)}")
        source = source.replace(old, new, 1)
    return source

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("retroarch_source", type=Path)
    args = ap.parse_args()
    p = args.retroarch_source / "gfx/drivers/rsx_gfx.c"
    old = p.read_text(encoding="utf-8")
    new = patch(old)
    p.write_text(new, encoding="utf-8")
    assert "rsx->smooth = video->smooth;" in new
    assert "gcm->smooth = video_info->video_smooth;" in new
    print("Patched PSL1GHT RSX bilinear startup and runtime updates:", p)

if __name__ == "__main__":
    main()
