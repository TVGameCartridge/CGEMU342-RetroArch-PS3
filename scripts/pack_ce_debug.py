#!/usr/bin/env python3
"""Stream non-finalized PS3 NPDRM homebrew PKG from a staged CE directory.

The package layout and digest/stream encryption follow RetroArch upstream's
tools/ps3/ps3py/pkg.py format. This avoids building a 240 MB string in RAM.
Intended for PS3 HEN TESTING ONLY; no retail signing is performed.
No ROMs or original PSX-Place binary files are stored in this repository.

Usage: python3 scripts/pack_ce_debug.py STAGE OUTPUT.pkg CONTENT_ID
"""
from pathlib import Path
import hashlib
import struct
import sys

if len(sys.argv) != 4:
    raise SystemExit("Usage: pack_ce_debug.py STAGE OUTPUT.pkg CONTENT_ID")
ROOT, OUTPUT, CID = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
if not ROOT.is_dir() or len(CID.encode("ascii")) > 48:
    raise SystemExit("Invalid staging directory or content ID")
if OUTPUT.exists():
    raise SystemExit("Output exists; refusing overwrite")

files = []
for path in sorted(ROOT.rglob("*")):
    if path.is_symlink() or (not path.is_dir() and not path.is_file()):
        raise SystemExit("Symlink or unusual filesystem object refused: " + str(path))
    rel = path.relative_to(ROOT).as_posix()
    size = path.stat().st_size if path.is_file() else 0
    flags = 0x80000003 if path.is_file() else 0x80000004
    files.append((rel, path, size, flags))

if not (ROOT / "PARAM.SFO").is_file() or not (
        ROOT / "USRDIR/cores/fceumm_libretro_ps3.SELF").is_file():
    raise SystemExit("Original SFO or CGEMU342 core absent in staging directory")

name_off = 32 * len(files)
names = bytearray()
records = []
for name, path, size, flags in files:
    encoded = name.encode("utf-8")
    records.append([name_off + len(names), len(encoded), 0, size, flags, 0])
    names.extend(encoded)
    names.extend(bytes((-len(encoded)) % 16))

offset = name_off + len(names)
for record, (_, _, size, _) in zip(records, files):
    record[2] = offset
    offset += (size + 15) & ~15

DATA_SIZE = offset
if DATA_SIZE >= (1 << 64):
    raise SystemExit("Package too large")

def header(qa_digest, licensee):
    return struct.pack(
        ">4sHHIIIIQQQ48s16s16s",
        b"\x7fPKG", 0, 1, 0xc0, 5, 0x80, len(files),
        DATA_SIZE + 0x1a0, 0x140, DATA_SIZE,
        CID.encode("ascii").ljust(48, b"\0"), qa_digest, licensee)

metadata = struct.pack(">11I2H3I2H",
    1, 4, 3, 2, 4, 5, 3, 4, 14, 4, 8, 0, 0,
    DATA_SIZE, 5, 4, 0x1061, 0)

index = b"".join(struct.pack(">IIQQII", *r) for r in records) + bytes(names)
assert len(index) % 16 == 0

qa = hashlib.sha1()
for _, path, size, flags in files:
    if not size:
        continue
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            qa.update(chunk)
qa.update(header(bytes(16), bytes(16)))
qa.update(index)
qa_digest = qa.digest()[:16]

def seed(key):
    return bytearray(key[:8] * 2 + key[8:] * 2 + bytes(32))

def encrypt_aligned(blob, key, first_block=0):
    if len(blob) % 16:
        raise ValueError("Unaligned encryption")
    state = seed(key)
    result = bytearray(len(blob))
    for i in range(0, len(blob), 16):
        struct.pack_into(">Q", state, 56, (first_block + i // 16) % (1 << 64))
        stream = hashlib.sha1(state).digest()[:16]
        value = int.from_bytes(blob[i:i + 16], "big") ^ int.from_bytes(stream, "big")
        result[i:i+16] = value.to_bytes(16, "big")
    return bytes(result)

licensee = encrypt_aligned(bytes(16), qa_digest, (1 << 64) - 1)
hdr = header(qa_digest, licensee)
hdr_sha = hashlib.sha1(hdr).digest()[3:19]
meta_sha = hashlib.sha1(metadata).digest()[3:19]
meta_pad = encrypt_aligned(bytes(48), meta_sha)
wrapped_meta_pad = encrypt_aligned(meta_pad, hdr_sha)

class EncryptedWriter:
    def __init__(self, destination, key):
        self.out = destination
        self.counter = 0
        self.state = seed(key)
        self.tail = b""
        self.pending = bytearray()

    def write(self, part):
        if not part:
            return
        self.tail += part
        full = (len(self.tail) // 16) * 16
        data = memoryview(self.tail)[:full]
        for at in range(0, full, 16):
            struct.pack_into(">Q", self.state, 56, self.counter)
            stream = hashlib.sha1(self.state).digest()[:16]
            block = (int.from_bytes(data[at:at+16], "big") ^
                     int.from_bytes(stream, "big")).to_bytes(16, "big")
            self.pending.extend(block)
            self.counter += 1
            if len(self.pending) >= 1024 * 1024:
                self.out.write(self.pending)
                self.pending.clear()
        self.tail = self.tail[full:]

    def finish(self):
        if self.tail:
            raise RuntimeError("Unaligned package content")
        if self.pending:
            self.out.write(self.pending)
            self.pending.clear()

with OUTPUT.open("wb") as out:
    out.write(hdr)
    out.write(hdr_sha)
    out.write(wrapped_meta_pad)
    out.write(metadata)
    out.write(meta_sha)
    out.write(meta_pad)
    assert out.tell() == 0x140
    writer = EncryptedWriter(out, qa_digest)
    writer.write(index)
    for name, path, size, flags in files:
        if size:
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    writer.write(chunk)
            if size % 16:
                writer.write(bytes(16 - size % 16))
    writer.finish()
    out.write(bytes(0x60))

if OUTPUT.stat().st_size != DATA_SIZE + 0x1a0:
    raise RuntimeError("Package size verification failed")
print("Wrote NON-FINALIZED PS3 HEN TEST PKG:", OUTPUT)
print("Content ID:", CID)
print("Files:", len(files), "Size:", OUTPUT.stat().st_size)
print("Unverified with the original PSX-Place CE launcher; back up PS3 first.")
