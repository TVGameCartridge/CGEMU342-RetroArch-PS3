# CGEMU342 RetroArch PS3

NES / Famicom core development for **PlayStation 3 with HEN**, targeting the
user-supplied **RetroArch PSX-Place Community Edition Beta 4** package.

**Status: Stage 1 — PS3 FCEUmm core build.** This repository does **not yet**
generate an installable `.pkg`. The output of the current GitHub Actions
workflow is `fceumm_libretro_psl1ght.a`, a static PowerPC core library.
This library must be integrated with a compatible RetroArch PS3 frontend
before a HEN-installable application can be packaged and tested.

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
Download the `PS3-FCEUmm-static-core-...` artifact after a successful run.
**Do not try to install this `.a` library on the PS3**.

The workflow:
1. Checks out this repository and upstream
   [libretro-fceumm](https://github.com/libretro/libretro-fceumm).
2. Checks mapper registration and optionally substitutes BMC-8157 mapping.
3. Cross-compiles the FCEUmm static core with a
   [PSL1GHT / PS3DEV toolchain image](https://github.com/02900/ps3-toolchain).
4. Uploads the compiled `.a` and the upstream revision for future integration.

## Next steps

- Confirm this static PS3 build works in Actions.
- Identify the exact bundled core/frontend ABI and original build toolchain of
  **RetroArch PSX-Place CE Beta 4**.
- Integrate the core into a compatible frontend and package it as a PS3 `.pkg`.
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
