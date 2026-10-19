# Personal PS3 HEN RetroArch CE Custom Installer

This project supports packaging an **actual known-working CE installation**
rather than recreating somebody's preferred settings from scratch.

Source input: the user's locally supplied `RETROARCH.zip`, extracted from
`/dev_hdd0/game/RETROARCH/`. It has the original PSX-Place CE launcher
(`EBOOT.BIN` and `PARAM.SFO`), nine retained PS3 SELF cores, the custom
CGEMU342 FCEUmm SELF with the RSX bilinear fix, and the actual RGUI/video/
controller configuration. The input archive, game saves, and assembled PKG
**are not committed to this public repository**.

## What's in the personal build

- Exactly nine cores already installed in the archive:
  `dosbox_svn`, `fceumm`, `genesis_plus_gx`,
  `genesis_plus_gx_wide`, `mame2003_midway`, `mame2003_plus`,
  `snes9x2005_plus`, `snes9x2010`, `snes9x`.
- Every present CFG and OPT from the working installation copied as-is,
  **except one option**: `fceumm_palette = "default"` is changed to
  `fceumm_palette = "custom"`.
- The **unaltered default PC FCEUX palette**, supplied by upstream
  [TASEmulators/fceux](https://github.com/TASEmulators/fceux/blob/master/output/palettes/FCEUX.pal),
  is installed as `USRDIR/system/nes.pal` (the file name required by
  FCEUmm). Palette SHA-256:
  `bbb0355bcadc4be771efeb81930b09b17d97dcb8c70167a652902a789158c5f8`.
- User-configured 4:3, bilinear/RSX, Turbo A+B, and No Sprite Limit remain.
- RGUI + branding and common assets, original EBOOT/PARAM/ICON/PIC and
  overlays/shaders are retained. Old XMB/Ozone/NX themes, wallpapers, unrelated
  core info, unrelated content databases and stale cache are omitted.
  Selected NES/SNES/Sega/DOS/MAME databases are retained.
- **Personal NES .srm saves are excluded from installer** to avoid overwriting
  existing save data. Preserve them separately from the original full ZIP.

The locally generated non-finalized HEN test PKG from this exact snapshot was
`120,078,368` bytes (114.52 MiB) with 2,546 PKG entries. Its SHA-256 was
`e151e2d510955b5402dda03debc62902b144fc76b8ab4465a590bc38e017ca86`.
The package was verified by decrypting and comparing 86 extracted payloads,
including the app EBOOT, FCEUmm SELF, CFG/OPT and `nes.pal`, plus all file
index names. **This is not equivalent to validating installation on a real PS3.**

## Rebuild privately on a computer

Download the original FCEUX palette above and save it as `FCEUX.pal`.
Check that its SHA-256 matches.

```bash
python3 scripts/stage_working_ce_archive.py RETROARCH.zip FCEUX.pal ./staged-ce
python3 scripts/pack_ce_debug.py ./staged-ce \
  RetroArch_CGEMU342_FCEUX_Custom_HEN.pkg \
  UP0001-RETROARCH_00-0000111122223333
```

The PS3 PKG is a **non-finalized homebrew/HEN-test package**, not a
Sony-signed retail release. Console installability needs to be validated on
the target PS3 HEN system. The package uses title ID `RETROARCH` and may
overwrite the existing installation. Installing over an existing title can
leave old files behind (including previously installed unused cores), so
do not expect an in-place install to remove everything old.

**Before installing:** make a separate full backup of the working
`/dev_hdd0/game/RETROARCH/`, including `savefiles`, and keep the old
`fceumm_libretro_ps3.SELF`. Test the new installer only when recovery from
the backup is possible. Avoid publishing the user's copyrighted homebrew
package contents or personal configuration on public GitHub.
