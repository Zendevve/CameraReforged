#!/usr/bin/env python3
"""
WoW 3.3.5a Camera Height Offset Patcher

Adds a constant height offset to the camera target Z position in Camera_Update,
right after Camera_GetTargetPosition returns.

Target position is stored as:
  [EBP - 0x34] = X
  [EBP - 0x30] = Y
  [EBP - 0x2c] = Z  <-- we add to this

Patch site: 0x006070cb (6-byte FLD right after GetTargetPosition call)
  Original:  FLD dword ptr [0x009f1670]    ; D9 05 70 16 9F 00
  Patched:   JMP <code_cave>; NOP

Code cave adds a constant to [EBP-0x2c] (target Z), then does the original FLD.
"""

import struct
import sys
import shutil
import os

# --- Patch constants ---
PATCH_VA       = 0x006070cb   # FLD dword ptr [0x009f1670], right after Camera_GetTargetPosition call
RETURN_VA      = 0x006070d1   # next instruction (LEA ECX,[EBP-0x54])
ORIGINAL_BYTES = bytes([0xD9, 0x05, 0x70, 0x16, 0x9F, 0x00])

# Height offset in game units (1 unit ≈ 1 yard).
# Player model is ~2 yards tall, camera target is ~chest height (~1.5y).
# Adding 0.75 raises it 50% of the character's height.
HEIGHT_ADD = 0.5


def parse_pe(data):
    if data[:2] != b'MZ':
        raise ValueError("Not an MZ executable")
    e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
    sig = struct.unpack_from('<I', data, e_lfanew)[0]
    if sig != 0x4550:
        raise ValueError("Not a PE file")
    coff = e_lfanew + 4
    num_sections  = struct.unpack_from('<H', data, coff + 2)[0]
    optional_size = struct.unpack_from('<H', data, coff + 16)[0]
    opt = coff + 20
    image_base = struct.unpack_from('<I', data, opt + 28)[0]
    sections = []
    sec = opt + optional_size
    for i in range(num_sections):
        off = sec + i * 40
        name       = data[off:off+8].rstrip(b'\x00').decode('ascii', errors='replace')
        virt_size  = struct.unpack_from('<I', data, off + 8)[0]
        virt_addr  = struct.unpack_from('<I', data, off + 12)[0]
        raw_size   = struct.unpack_from('<I', data, off + 16)[0]
        raw_offset = struct.unpack_from('<I', data, off + 20)[0]
        sections.append((name, virt_addr, virt_size, raw_offset, raw_size))
    return image_base, sections


def va_to_offset(va, sections, image_base):
    rva = va - image_base
    for name, virt_addr, virt_size, raw_offset, raw_size in sections:
        if virt_addr <= rva < virt_addr + raw_size:
            return raw_offset + (rva - virt_addr)
    raise ValueError(f"VA {va:#010x} not in any section")


def offset_to_va(off, sections, image_base):
    for name, virt_addr, virt_size, raw_offset, raw_size in sections:
        if raw_offset <= off < raw_offset + raw_size:
            return image_base + virt_addr + (off - raw_offset)
    raise ValueError(f"File offset {off:#x} not in any section")


def find_code_cave(data, sections, image_base, needed=32):
    """Find a run of 0x00/0xCC/0x90 in the .text section, scanning from the end."""
    for name, virt_addr, virt_size, raw_offset, raw_size in sections:
        if 'text' not in name.lower() and 'code' not in name.lower():
            continue
        end   = raw_offset + raw_size
        start = max(raw_offset, end - 4096)
        run_start = None
        run_len   = 0
        for i in range(start, end):
            if data[i] in (0x00, 0xCC, 0x90):
                if run_start is None:
                    run_start = i
                run_len += 1
                if run_len >= needed:
                    return run_start
            else:
                run_start = None
                run_len   = 0
    return None


def find_existing_cave_va(data, sections, image_base):
    """If the exe is already patched, read the JMP at PATCH_VA and recover
    the code cave's VA. Returns None if PATCH_VA doesn't hold a JMP."""
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    if data[patch_off] != 0xE9:
        return None
    rel = struct.unpack_from('<i', data, patch_off + 1)[0]
    return PATCH_VA + 5 + rel


def build_cave(cave_va, height_add):
    """
    Build the code cave:
      FLD  dword ptr [height_va]         ; D9 05 xx xx xx xx  (6 bytes) - load constant
      FADD dword ptr [EBP - 0x2c]        ; D8 45 D4           (3 bytes) - add target Z
      FSTP dword ptr [EBP - 0x2c]        ; D9 5D D4           (3 bytes) - store back
      FLD  dword ptr [0x009f1670]         ; D9 05 70 16 9F 00  (6 bytes) - original instruction
      JMP  RETURN_VA                      ; E9 xx xx xx xx     (5 bytes) - return
      dd   height_float                   ;                    (4 bytes)
    Total: 27 bytes
    """
    height_va = cave_va + 23  # float at offset 6+3+3+6+5 = 23

    buf = bytearray()
    # FLD dword ptr [height_va]
    buf += b'\xD9\x05'
    buf += struct.pack('<I', height_va)
    # FADD dword ptr [EBP - 0x2c]  (0x2c = 44, EBP-44 = EBP+0xFFFFFFD4, signed = -0x2c)
    buf += b'\xD8\x45\xD4'
    # FSTP dword ptr [EBP - 0x2c]
    buf += b'\xD9\x5D\xD4'
    # FLD dword ptr [0x009f1670]  (original instruction)
    buf += b'\xD9\x05\x70\x16\x9F\x00'
    # JMP RETURN_VA
    jmp_target = RETURN_VA - (cave_va + 23)
    buf += b'\xE9' + struct.pack('<i', jmp_target)
    # float constant
    buf += struct.pack('<f', height_add)

    assert len(buf) == 27
    return buf


def main():
    if len(sys.argv) < 2:
        print("WoW 3.3.5a Camera Height Offset Patcher")
        print(f"Usage: {sys.argv[0]} <WoW.exe> [--apply]")
        print(f"       {sys.argv[0]} <WoW.exe> --set-height <value>")
        print()
        print(f"  Raises camera target position by {HEIGHT_ADD} yards.")
        print("  Dry-run by default; pass --apply to write changes.")
        print()
        print("  --set-height permanently rewrites the baked-in default on an")
        print("  already-patched exe (close WoW first). Use this to keep a")
        print("  value you liked from the live adjuster across game restarts.")
        sys.exit(1)

    exe_path = sys.argv[1]
    apply    = '--apply' in sys.argv

    if '--set-height' in sys.argv:
        idx = sys.argv.index('--set-height')
        if idx + 1 >= len(sys.argv):
            print("ERROR: --set-height requires a value, e.g. --set-height 1.25")
            sys.exit(1)
        new_height = float(sys.argv[idx + 1])

        with open(exe_path, 'rb') as f:
            data = bytearray(f.read())
        image_base, sections = parse_pe(data)

        cave_va = find_existing_cave_va(data, sections, image_base)
        if cave_va is None:
            print(f"{exe_path} doesn't look patched yet (no JMP found at "
                  f"{PATCH_VA:#010x}). Run with --apply first.")
            sys.exit(1)

        height_va  = cave_va + 23
        height_off = va_to_offset(height_va, sections, image_base)
        old_height = struct.unpack_from('<f', data, height_off)[0]

        backup = exe_path + '.bak'
        if not os.path.exists(backup):
            shutil.copy2(exe_path, backup)
            print(f"Backup saved: {backup}")

        data[height_off:height_off + 4] = struct.pack('<f', new_height)
        with open(exe_path, 'wb') as f:
            f.write(data)

        print(f"Default camera height offset updated: "
              f"{old_height:+.3f} -> {new_height:+.3f} yards.")
        print("This is now permanent across game restarts (WoW must have "
              "been closed while this ran).")
        return

    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    image_base, sections = parse_pe(data)
    print(f"Image base: {image_base:#010x}")
    for s in sections:
        print(f"  {s[0]:8s}  VA {image_base + s[1]:#010x}  "
              f"VSize {s[2]:#08x}  Raw {s[3]:#08x}+{s[4]:#08x}")

    # ---- verify patch site ----
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    actual    = bytes(data[patch_off:patch_off + len(ORIGINAL_BYTES)])
    if actual != ORIGINAL_BYTES:
        print(f"\nPatch site {PATCH_VA:#010x} (file {patch_off:#x}):")
        print(f"  Expected: {ORIGINAL_BYTES.hex(' ')}")
        print(f"  Found:    {actual.hex(' ')}")
        if actual[:1] == b'\xE9':
            print("  Looks already patched.")
        else:
            print("  Wrong version or already modified.")
        sys.exit(1)

    print(f"\nPatch site verified at {PATCH_VA:#010x} (file offset {patch_off:#x})")

    # ---- find code cave ----
    cave_off = find_code_cave(data, sections, image_base, needed=32)
    if cave_off is None:
        print("ERROR: no code cave found in .text section")
        sys.exit(1)

    cave_va = offset_to_va(cave_off, sections, image_base)
    print(f"Code cave at file offset {cave_off:#x}, VA {cave_va:#010x}")

    # ---- build payloads ----
    cave_code = build_cave(cave_va, HEIGHT_ADD)

    jmp_patch = bytearray(b'\xE9')
    jmp_patch += struct.pack('<i', cave_va - (PATCH_VA + 5))
    jmp_patch += b'\x90'  # NOP the 6th byte

    print(f"\nPatch plan:")
    print(f"  {PATCH_VA:#010x}: {ORIGINAL_BYTES.hex(' ')}  ->  {bytes(jmp_patch).hex(' ')}  (JMP {cave_va:#010x}; NOP)")
    print(f"  {cave_va:#010x}: {bytes(cave_code).hex(' ')}")
    print(f"  Height offset: +{HEIGHT_ADD} yards = 0x{struct.pack('<f', HEIGHT_ADD).hex()}")
    print()

    if not apply:
        print("Dry run. Pass --apply to write the patch.")
        return

    # ---- apply ----
    backup = exe_path + '.bak'
    if not os.path.exists(backup):
        shutil.copy2(exe_path, backup)
        print(f"Backup saved: {backup}")
    else:
        print(f"Backup already exists: {backup} (not overwriting)")

    data[cave_off : cave_off + len(cave_code)] = cave_code
    data[patch_off : patch_off + len(jmp_patch)] = jmp_patch

    with open(exe_path, 'wb') as f:
        f.write(data)

    print(f"Patched! Camera target raised by {HEIGHT_ADD} yards.")


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        pass
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        print()
        input("Press Enter to exit...")
