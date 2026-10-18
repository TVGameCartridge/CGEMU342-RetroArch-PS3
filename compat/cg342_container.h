/*
 * CGEMU342 embedded ROM directory reader for the PS3 FCEUmm port.
 * Format shared with CGEMU342-NESemu-Android/CG342Container.h.
 * Copyright (C) 2026 CGEMU342 PS3 integration contributors.
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Parser only. It does not emulate multicart hardware, and only activates
 * for ROM files with the explicit CGEMU342 footer and valid directory.
 */
#ifndef CG342_CONTAINER_H
#define CG342_CONTAINER_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define CG342_MAX_ROM_SIZE ((size_t)128 * 1024 * 1024)
#define CG342_FOOTER_SIZE ((size_t)48)
#define CG342_ENTRY_SIZE  ((size_t)288)
#define CG342_MAX_ENTRIES 4096u

typedef struct {
   uint32_t count;
   uint64_t dir_start;
} cg342_index_t;

typedef struct {
   uint64_t offset;
   uint64_t size;
   uint16_t format;
   uint16_t mapper;
   uint16_t submapper;
   char title[129];
} cg342_entry_t;

static uint16_t cg342_u16(const uint8_t *p)
{
   return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t cg342_u32(const uint8_t *p)
{
   return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
          ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint64_t cg342_u64(const uint8_t *p)
{
   return (uint64_t)cg342_u32(p) | ((uint64_t)cg342_u32(p + 4) << 32);
}

static int cg342_range(uint64_t start, uint64_t length, uint64_t limit)
{
   return start <= limit && length <= limit - start;
}

static int cg342_entry_at(const uint8_t *rom, size_t size,
      const cg342_index_t *index, uint32_t id, cg342_entry_t *entry)
{
   uint64_t position;
   const uint8_t *p;
   unsigned i;
   int is_nes;
   int is_unif;

   if (!rom || !index || !entry || id >= index->count)
      return 0;
   position = index->dir_start + (uint64_t)id * CG342_ENTRY_SIZE;
   if (!cg342_range(position, CG342_ENTRY_SIZE, size - CG342_FOOTER_SIZE))
      return 0;

   p = rom + (size_t)position;
   entry->offset    = cg342_u64(p);
   entry->size      = cg342_u64(p + 8);
   entry->format    = cg342_u16(p + 16);
   entry->mapper    = cg342_u16(p + 18);
   entry->submapper = cg342_u16(p + 20);
   if ((entry->format != 1 && entry->format != 2 && entry->format != 3) ||
       entry->size < 16 ||
       !cg342_range(entry->offset, entry->size, index->dir_start))
      return 0;

   is_nes  = !memcmp(rom + (size_t)entry->offset, "NES\x1a", 4);
   is_unif = !memcmp(rom + (size_t)entry->offset, "UNIF", 4);
   if (((entry->format == 1 || entry->format == 2) && !is_nes) ||
       (entry->format == 3 && !is_unif))
      return 0;

   for (i = 0; i < 128; ++i)
   {
      char ch = (char)p[24 + i];
      if (!ch || ch == '/' || ch == '\\' || ch == ':' ||
          ch == '*' || ch == '?' || ch == '"' || ch == '<' ||
          ch == '>' || ch == '|' || ch == '\n' || ch == '\r' ||
          (unsigned char)ch < 32)
         ch = '_';
      entry->title[i] = ch;
   }
   entry->title[128] = '\0';
   return 1;
}

static int cg342_parse(const uint8_t *rom, size_t size, cg342_index_t *index)
{
   const uint8_t *footer;
   uint64_t dir_start, dir_size;
   uint32_t count, id;
   cg342_index_t tmp;
   cg342_entry_t entry;

   if (!rom || !index || size < CG342_FOOTER_SIZE ||
       size > CG342_MAX_ROM_SIZE)
      return 0;

   footer = rom + size - CG342_FOOTER_SIZE;
   if (memcmp(footer, "CGEMU342", 8) != 0 || cg342_u32(footer + 8) != 1)
      return 0;

   count = cg342_u32(footer + 12);
   dir_start = cg342_u64(footer + 16);
   dir_size  = cg342_u64(footer + 24);
   if (!count || count > CG342_MAX_ENTRIES ||
       dir_size < (uint64_t)count * CG342_ENTRY_SIZE ||
       !cg342_range(dir_start, dir_size, size - CG342_FOOTER_SIZE))
      return 0;

   tmp.count = count;
   tmp.dir_start = dir_start;
   for (id = 0; id < count; ++id)
      if (!cg342_entry_at(rom, size, &tmp, id, &entry))
         return 0;

   *index = tmp;
   return 1;
}

#endif /* CG342_CONTAINER_H */
