#!/usr/bin/env python3
"""Integrate the CGEMU342 launcher/embedded-ROM selector into libretro FCEUmm.

This is not a mapper substitution. A CGEMU342 launcher communicates a selected
directory entry via NES RAM $07F0/$07F1 (little-endian ID) and $07F2 = $A5.
The libretro frontend swaps to the embedded child ROM after the current frame,
then a RetroArch reset returns to the launcher.

Ported from CGEMU342-NESemu-Android/apply_cg342.py. GPL-3.0-or-later.
"""
from pathlib import Path
import argparse
import shutil


RUNTIME = r'''
/* CGEMU342 integration - only active for a validated container footer. */
static uint8_t *cg342_container;
static size_t cg342_container_size;
static cg342_index_t cg342_directory;
static int cg342_child_active;
static char cg342_parent_path[2048];

static void cg342_clear(void)
{
   free(cg342_container);
   cg342_container = NULL;
   cg342_container_size = 0;
   cg342_child_active = 0;
   cg342_parent_path[0] = '\0';
   memset(&cg342_directory, 0, sizeof(cg342_directory));
}

/* Avoid allocating a second ROM copy for ordinary .nes content. */
static void cg342_probe(const char *path, const uint8_t *data, size_t size)
{
   uint8_t *copy = NULL;
   size_t copy_size = 0;
   cg342_index_t directory;

   cg342_clear();

   if (data && size >= CG342_FOOTER_SIZE && size <= CG342_MAX_ROM_SIZE)
   {
      if (memcmp(data + size - CG342_FOOTER_SIZE, "CGEMU342", 8))
         return;
      copy = (uint8_t*)malloc(size);
      if (!copy)
         return;
      memcpy(copy, data, size);
      copy_size = size;
   }
   else if (path && *path)
   {
      RFILE *file = filestream_open(path, RETRO_VFS_FILE_ACCESS_READ,
            RETRO_VFS_FILE_ACCESS_HINT_NONE);
      int64_t length;
      uint8_t footer[CG342_FOOTER_SIZE];

      if (!file)
         return;

      length = filestream_get_size(file);
      if (length >= (int64_t)CG342_FOOTER_SIZE &&
          length <= (int64_t)CG342_MAX_ROM_SIZE &&
          filestream_seek(file, length - (int64_t)CG342_FOOTER_SIZE,
                SEEK_SET) >= 0 &&
          filestream_read(file, footer, sizeof(footer)) ==
                (int64_t)sizeof(footer) &&
          !memcmp(footer, "CGEMU342", 8) &&
          filestream_seek(file, 0, SEEK_SET) >= 0)
      {
         copy = (uint8_t*)malloc((size_t)length);
         if (copy && filestream_read(file, copy, length) == length)
            copy_size = (size_t)length;
      }
      filestream_close(file);
   }

   if (!copy)
      return;
   if (!copy_size || !cg342_parse(copy, copy_size, &directory))
   {
      free(copy);
      return;
   }

   cg342_container = copy;
   cg342_container_size = copy_size;
   cg342_directory = directory;
   if (path)
      strlcpy(cg342_parent_path, path, sizeof(cg342_parent_path));
   FCEUD_Message("[CGEMU342] Validated embedded ROM directory.");
}

/* Loading a child is different from a normal frontend load: we must restore
 * input callbacks and savestate registrations for the new game. */
static int cg342_load_image(const char *name, const uint8_t *data, size_t size)
{
   unsigned port;
   if (!FCEUI_LoadGame(name, data, size, frontend_post_load_init))
      return 0;

   serialize_size = 0;
   memset(turbo_button_toggle, 0, sizeof(turbo_button_toggle));
   AddExState(turbo_button_toggle, sizeof(turbo_button_toggle), 0, "TBTG");

   for (port = 0; port < MAX_PORTS; ++port)
   {
      FCEUI_SetInput(port, SI_GAMEPAD, &nes_input.JSReturn, 0);
      nes_input.type[port] = RETRO_DEVICE_JOYPAD;
   }
   FCEUI_DisableFourScore(1);
   nes_input.enable_4player = false;

   systemRegion = (dendy << 1) | (retro_get_region() & 1);
   ResetPalette();
   check_variables(true);
   return 1;
}

static void cg342_frame_end(void)
{
   uint32_t game_id;
   cg342_entry_t entry;
   char filename[192];

   if (!cg342_container || cg342_child_active || !GameInfo ||
       RAM[0x7F2] != 0xA5)
      return;

   game_id = (uint32_t)RAM[0x7F0] | ((uint32_t)RAM[0x7F1] << 8);
   RAM[0x7F2] = 0;
   if (!cg342_entry_at(cg342_container, cg342_container_size,
          &cg342_directory, game_id, &entry))
   {
      FCEUD_Message("[CGEMU342] Invalid child ROM index.");
      return;
   }

   snprintf(filename, sizeof(filename), "CG342-%u-%.110s.%s",
         (unsigned)game_id, entry.title, entry.format == 3 ? "unf" : "nes");

   if (cg342_load_image(filename,
          cg342_container + (size_t)entry.offset, (size_t)entry.size))
   {
      cg342_child_active = 1;
      FCEUD_Message("[CGEMU342] Embedded game loaded.");
   }
   else
   {
      FCEUD_Message("[CGEMU342] Child failed; restoring selection menu.");
      if (cg342_load_image(cg342_parent_path,
             cg342_container, cg342_container_size))
         cg342_child_active = 0;
   }
}

static int cg342_return_to_menu(void)
{
   if (!cg342_container || !cg342_child_active)
      return 0;

   if (!cg342_load_image(cg342_parent_path,
          cg342_container, cg342_container_size))
      return 0;

   cg342_child_active = 0;
   return 1;
}
'''


def replace_exact(source: str, old: str, new: str, desc: str) -> str:
    hits = source.count(old)
    if hits != 1:
        raise SystemExit(f"Cannot patch {desc}: expected 1 anchor, got {hits}")
    return source.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fceumm", type=Path)
    args = parser.parse_args()
    root = args.fceumm.resolve()
    libretro = root / "src/drivers/libretro/libretro.c"
    if not libretro.is_file():
        parser.error(f"File missing: {libretro}")
    source = libretro.read_text(encoding="utf-8")
    if "cg342_frame_end" in source:
        parser.error("CGEMU342 hook already exists; refusing double patch")

    source = replace_exact(source,
        '#include "../../video.h"\n',
        '#include "../../video.h"\n#include "cg342_container.h"\n',
        "parser include")

    source = replace_exact(source,
        'void retro_set_environment(retro_environment_t cb)\n',
        RUNTIME + '\nvoid retro_set_environment(retro_environment_t cb)\n',
        "runtime implementation")

    source = replace_exact(source,
        'void retro_deinit (void)\n{\n   FCEUI_CloseGame();',
        'void retro_deinit (void)\n{\n   FCEUI_CloseGame();\n   cg342_clear();',
        "deinit cleanup")

    source = replace_exact(source,
        '   memset(turbo_button_toggle, 0, sizeof(turbo_button_toggle));\n   ResetNES();',
        '   memset(turbo_button_toggle, 0, sizeof(turbo_button_toggle));\n'
        '   if (cg342_return_to_menu())\n      return;\n   ResetNES();',
        "return to menu on reset")

    source = replace_exact(source,
        '   audio_batch_cb((const int16_t*)sound, ssize);\n}',
        '   audio_batch_cb((const int16_t*)sound, ssize);\n'
        '   cg342_frame_end();\n}',
        "ROM selection after finished frame")

    source = replace_exact(source,
        '   /* initialize some of the default variables */',
        '   /* Cache CGEMU342 directory, if present; ordinary ROMs are unchanged. */\n'
        '   cg342_probe(content_path, content_data, content_size);\n\n'
        '   /* initialize some of the default variables */',
        "container detection in load")

    source = replace_exact(source,
        '      fceu_video_out = NULL;\n#if 0',
        '      fceu_video_out = NULL;\n      cg342_clear();\n#if 0',
        "load failure cleanup")

    source = replace_exact(source,
        'void retro_unload_game(void)\n{',
        'void retro_unload_game(void)\n{\n   cg342_clear();',
        "unload cleanup")

    libretro.write_text(source, encoding="utf-8")
    src = Path(__file__).resolve().parents[1] / "compat/cg342_container.h"
    dst = root / "src/drivers/libretro/cg342_container.h"
    shutil.copyfile(src, dst)
    print("CGEMU342 libretro runtime patched: directory, $07F2 selection, reset-to-menu")
    print("This verifies integration only; real multi-ROM gameplay requires HEN testing.")


if __name__ == "__main__":
    main()
