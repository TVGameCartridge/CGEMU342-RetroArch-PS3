# CGEMU342 RetroArch PS3

NES / Famicom core development for **PlayStation 3 with HEN**, targeting the
user-supplied **RetroArch PSX-Place Community Edition Beta 4** package.

**Status: CGEMU342 v3 HEN test PKG confirmed working on real PS3 hardware
(2026-10-18).** The user confirmed that the standalone PSL1GHT RetroArch
PKG installs, launches and plays ordinary NES ROMs. On v1/v2 the CGEMU342
multi-ROM selector appeared but launching a child game gave a black screen.
After the v3 embedded-ROM handoff was added, the user reported that
**55 in 1 Street Fighter**, **292 in 1**, and **146 in 1 Infinity**
all work on PS3 HEN.

**Tested binary:** [PS3-HEN-FCEUmm-CG342-Test-PKG-v3-8157,
GitHub Actions run 39138485196](https://github.com/TVGameCartridge/CGEMU342-RetroArch-PS3/actions/runs/39138485196),
built from commit `96ff47ee909e1f40dcf9598090ef9063b246b7dc`.
This is a user-reported hardware result, not exhaustive verification of
every game, mapper or feature. The Actions artifact has a limited retention
period. This is NOT yet a modified PSX-Place CE Beta 4 release.

## Mappers

The libretro/FCEUmm upstream mapper table includes:

| Mapper | Meaning / note |
| --- | --- |
| 264 | Yoko / Master Fighter VI |
| 287 | BMC-411120-C |
| 301 | **Two incompatible implementations** (see below) |
| 315 | BMC-830134C |
| 344 | GN-26 |
| 358 | YY860606C |
| 393 | BMC-820720C |
| 395 | Realtec 8210 |

Our earlier Android [CGEMU342-NESemu-Android](https://github.com/TVGameCartridge/CGEMU342-NESemu-Android)
project assigned mapper 301 to the older **BMC-8157** behavior, while
upstream FCEUmm implements mapper 301 as **K-3003**.
Neither definition can safely be assumed to match every ROM.

The Actions workflow has a **mapper301_mode** option:
- `8157` (default for this project): replace FCEUmm's `src/boards/301.c`
  with `compat/mapper301_8157.c` adapted from CaH4e3's GPL FCEUX code.
  This may break games that need upstream K-3003 mapper 301.
- `upstream`: preserve FCEUmm's own K-3003 implementation.

All other listed mapper IDs use **upstream FCEUmm source**, not copies of
the Android-specific C++ files. Tests with real NES ROMs are still required;
compilation alone does not establish mapper correctness.

## Build on GitHub

Open **Actions > Build PS3 FCEUmm core > Run workflow**. Choose the 301
mode if needed. Builds also start automatically when `main` changes.
Download the `PS3-CG342-FCEUmm-static-core-...` artifact after a successful run.
**Do not try to install this `.a` library on the PS3**.

The workflow:
1. Checks out this repository and upstream
   [libretro-fceumm](https://github.com/libretro/libretro-fceumm).
2. Checks mapper registration and optionally substitutes BMC-8157 mapping.
3. Cross-compiles the FCEUmm static core with a
   [PSL1GHT / PS3DEV toolchain image](https://github.com/02900/ps3-toolchain).
4. Uploads the compiled `.a` and the upstream revision for future integration.

## Experimental HEN-installable PKG

A second workflow, **Actions > Build PS3 HEN test PKG**, builds
upstream RetroArch's PSL1GHT application linked with the modified FCEUmm
static core. It uses upstream RetroArch's package scripts to
create `retroarch_psl1ght.pkg` (if the entire build succeeds).

**Test PKG v2** added `USRDIR/info/CORE.info` from upstream FCEUmm.
**Test PKG v3** also patches FCEUmm to read the CGEMU342 directory at the
end of a container ROM and respond to the NES RAM handshake
(`$07F0/$07F1` = selected child ID, `$07F2` = `$A5`). After each
frame, it loads the selected embedded NES/UNIF child image, and RetroArch's
reset command tries to return to the CGEMU342 launcher.
The validated parser uses the format shared with the Android project and
has synthetic positive/negative tests. No copyrighted ROMs are included.
The user subsequently verified that all three CGEMU342 collections
listed above launch games successfully on PS3 HEN using the v3 PKG.
This is hardware evidence for those collections, not a guarantee for
untested files or other mappers. The package does not include the ROM
database required by automatic **Import Content** scanning.
Try **Load Content > /dev_usb000/ > example.nes**. USB storage may also
appear as `/dev_usb001/` depending on the port. Selecting a ROM
must be verified on real hardware; a green Actions build is not
proof that the menu or game loading works.

**This is NOT a modification of the provided PSX-Place Community Edition
Beta 4 package.** It is a separate experimental homebrew application.
PSX-Place CE uses title ID `SSNE10000`; upstream RetroArch PSL1GHT
uses `SSNE10001`. It could overwrite an existing PS3 app with the
same `SSNE10001` title ID. Never install blindly; back up PS3 data
and test carefully on HEN-enabled hardware.

Normal NES ROMs and the three named CGEMU342 multi-ROM collections
have been confirmed working on PS3 HEN by the user; reset-to-menu,
savestates, every included title and remaining mapper-specific games
have not all been independently tested.
The PS3 PSL1GHT menu initially uses circle (O) to confirm and cross (X)
to go back, as confirmed by the user. Mapper-301 `8157` is not a
universal mapper fix.

## Original PSX-Place CE Beta 4 package integration

The original 238 MB `RetroArch_Psx-Place.pkg` was **actually inspected and
decrypted** (not inferred from upstream repository defaults):

- Metadata `TITLE_ID`: **`RETROARCH`**, not `SSNE10000`.
- Content ID: `UP0001-RETROARCH_00-0000111122223333`.
- Original bundled core: `USRDIR/cores/2048_libretro_ps3.SELF`.
- The original includes `USRDIR/info/fceumm_libretro.info` but **no**
  FCEUmm executable; it must be added.
- 7584 package entries. Existing assets/configs and the 2048 core must
  not be removed.

**Actions > Build PSX-Place CE CGEMU342 add-on** creates
`fceumm_libretro_ps3.SELF` using the tested CGEMU342 v3 core code, but
rebases the PSL1GHT frontend's hardcoded PS3 runtime root to `RETROARCH`.
The output archive contains only:

```text
USRDIR/cores/fceumm_libretro_ps3.SELF
USRDIR/info/fceumm_libretro.info
```

For a reversible hardware compatibility test: back up the original CE
config and installed files; use multiMAN to copy these **files** under
`/dev_hdd0/game/RETROARCH/USRDIR/` (the `USRDIR` directory from
the add-on corresponds to the installed app's `USRDIR`). Do not replace
`EBOOT.BIN`, `2048_libretro_ps3.SELF` or the PS3 system installation.
This is **not a PKG** and should **not** be installed through Package
Manager. Compatibility of the PSL1GHT-built core with the existing
Sony-SDK-built CE launcher **has not been proven** yet.

The optional `scripts/stage_original_ce.py` safely stages a copy of the
user-supplied original retail PKG together with the new core. It does not
overwrite the original source file, repack a signed PKG or publish copyrighted
game files. This script is for local packaging work, not for installing.

## Next steps

- Preserve the successful v3 test package and source revision; verify
  reset-to-menu, savestates and additional child games separately.
- Identify the exact bundled core/frontend ABI and original build toolchain of
  **RetroArch PSX-Place CE Beta 4**.
- Eventually integrate the custom NES core into the original PSX-Place CE Beta 4
  frontend without losing its other built-in emulators.
- Test with HEN enabled on real hardware: Master Fighter VI (264),
  301 multicarts, and the remaining mapper-specific ROMs.
- Back up any existing PS3 RetroArch configuration, saves, and original `.pkg`
  before installing a test build.

**Important:** PSX-Place CE's older Sony-SDK-oriented build system differs
from the open PSL1GHT target. Building a PSL1GHT static core does not
automatically create a compatible PSX-Place CE replacement package.

Source licensing: upstream FCEUmm and the BMC-8157 adapter are
GPL-2.0-or-later; preserve copyright notices and provide source for releases.

This repository is separate from the Android project. No Android files or
workflows are modified by PS3 development.
