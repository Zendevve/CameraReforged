"""
CameraReforged — WoW 3.3.5a Camera Height Offset Patcher (Engine)

Pure patching logic with no UI, no sys.exit, no print.
All functions return values or raise exceptions.
"""

import struct
import shutil
import os

# --- Patch constants ---
PATCH_VA       = 0x006070cb
RETURN_VA      = 0x006070d1
ORIGINAL_BYTES = bytes([0xD9, 0x05, 0x70, 0x16, 0x9F, 0x00])
DEFAULT_HEIGHT = 0.5


def parse_pe(data):
    """Parse a PE executable and return (image_base, sections)."""
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
    """Find a run of 0x00/0xCC/0x90 in the .text section."""
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
    """If already patched, recover the code cave VA from the JMP."""
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    if data[patch_off] != 0xE9:
        return None
    rel = struct.unpack_from('<i', data, patch_off + 1)[0]
    return PATCH_VA + 5 + rel


def build_cave(cave_va, height_add):
    """Build the code cave payload (27 bytes)."""
    height_va = cave_va + 23

    buf = bytearray()
    buf += b'\xD9\x05'
    buf += struct.pack('<I', height_va)
    buf += b'\xD8\x45\xD4'
    buf += b'\xD9\x5D\xD4'
    buf += b'\xD9\x05\x70\x16\x9F\x00'
    jmp_target = RETURN_VA - (cave_va + 23)
    buf += b'\xE9' + struct.pack('<i', jmp_target)
    buf += struct.pack('<f', height_add)

    assert len(buf) == 27
    return buf


# ---------------------------------------------------------------------------
# High-level API for the GUI
# ---------------------------------------------------------------------------

def check_status(exe_path):
    """
    Check the patch status of a WoW executable.

    Returns:
        (status, height) where status is one of:
        - "unpatched"  — original bytes intact, height is None
        - "patched"    — JMP found, height is the current float offset
        - "unknown"    — unexpected bytes at patch site, height is None
    """
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    image_base, sections = parse_pe(data)
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    actual = bytes(data[patch_off:patch_off + len(ORIGINAL_BYTES)])

    if actual == ORIGINAL_BYTES:
        return ("unpatched", None)

    if actual[:1] == b'\xE9':
        cave_va = find_existing_cave_va(data, sections, image_base)
        if cave_va:
            height_va  = cave_va + 23
            height_off = va_to_offset(height_va, sections, image_base)
            cur_height = struct.unpack_from('<f', data, height_off)[0]
            return ("patched", cur_height)
        return ("patched", None)

    return ("unknown", None)


def apply_patch(exe_path, height=None):
    """
    Apply the camera height patch. Creates a .bak backup first.

    Returns a status message string.
    Raises on failure.
    """
    if height is None:
        height = DEFAULT_HEIGHT

    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    image_base, sections = parse_pe(data)

    # Verify patch site
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    actual = bytes(data[patch_off:patch_off + len(ORIGINAL_BYTES)])
    if actual != ORIGINAL_BYTES:
        if actual[:1] == b'\xE9':
            raise ValueError("Already patched. Use 'Update Height' to change the offset.")
        raise ValueError("Unexpected bytes at patch site. Wrong WoW version (need 3.3.5a)?")

    # Find code cave
    cave_off = find_code_cave(data, sections, image_base, needed=32)
    if cave_off is None:
        raise ValueError("No code cave found in .text section")

    cave_va = offset_to_va(cave_off, sections, image_base)

    # Build payloads
    cave_code = build_cave(cave_va, height)
    jmp_patch = bytearray(b'\xE9')
    jmp_patch += struct.pack('<i', cave_va - (PATCH_VA + 5))
    jmp_patch += b'\x90'

    # Backup
    backup = exe_path + '.bak'
    msgs = []
    if not os.path.exists(backup):
        shutil.copy2(exe_path, backup)
        msgs.append(f"Backup saved: {os.path.basename(backup)}")
    else:
        msgs.append(f"Backup already exists (not overwriting)")

    # Write
    data[cave_off : cave_off + len(cave_code)] = cave_code
    data[patch_off : patch_off + len(jmp_patch)] = jmp_patch

    with open(exe_path, 'wb') as f:
        f.write(data)

    msgs.append(f"Patched! Camera target raised by {height:+.2f} yards.")
    return "\n".join(msgs)


def set_height(exe_path, new_height):
    """
    Update the height offset on an already-patched exe.

    Returns a status message string.
    """
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    image_base, sections = parse_pe(data)
    cave_va = find_existing_cave_va(data, sections, image_base)
    if cave_va is None:
        raise ValueError("Not patched yet. Apply the patch first.")

    height_va  = cave_va + 23
    height_off = va_to_offset(height_va, sections, image_base)
    old_height = struct.unpack_from('<f', data, height_off)[0]

    backup = exe_path + '.bak'
    if not os.path.exists(backup):
        shutil.copy2(exe_path, backup)

    data[height_off:height_off + 4] = struct.pack('<f', new_height)
    with open(exe_path, 'wb') as f:
        f.write(data)

    return f"Height offset updated: {old_height:+.3f} → {new_height:+.3f} yards."


def restore_backup(exe_path):
    """
    Restore WoW.exe from WoW.exe.bak.

    Returns a status message string.
    """
    backup = exe_path + '.bak'
    if not os.path.exists(backup):
        raise FileNotFoundError("No backup file found (WoW.exe.bak). Cannot restore.")

    shutil.copy2(backup, exe_path)
    os.remove(backup)
    return "Restored original WoW.exe from backup and removed .bak file."
