#!/usr/bin/env python3
"""Stage a real, already-working PSX-Place CE RETROARCH.zip for personal HEN PKG.

Usage:
  python3 scripts/stage_working_ce_archive.py RETROARCH.zip FCEUX.pal stage-folder
  python3 scripts/pack_ce_debug.py stage-folder custom.pkg UP0001-RETROARCH_00-0000111122223333

The input ZIP and output package stay on your computer. Never upload
personal configuration, ROM saves or Sony/PSX-Place binaries to public GitHub.
"""
from pathlib import Path, PurePosixPath
import hashlib
import re
import sys
import zipfile

PALETTE_SHA256 = "bbb0355bcadc4be771efeb81930b09b17d97dcb8c70167a652902a789158c5f8"
ASSETS_TO_KEEP = {"rgui", "branding", "pkg", "glui", "sounds", "menu_widgets"}
DATABASES_TO_KEEP = {
    "Nintendo - Nintendo Entertainment System.rdb",
    "Nintendo - Family Computer Disk System.rdb",
    "Nintendo - Super Nintendo Entertainment System.rdb",
    "Nintendo - Satellaview.rdb", "Nintendo - Sufami Turbo.rdb",
    "Sega - Mega Drive - Genesis.rdb",
    "Sega - Master System - Mark III.rdb", "Sega - Game Gear.rdb",
    "Sega - Mega-CD - Sega CD.rdb", "Sega - SG-1000.rdb",
    "MAME.rdb", "MAME 2003.rdb", "MAME 2003-Plus.rdb", "DOS.rdb",
}

def stage(input_zip: Path, palette: Path, dst: Path) -> None:
    if dst.exists():
        raise ValueError("Staging destination exists. Refusing overwrite")
    pal = palette.read_bytes()
    if len(pal) != 192 or hashlib.sha256(pal).hexdigest() != PALETTE_SHA256:
        raise ValueError("Expected unmodified official FCEUX.pal (192 bytes)")
    with zipfile.ZipFile(input_zip) as z:
        if z.testzip() is not None:
            raise ValueError("Damaged input ZIP")
        names = set(z.namelist())
        for needed in (
            "PARAM.SFO", "USRDIR/EBOOT.BIN", "USRDIR/retroarch.cfg",
            "USRDIR/retroarch-salamander.cfg", "USRDIR/cores/fceumm_libretro_ps3.SELF",
            "USRDIR/config/FCEUmm/FCEUmm.cfg",
            "USRDIR/config/FCEUmm/FCEUmm.opt",
        ):
            if needed not in names:
                raise ValueError("Missing installed-file requirement: " + needed)
        sfo = z.read("PARAM.SFO")
        if b"RETROARCH\\0" not in sfo or b"PSX-Place" not in sfo:
            raise ValueError("Unexpected title ID or distribution")
        main_cfg = z.read("USRDIR/retroarch.cfg").decode("utf-8")
        if not re.search(r'^menu_driver\\s*=\\s*"rgui"', main_cfg, re.M):
            raise ValueError("Current menu is not RGUI; do not prune menu themes")
        if 'system_directory = "/dev_hdd0/game/RETROARCH/USRDIR/system"' not in main_cfg:
            raise ValueError("Unexpected FCEUmm system dir for nes.pal")
        if "/dev_hdd0/game/RETROARCH/USRDIR/cores/fceumm_libretro_ps3.SELF" not in z.read("USRDIR/retroarch-salamander.cfg").decode():
            raise ValueError("Saved boot core would not resolve after installation")
        opt = z.read("USRDIR/config/FCEUmm/FCEUmm.opt").decode("utf-8")
        for setting in ('fceumm_aspect = "4:3"', 'fceumm_nospritelimit = "enabled"', 'fceumm_turbo_enable = "Both"'):
            if setting not in opt:
                raise ValueError("Missing known working setting: " + setting)
        if opt.count('fceumm_palette = "default"') != 1:
            raise ValueError("Unexpected previous palette config")
        opt = opt.replace('fceumm_palette = "default"', 'fceumm_palette = "custom"')
        cores = {PurePosixPath(n).name.removesuffix("_libretro_ps3.SELF")
                 for n in names if n.startswith("USRDIR/cores/") and n.endswith(".SELF")}
        dst.mkdir(parents=True)
        retained = 0
        excluded = 0
        for item in z.infolist():
            name = item.filename
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\\\" in name or ":" in name:
                raise ValueError("Unsafe ZIP entry: " + name)
            if not path.parts or not (path.parts[0] == "USRDIR" or name in (
                    "PARAM.SFO", "ICON0.PNG", "PIC1.PNG", "PS3LOGO.DAT", "SND0.AT3")):
                raise ValueError("Unexpected ZIP entry: " + name)
            parts = path.parts
            omit = (
                (len(parts) >= 3 and parts[:2] == ("USRDIR", "assets")
                 and parts[2] not in ASSETS_TO_KEEP and parts[2] not in {"COPYING", "Makefile", "configure"})
                or (len(parts) >= 4 and parts[:3] == ("USRDIR", "database", "rdb")
                    and path.name not in DATABASES_TO_KEEP)
                or (len(parts) == 3 and parts[:2] == ("USRDIR", "info")
                    and (path.name == "core_info.cache"
                         or (path.name.endswith("_libretro.info")
                             and path.name.removesuffix("_libretro.info") not in cores)))
                or (len(parts) > 2 and parts[:2] == ("USRDIR", "savefiles")
                    and path.suffix.lower() in (".srm", ".sav", ".rtc"))
                or path.name.endswith(".log") or path.name.endswith("-log.txt")
            )
            if omit:
                excluded += not item.is_dir()
                continue
            target = dst.joinpath(*parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = opt.encode("utf-8") if name == "USRDIR/config/FCEUmm/FCEUmm.opt" else z.read(item)
            target.write_bytes(raw)
            retained += 1
        (dst / "USRDIR/system").mkdir(parents=True, exist_ok=True)
        (dst / "USRDIR/system/nes.pal").write_bytes(pal)
        print("Staged", retained+1, "files,", len(cores), "core(s); excluded", excluded, "unused files")
        print("Preserved all configs except FCEUmm palette default -> custom")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: stage_working_ce_archive.py RETROARCH.zip FCEUX.pal STAGE")
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
