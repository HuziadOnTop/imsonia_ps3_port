#!/usr/bin/env python
"""
PS3 PKG Builder - Generates PKGs matching the format of working homebrew PKGs
(DDLC LOVE AIO, LuaPlayer) with 8 metadata entries, Content Type=5, Package Type=0x4E.
Pure Python, no external dependencies.
"""
import struct, hashlib, os, sys, time

def sha1(data):
    return hashlib.sha1(data).digest()

def pkg_crypt(key16, inbuf, length):
    """Stream cipher: SHA1-based, 16 bytes per round. key16 = 16-byte key."""
    ctx = bytearray(64)
    ctx[0:8]   = key16[0:8]
    ctx[8:16]  = key16[0:8]
    ctx[16:24] = key16[8:16]
    ctx[24:32] = key16[8:16]
    # bytes 32-63 = 0 (counter at 56-63 starts at 0)

    result = bytearray(length)
    offset = 0
    last_pct = -1
    t0 = time.time()

    while offset < length:
        chunk = min(length - offset, 16)
        h = hashlib.sha1(bytes(ctx)).digest()
        for i in range(chunk):
            result[offset + i] = h[i] ^ inbuf[offset + i]

        # Increment 64-bit counter at ctx[56:64]
        for i in range(63, 55, -1):
            v = ctx[i] + 1
            ctx[i] = v & 0xFF
            if v < 256:
                break

        offset += chunk

        # Progress every 5%
        if length > 1000000:
            pct = offset * 100 // length
            if pct != last_pct and pct % 5 == 0:
                last_pct = pct
                elapsed = time.time() - t0
                speed = offset / elapsed / 1024 / 1024 if elapsed > 0 else 0
                eta = (length - offset) / (offset / elapsed) if elapsed > 0 else 0
                print(f"  Encrypting: {pct}% ({speed:.1f} MB/s, ETA: {eta:.0f}s)")

    return bytes(result)

def pkg_crypt_with_counter(key16, counter_start, inbuf, length):
    """Same as pkg_crypt but with a custom starting counter."""
    ctx = bytearray(64)
    ctx[0:8]   = key16[0:8]
    ctx[8:16]  = key16[0:8]
    ctx[16:24] = key16[8:16]
    ctx[24:32] = key16[8:16]
    struct.pack_into('>Q', ctx, 56, counter_start & 0xFFFFFFFFFFFFFFFF)

    result = bytearray(length)
    for offset in range(0, length, 16):
        chunk = min(length - offset, 16)
        h = hashlib.sha1(bytes(ctx)).digest()
        for i in range(chunk):
            result[offset + i] = h[i] ^ inbuf[offset + i]
        for i in range(63, 55, -1):
            v = ctx[i] + 1
            ctx[i] = v & 0xFF
            if v < 256:
                break
    return bytes(result)

def align16(n):
    return (n + 15) & ~15

def build_pkg(content_dir, content_id, output_path):
    print(f"=== PS3 PKG Builder ===")
    print(f"Content dir: {content_dir}")
    print(f"Content ID:  {content_id}")
    print(f"Output:      {output_path}")
    print()

    # 1. Scan files
    entries = []
    def scan(base, rel=""):
        items = sorted(os.listdir(base))
        # Top-level files first (SFO, icons), then dirs
        file_items = [(n, os.path.join(base, n)) for n in items if not os.path.isdir(os.path.join(base, n))]
        dir_items  = [(n, os.path.join(base, n)) for n in items if os.path.isdir(os.path.join(base, n))]

        for name, full in file_items:
            rpath = f"{rel}/{name}" if rel else name
            entries.append((rpath, False, full, os.path.getsize(full)))

        for name, full in dir_items:
            rpath = f"{rel}/{name}" if rel else name
            entries.append((rpath, True, full, 0))
            scan(full, rpath)

    scan(content_dir)
    item_count = len(entries)
    print(f"Items: {item_count}")

    # 2. Build file descriptor block and name block
    OVERWRITE = 0x80000000
    FLAG_RAW  = 0x03
    FLAG_DIR  = 0x04

    desc_size = 0x20 * item_count  # each descriptor = 32 bytes
    name_block = bytearray()
    descs = []

    for rpath, is_dir, full, fsize in entries:
        name_bytes = rpath.encode('utf-8')
        name_off = desc_size + len(name_block)
        name_len = len(name_bytes)
        padded = align16(name_len)
        name_block += name_bytes + b'\x00' * (padded - name_len)

        descs.append({
            'name_off': name_off, 'name_len': name_len,
            'file_off': 0, 'file_size': fsize if not is_dir else 0,
            'flags': OVERWRITE | (FLAG_DIR if is_dir else FLAG_RAW),
            'rpath': rpath, 'full': full, 'is_dir': is_dir,
        })

    # Calculate file data offsets within the data section
    file_data_start = desc_size + len(name_block)
    cur = file_data_start
    for d in descs:
        d['file_off'] = cur
        if not d['is_dir']:
            cur += align16(d['file_size'])

    # 3. Build plaintext data (descriptors + names + file data)
    print("Building file table...")
    desc_block = bytearray()
    for d in descs:
        desc_block += struct.pack('>II', d['name_off'], d['name_len'])
        desc_block += struct.pack('>Q', d['file_off'])
        desc_block += struct.pack('>Q', d['file_size'])
        desc_block += struct.pack('>II', d['flags'], 0)

    # Read all files and compute QA digest simultaneously
    print("Reading files...")
    file_data_block = bytearray()
    qa_files = hashlib.sha1()  # SHA1 of just file data (for metadata type 7)
    total_read = 0

    for d in descs:
        if d['is_dir']:
            continue
        with open(d['full'], 'rb') as fp:
            raw = fp.read()
        qa_files.update(raw)
        file_data_block += raw
        pad = align16(d['file_size']) - len(raw)
        if pad > 0:
            file_data_block += b'\x00' * pad
        total_read += len(raw)

    print(f"  Read {total_read:,} bytes from {sum(1 for d in descs if not d['is_dir'])} files")

    # Full plaintext data section
    plaintext = bytes(desc_block) + bytes(name_block) + bytes(file_data_block)
    data_size = len(plaintext)
    print(f"  Data section: {data_size:,} bytes ({data_size/1024/1024:.1f} MB)")

    # 4. Build metadata (8 entries, 0x80 bytes)
    meta_entries_size = 0x80  # 8 entries
    meta = bytearray(meta_entries_size)
    off = 0
    # Entry 0: DRM Type = 3 (Free)
    struct.pack_into('>III', meta, off, 1, 4, 3); off += 12
    # Entry 1: Content Type = 5 (Game Exec)
    struct.pack_into('>III', meta, off, 2, 4, 5); off += 12
    # Entry 2: Package Type = 0x4E
    struct.pack_into('>III', meta, off, 3, 4, 0x4E); off += 12
    # Entry 3: Data Size (8 bytes)
    struct.pack_into('>II', meta, off, 4, 8); off += 8
    struct.pack_into('>Q', meta, off, data_size); off += 8
    # Entry 4: Make Pkg Rev
    struct.pack_into('>III', meta, off, 5, 4, 0x99980100); off += 12
    # Entry 5: QA Digest (type 7, size 24)
    qa_file_hash = qa_files.digest()
    struct.pack_into('>II', meta, off, 7, 0x18); off += 8
    struct.pack_into('>Q', meta, off, 0); off += 8  # 8 zero bytes
    meta[off:off+16] = qa_file_hash[:16]; off += 16
    # Entry 6: Unknown8 (type 8, size 8)
    struct.pack_into('>II', meta, off, 8, 8); off += 8
    meta[off:off+8] = bytes.fromhex('8101500001000100'); off += 8
    # Entry 7: Unknown9 (type 9, size 8)
    struct.pack_into('>II', meta, off, 9, 8); off += 8
    struct.pack_into('>Q', meta, off, 0); off += 8

    assert off == meta_entries_size, f"Metadata size mismatch: {off} != {meta_entries_size}"

    # 5. Compute sizes and offsets
    DATA_OFFSET = 0x180  # 0x80 header + 0x40 hash area + 0xC0 meta area
    META_OFFSET = 0xC0
    META_SIZE = 0xC0     # 0x80 entries + 0x40 hash area
    total_pkg_size = DATA_OFFSET + data_size + 0x60  # + tail

    # 6. Build header (0x80 bytes)
    header = bytearray(0x80)
    struct.pack_into('>I', header, 0x00, 0x7F504B47)    # magic
    struct.pack_into('>I', header, 0x04, 0x00000001)     # type/revision
    struct.pack_into('>I', header, 0x08, META_OFFSET)    # metadata offset
    struct.pack_into('>I', header, 0x0C, 8)              # metadata count
    struct.pack_into('>I', header, 0x10, META_SIZE)      # metadata size
    struct.pack_into('>I', header, 0x14, item_count)     # item count
    struct.pack_into('>Q', header, 0x18, total_pkg_size) # total size
    struct.pack_into('>Q', header, 0x20, DATA_OFFSET)    # data offset
    struct.pack_into('>Q', header, 0x28, data_size)      # data size
    # Content ID at 0x30 (48 bytes)
    cid = content_id.encode('ascii')[:48]
    header[0x30:0x30+len(cid)] = cid
    # 0x60-0x6F: QA digest (computed next)
    # 0x70-0x7F: KLicensee (computed next)

    # 7. Compute QA digest
    # QA = SHA1(all_file_data + header_with_zeroes_at_60_7F + file_descriptors)
    qa_full = hashlib.sha1()
    # File data (raw, not padded)
    for d in descs:
        if d['is_dir']:
            continue
        with open(d['full'], 'rb') as fp:
            qa_full.update(fp.read())
    # Header (with 0x60-0x7F as zeros)
    qa_full.update(bytes(header))
    # File descriptors only (not names, not file data)
    qa_full.update(bytes(desc_block))
    qa_bytes = qa_full.digest()

    # Fill QA digest in header
    header[0x60:0x70] = qa_bytes[:16]

    # Compute KLicensee
    klic = pkg_crypt_with_counter(qa_bytes[:16], 0xFFFFFFFFFFFFFFFF, b'\x00' * 16, 16)
    header[0x70:0x80] = klic[:16]

    print("Computing hashes...")

    # 8. Compute SHA hashes
    header_sha = sha1(bytes(header))[3:19]  # 16 bytes
    meta_sha   = sha1(bytes(meta))[3:19]    # 16 bytes

    # Encrypted pads
    meta_sha_pad  = pkg_crypt(meta_sha, b'\x00' * 0x30, 0x30)    # 48 bytes
    meta_sha_pad2 = pkg_crypt(header_sha, bytes(meta_sha_pad), 0x30)  # 48 bytes

    # 9. Encrypt data section
    print(f"Encrypting {data_size:,} bytes...")
    enc_data = pkg_crypt(qa_bytes[:16], plaintext, data_size)

    # 10. Write PKG
    print(f"Writing PKG...")
    with open(output_path, 'wb') as fp:
        fp.write(bytes(header))       # 0x00-0x7F  (0x80)
        fp.write(header_sha)          # 0x80-0x8F  (0x10)
        fp.write(meta_sha_pad2)       # 0x90-0xBF  (0x30)
        fp.write(bytes(meta))         # 0xC0-0x13F (0x80)
        fp.write(meta_sha)            # 0x140-0x14F (0x10)
        fp.write(meta_sha_pad)        # 0x150-0x17F (0x30)
        fp.write(enc_data)            # 0x180+
        fp.write(b'\x00' * 0x60)      # tail

    final_size = os.path.getsize(output_path)
    print(f"\n{'='*50}")
    print(f"PKG created: {output_path}")
    print(f"Size: {final_size:,} bytes ({final_size/1024/1024:.1f} MB)")
    print(f"Content Type: 0x05 (Game Exec)")
    print(f"Package Type: 0x4E")
    print(f"DRM Type: 3 (Free)")
    print(f"Items: {item_count}")
    print(f"Content ID: {content_id}")

    # Verify
    with open(output_path, 'rb') as fp:
        vd = fp.read(0x180)
    ct = struct.unpack_from('>I', vd, 0xD4)[0]
    pt = struct.unpack_from('>I', vd, 0xE0)[0]
    print(f"\nVerification:")
    print(f"  Content Type: 0x{ct:08X} {'OK' if ct==5 else 'FAIL'}")
    print(f"  Package Type: 0x{pt:08X} {'OK' if pt==0x4E else 'FAIL'}")
    print(f"  Data offset:  0x{struct.unpack_from('>Q', vd, 0x20)[0]:X}")
    print(f"  Meta count:   {struct.unpack_from('>I', vd, 0x0C)[0]}")

if __name__ == '__main__':
    build_pkg(
        content_dir = r'C:\Users\AleemB\Desktop\insomnia-pkg\content',
        content_id  = 'UP0001-DOKI12300_00-0000000000000000',
        output_path = r'C:\Users\AleemB\Desktop\insomnia-pkg\Insomnia-PS3-v2.pkg',
    )
