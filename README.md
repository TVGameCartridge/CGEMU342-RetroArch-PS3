# CGEMU342 RetroArch PS3

NES / Famicom core development for **PlayStation 3 with HEN**, targeting the
user-supplied **RetroArch PSX-Place Community Edition Beta 4** package.

**Status: experimental PS3 HEN test PKG and standalone core.**
The user has confirmed that the standalone PSL1GHT RetroArch PKG installs
and launches on HEN, and normal single-game NES ROMs run. CGEMU342
multi-ROM cartridges displayed their selector menu but selecting a child
game resulted in a black screen on v1/v2. The v3 source implements the
missing CGEMU342 embedded ROM selection; hardware testing is still needed.
This is NOT yet a modified PSX-Place CE Beta 4 release.

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
A successful Actions build does **not** prove that any of the user's
55-in-1 Street Fighter / 292-in-1 / 146-in-1 Infinity files use that
exact container layout or that the child image works on PS3. It does not
include the ROM database required by automatic **Import Content** scanning.
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

Normal NES game loading is hardware-tested by the user. The CGEMU342
container handler is new and remains unverified on hardware.
The PS3 PSL1GHT menu initially uses circle (O) to confirm and cross (X)
to go back, as confirmed by the user. Mapper-301 `8157` is not a
universal mapper fix.

## Next steps

- Build and test CGEMU342 v3 on HEN hardware, including all three
  failing multi-ROM collections; verify child selection and reset-to-menu.
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
