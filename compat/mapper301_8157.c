/* FCE Ultra / FCEUmm - Mapper 301 BMC-8157 compatibility variant
 *
 * Based on NES.emu/src/fceu/boards/8157.cpp (original author CaH4e3, 2005).
 * Copyright (C) 2005 CaH4e3
 *
 * GPL-2.0-or-later. See upstream FCEUmm licensing.
 *
 * IMPORTANT: Installing this source replaces the upstream mapper 301 K-3003
 * implementation. This is an opt-in compatibility mode, not a universal fix.
 */
#include "mapinc.h"

static uint16_t cmdreg;
static uint8_t reset_counter;

static SFORMAT state_regs[] = {
    { &reset_counter, 1, "REST" },
    { &cmdreg, 2, "CREG" },
    { 0 }
};

static void sync_mapper301_8157(void)
{
    uint32_t base = ((cmdreg & 0x060) | ((cmdreg & 0x100) >> 1)) >> 2;
    uint32_t bank = (cmdreg & 0x01C) >> 2;
    uint32_t last_bank = (cmdreg & 0x200) ? 7 : ((cmdreg & 0x80) ? bank : 0);

    if (PRGptr[1]) {
        setprg16r(base >> 3, 0x8000, bank);
        setprg16r(base >> 3, 0xC000, last_bank);
    } else {
        setprg16(0x8000, base | bank);
        setprg16(0xC000, base | last_bank);
    }
    setmirror(((cmdreg & 2) >> 1) ^ 1);
}

static DECLFR(read_8157)
{
    if ((cmdreg & 0x100) && (PRGsize[0] < (1024 * 1024))) {
        A = (A & 0xFFF0) + reset_counter;
    }
    return CartBR(A);
}

static DECLFW(write_8157)
{
    cmdreg = A;
    sync_mapper301_8157();
}

static void power_8157(void)
{
    setchr8(0);
    SetWriteHandler(0x8000, 0xFFFF, write_8157);
    SetReadHandler(0x8000, 0xFFFF, read_8157);
    cmdreg = 0;
    reset_counter = 0;
    sync_mapper301_8157();
}

static void reset_8157(void)
{
    /* Preserve the source's reset behavior for compatibility testing. */
    cmdreg = 0;
    reset_counter = 0;
    reset_counter++;
    reset_counter &= 0x1F;
    sync_mapper301_8157();
}

static void restore_8157(int version)
{
    (void)version;
    sync_mapper301_8157();
}

void Mapper301_Init(CartInfo *info)
{
    info->Power = power_8157;
    info->Reset = reset_8157;
    GameStateRestore = restore_8157;
    AddExState(state_regs, ~0, 0, 0);
}
