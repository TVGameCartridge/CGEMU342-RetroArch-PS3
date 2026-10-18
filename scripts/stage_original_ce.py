#!/usr/bin/env python3
"""Stage the user-supplied PSX-Place CE Beta 4 PKG without deleting its contents.

Requires: pip install cryptography
Usage: python3 scripts/stage_original_ce.py original.pkg PS3_CORE.SELF stage-dir

Does not build a PKG. The output is a staged directory for a developer
to repackage with a working PS3 homebrew package builder. The existing
original executable, assets, settings and core files are preserved.
"""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import hashlib
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY = bytes.fromhex("2e7b71d7c9c9a14ea3221f188828b8f8")
HEADER = struct.Struct(">4sHHIIIIQQQ48s16s16s")
ITEM = struct.Struct(">IIQQII")
EXPECTED_TITLE = "RETROARCH"
EXPECTED_CONTENT = "UP0001-RETROARCH_00-0000111122223333"
NEW_CORE = "USRDIR/cores/fceumm_libretro_ps3.SELF"


def decrypt_region(f, header, offset: int, length: int) -> bytes:
    if length == 0:
        return b""
    block_start = offset & ~15
    prefix = offset - block_start
    f.seek(header["data_start"] + block_start)
    raw = f.read(prefix + length)
    if len(raw) != prefix + length:
        raise ValueError("Truncated encrypted package data")
    if header["revision"] == 0x8000:
        counter = (int.from_bytes(header["riv"], "big") +
                   block_start // 16) % (1 << 128)
        cipher = Cipher(algorithms.AES(KEY), modes.CTR(counter.to_bytes(16, "big")))
        d = cipher.decryptor()
        plain = d.update(raw) + d.finalize()
    elif header["revision"] == 0:
        plain = bytearray()
        qa = header["digest"]
        for pos in range(0, len(raw), 16):
            block_num = block_start // 16 + pos // 16
            key = qa[:8] * 2 + qa[8:] * 2 + bytes(24) + block_num.to_bytes(8, "big")
            stream = hashlib.sha1(key).digest()[:16]
            plain += bytes(a ^ b for a, b in zip(raw[pos:pos+16], stream))
    else:
        raise ValueError("Unsupported PS3 PKG revision")
    return plain[prefix:prefix+length]


def read_header(f):
    raw = f.read(HEADER.size)
    if len(raw) != HEADER.size:
        raise ValueError("Not a PKG")
    (magic, revision, pkg_type, _, _, _, count, total,
     data_start, data_len, cid, digest, riv) = HEADER.unpack(raw)
    if magic != b"\x7fPKG" or pkg_type != 1 or revision not in (0, 0x8000):
        raise ValueError("Not a supported PS3 PKG")
    cid = cid.rstrip(b"\0").decode("ascii")
    if cid != EXPECTED_CONTENT:
        raise ValueError(f"Wrong original PKG: content ID {cid!r}")
    f.seek(0, 2)
    actual_size = f.tell()
    if not (0 < count <= 50000 and actual_size >= total and
            data_start + data_len <= actual_size and count * ITEM.size < data_len):
        raise ValueError("Invalid PKG header bounds")
    return {"revision": revision, "count": count, "data_start": data_start,
            "data_len": data_len, "digest": digest, "riv": riv, "content_id": cid}


def entries(f, header):
    table = decrypt_region(f, header, 0, header["count"] * ITEM.size)
    rows = [ITEM.unpack_from(table, i * ITEM.size) for i in range(header["count"])]
    # Read the names in one block: avoids thousands of independent AES initialisations.
    end_of_names = max((no + ns for no, ns, _, _, _, _ in rows), default=0)
    if end_of_names > header["data_len"] or end_of_names > 32_000_000:
        raise ValueError("Invalid file names region")
    names = decrypt_region(f, header, 0, end_of_names)
    seen = set()
    for no, ns, off, size, flags, _ in rows:
        if ns == 0 or ns > 2048 or no + ns > end_of_names:
            raise ValueError("Invalid entry name length")
        raw = names[no:no+ns]
        if b"\0" in raw:
            raise ValueError("Embedded NUL in package name")
        name = raw.decode("utf-8")
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or
            "\\" in name or ":" in name or not name.startswith(("USRDIR/", "PARAM.SFO", "ICON0.PNG", "PIC1.PNG", "PS3LOGO.DAT"))):
            raise ValueError(f"Unsafe package path {name!r}")
        if name in seen:
            raise ValueError(f"Duplicate archive name {name!r}")
        seen.add(name)
        if off + size > header["data_len"]:
            raise ValueError(f"Invalid data range for {name}")
        yield name, off, size, flags


def sfo_title_id(raw):
    if len(raw) < 20 or raw[:4] != b"\0PSF":
        raise ValueError("Missing PARAM.SFO")
    key_off, data_off, count = struct.unpack_from("<III", raw, 8)
    if count > 300:
        raise ValueError("Invalid PARAM.SFO")
    for i in range(count):
        key_pos, typ, length, _, val_pos = struct.unpack_from("<HHIII", raw, 20+i*16)
        start = key_off + key_pos
        end = raw.find(b"\0", start)
        if end < 0:
            raise ValueError("Malformed SFO keys")
        if raw[start:end] == b"TITLE_ID":
            return raw[data_off + val_pos:data_off + val_pos+length].split(b"\0", 1)[0].decode("ascii")
    raise ValueError("Missing PARAM.SFO TITLE_ID")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("original_pkg", type=Path)
    parser.add_argument("new_core_self", type=Path)
    parser.add_argument("stage", type=Path)
    args = parser.parse_args()
    core = args.new_core_self.resolve()
    if not core.is_file() or core.stat().st_size < 100_000:
        parser.error("Expected compiled nonempty PS3 FCEUmm SELF core")

    output = args.stage.resolve()
    if output.exists():
        parser.error("Staging folder exists; refusing to overwrite any files")
    # Validate the original PKG before touching the destination.
    with args.original_pkg.open("rb") as src:
        header = read_header(src)
        listing = list(entries(src, header))
        names = {x[0] for x in listing}
        if NEW_CORE in names:
            parser.error("Original already contains CGEMU342 core; refusing overwrite")
        if "USRDIR/cores/2048_libretro_ps3.SELF" not in names:
            parser.error("This is not the expected original CE package (2048 core missing)")
        sfo = next(((off, size) for name, off, size, _ in listing
                    if name == "PARAM.SFO"), None)
        if not sfo or sfo_title_id(decrypt_region(src, header, *sfo)) != EXPECTED_TITLE:
            parser.error("Unexpected PARAM.SFO TITLE_ID")
        print("Original CE package verified:", header["content_id"], len(listing), "items")
        output.mkdir(parents=True)
        for name, off, size, flags in listing:
            target = output / name
            if flags & 0xff == 4:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as dst:
                written = 0
                while written < size:
                    n = min(1024*1024, size - written)
                    dst.write(decrypt_region(src, header, off + written, n))
                    written += n
    import shutil
    dest = output / NEW_CORE
    shutil.copyfile(core, dest)
    print("Added:", dest, "size:", dest.stat().st_size)
    print("Original EBOOT.BIN, all other cores and media preserved.")
    print("Directory staged; NO PKG BUILT, NO PS3 COMPATIBILITY CLAIMED.")


if __name__ == "__main__":
    main()
