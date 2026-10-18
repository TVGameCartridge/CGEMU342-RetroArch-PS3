/* Synthetic parser tests: no copyrighted ROM data required.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../compat/cg342_container.h"

#define DIR_START 96u
#define COUNT 2u
#define ROM_SIZE (DIR_START + COUNT * CG342_ENTRY_SIZE + CG342_FOOTER_SIZE)

static void put16(uint8_t *p, uint16_t x) {
   p[0] = (uint8_t)x; p[1] = (uint8_t)(x >> 8);
}
static void put32(uint8_t *p, uint32_t x) {
   unsigned i; for (i = 0; i < 4; ++i) p[i] = (uint8_t)(x >> (8 * i));
}
static void put64(uint8_t *p, uint64_t x) {
   put32(p, (uint32_t)x); put32(p + 4, (uint32_t)(x >> 32));
}
int main(void) {
   uint8_t rom[ROM_SIZE] = {0};
   uint8_t *footer = rom + ROM_SIZE - CG342_FOOTER_SIZE;
   cg342_index_t idx;
   cg342_entry_t entry;

   memcpy(rom, "NES\x1a", 4);
   memcpy(rom + 48, "NES\x1a", 4);
   put64(rom + DIR_START, 0);
   put64(rom + DIR_START + 8, 48);
   put16(rom + DIR_START + 16, 1);
   put16(rom + DIR_START + 18, 264);
   memcpy(rom + DIR_START + 24, "55 in 1 child", 13);

   put64(rom + DIR_START + CG342_ENTRY_SIZE, 48);
   put64(rom + DIR_START + CG342_ENTRY_SIZE + 8, 48);
   put16(rom + DIR_START + CG342_ENTRY_SIZE + 16, 2);
   put16(rom + DIR_START + CG342_ENTRY_SIZE + 18, 342);
   memcpy(rom + DIR_START + CG342_ENTRY_SIZE + 24, "292 in 1 child", 14);

   memcpy(footer, "CGEMU342", 8);
   put32(footer + 8, 1);
   put32(footer + 12, COUNT);
   put64(footer + 16, DIR_START);
   put64(footer + 24, COUNT * CG342_ENTRY_SIZE);

   assert(cg342_parse(rom, sizeof(rom), &idx));
   assert(idx.count == COUNT);
   assert(cg342_entry_at(rom, sizeof(rom), &idx, 0, &entry));
   assert(entry.offset == 0 && entry.size == 48 && entry.mapper == 264);
   assert(!strcmp(entry.title, "55 in 1 child"));
   assert(cg342_entry_at(rom, sizeof(rom), &idx, 1, &entry));
   assert(entry.mapper == 342 && entry.format == 2);
   assert(!cg342_entry_at(rom, sizeof(rom), &idx, 2, &entry));

   footer[8] = 2;
   assert(!cg342_parse(rom, sizeof(rom), &idx));
   footer[8] = 1;

   put32(footer + 12, 0);
   assert(!cg342_parse(rom, sizeof(rom), &idx));
   put32(footer + 12, COUNT);

   put64(rom + DIR_START + 8, 123456);
   assert(!cg342_parse(rom, sizeof(rom), &idx));
   put64(rom + DIR_START + 8, 48);

   memcpy(rom + 48, "BAD!", 4);
   assert(!cg342_parse(rom, sizeof(rom), &idx));
   memcpy(rom + 48, "NES\x1a", 4);

   put64(footer + 16, 0xffffffffffffffffULL);
   assert(!cg342_parse(rom, sizeof(rom), &idx));
   put64(footer + 16, DIR_START);

   assert(cg342_parse(rom, sizeof(rom), &idx));
   puts("CGEMU342 parser: synthetic positive/negative cases passed");
   return 0;
}
