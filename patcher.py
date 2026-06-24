"""
CameraReforged — WoW 3.3.5a Camera Patcher (Definitive Edition Engine)

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

# Phase 1: CVar registrations
PUSH_MAX_FACTOR_VA = 0x005fe1b2
ORIGINAL_MAX_FACTOR_BYTES = bytes([0x68, 0x40, 0x13, 0x9E, 0x00])

PUSH_ZOOM_SPEED_VA = 0x005fda36
ORIGINAL_ZOOM_SPEED_BYTES = bytes([0x68, 0xE0, 0xE7, 0xA1, 0x00])

# Phase 2: Camera shoulder offset reads
READ_SHOULDER_VAS = [
    0x00969392,  # fld dword ptr [ecx + 2E4h]
    0x0096944f,  # fld dword ptr [edi + 2E4h]
    0x0096aae1,  # fld dword ptr [edi + 2E4h]
    0x009739d8   # fld dword ptr [eax + 2E4h]
]
ORIGINAL_SHOULDER_BYTES = {
    0x00969392: bytes([0xD9, 0x81, 0xE4, 0x02, 0x00, 0x00]),
    0x0096944f: bytes([0xD9, 0x87, 0xE4, 0x02, 0x00, 0x00]),
    0x0096aae1: bytes([0xD9, 0x87, 0xE4, 0x02, 0x00, 0x00]),
    0x009739d8: bytes([0xD9, 0x80, 0xE4, 0x02, 0x00, 0x00])
}

# Code cave offsets
CAVE_HEIGHT_VAL_OFFSET     = 23
CAVE_SHOULDER_VAL_OFFSET   = 27
CAVE_MAX_FACTOR_STR_OFFSET = 31
CAVE_ZOOM_SPEED_STR_OFFSET = 39
CAVE_TOTAL_SIZE            = 47

# Defaults
DEFAULT_HEIGHT = 0.5
DEFAULT_SHOULDER = 0.0
DEFAULT_MAX_FACTOR = 2.6
DEFAULT_ZOOM_SPEED = 20.0


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


def find_code_cave(data, sections, image_base, needed=64):
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


def build_cave(cave_va, height_add, shoulder_val, max_factor_str, zoom_speed_str):
    """Build the code cave payload (47 bytes)."""
    height_va = cave_va + CAVE_HEIGHT_VAL_OFFSET

    buf = bytearray()
    buf += b'\xD9\x05'
    buf += struct.pack('<I', height_va)
    buf += b'\xD8\x45\xD4'
    buf += b'\xD9\x5D\xD4'
    buf += b'\xD9\x05\x70\x16\x9F\x00'
    jmp_target = RETURN_VA - (cave_va + CAVE_HEIGHT_VAL_OFFSET)
    buf += b'\xE9' + struct.pack('<i', jmp_target)

    # Values at offsets:
    # 23: Height (float, 4 bytes)
    buf += struct.pack('<f', height_add)
    # 27: Shoulder (float, 4 bytes)
    buf += struct.pack('<f', shoulder_val)
    # 31: Max distance factor (string, 8 bytes)
    buf += max_factor_str.encode('ascii').ljust(8, b'\x00')
    # 39: Zoom speed (string, 8 bytes)
    buf += zoom_speed_str.encode('ascii').ljust(8, b'\x00')

    assert len(buf) == CAVE_TOTAL_SIZE
    return buf


# ---------------------------------------------------------------------------
# High-level API for the GUI
# ---------------------------------------------------------------------------

def check_status(exe_path):
    """
    Check the patch status of a WoW executable.

    Returns:
        (status, values) where status is one of:
        - "unpatched"      — original bytes intact, values are stock defaults
        - "patched"        — JMP found, values are the current float/string settings
        - "patched_legacy" — JMP found but legacy cave format, values has legacy height and defaults for others
        - "unknown"        — unexpected bytes at patch site, values are defaults
    """
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    try:
        image_base, sections = parse_pe(data)
        patch_off = va_to_offset(PATCH_VA, sections, image_base)
        actual = bytes(data[patch_off:patch_off + len(ORIGINAL_BYTES)])

        if actual == ORIGINAL_BYTES:
            return ("unpatched", (0.0, 0.0, 1.0, 8.33))

        if actual[:1] == b'\xE9':
            cave_va = find_existing_cave_va(data, sections, image_base)
            if cave_va:
                # Read height
                height_off = va_to_offset(cave_va + CAVE_HEIGHT_VAL_OFFSET, sections, image_base)
                cur_height = struct.unpack_from('<f', data, height_off)[0]

                # Check if it's the new Definitive Edition layout by verifying the max factor CVar push redirect
                max_factor_push_off = va_to_offset(PUSH_MAX_FACTOR_VA, sections, image_base)
                is_definitive = False
                if data[max_factor_push_off] == 0x68:
                    target_va = struct.unpack_from('<I', data, max_factor_push_off + 1)[0]
                    if cave_va <= target_va < cave_va + CAVE_TOTAL_SIZE:
                        is_definitive = True

                if is_definitive:
                    # Read shoulder offset
                    shoulder_off = va_to_offset(cave_va + CAVE_SHOULDER_VAL_OFFSET, sections, image_base)
                    cur_shoulder = struct.unpack_from('<f', data, shoulder_off)[0]

                    # Read max factor
                    max_factor_off = va_to_offset(cave_va + CAVE_MAX_FACTOR_STR_OFFSET, sections, image_base)
                    max_factor_bytes = data[max_factor_off:max_factor_off + 8]
                    cur_max_factor = float(max_factor_bytes.split(b'\x00')[0].decode('ascii'))

                    # Read zoom speed
                    zoom_speed_off = va_to_offset(cave_va + CAVE_ZOOM_SPEED_STR_OFFSET, sections, image_base)
                    zoom_speed_bytes = data[zoom_speed_off:zoom_speed_off + 8]
                    cur_zoom_speed = float(zoom_speed_bytes.split(b'\x00')[0].decode('ascii'))

                    return ("patched", (cur_height, cur_shoulder, cur_max_factor, cur_zoom_speed))
                else:
                    return ("patched_legacy", (cur_height, 0.0, 1.0, 8.33))

            return ("patched", (0.0, 0.0, 1.0, 8.33))

    except Exception:
        pass

    return ("unknown", (0.0, 0.0, 1.0, 8.33))


def apply_patch(exe_path, height=0.5, shoulder=0.0, max_distance=2.6, zoom_speed=20.0):
    """
    Apply the Definitive Edition patches. Creates a .bak backup first.

    Returns a status message string.
    Raises on failure.
    """
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    image_base, sections = parse_pe(data)

    # 1. Verify height patch site
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    actual = bytes(data[patch_off:patch_off + len(ORIGINAL_BYTES)])
    if actual != ORIGINAL_BYTES:
        if actual[:1] == b'\xE9':
            raise ValueError("Already patched. Use 'Update' to change the parameters.")
        raise ValueError("Unexpected bytes at height patch site. Wrong WoW version (need 3.3.5a)?")

    # 2. Verify registration and shoulder offset patch sites
    max_factor_push_off = va_to_offset(PUSH_MAX_FACTOR_VA, sections, image_base)
    if bytes(data[max_factor_push_off : max_factor_push_off + len(ORIGINAL_MAX_FACTOR_BYTES)]) != ORIGINAL_MAX_FACTOR_BYTES:
        raise ValueError("Unexpected bytes at max factor CVar patch site.")

    zoom_speed_push_off = va_to_offset(PUSH_ZOOM_SPEED_VA, sections, image_base)
    if bytes(data[zoom_speed_push_off : zoom_speed_push_off + len(ORIGINAL_ZOOM_SPEED_BYTES)]) != ORIGINAL_ZOOM_SPEED_BYTES:
        raise ValueError("Unexpected bytes at zoom speed CVar patch site.")

    for va in READ_SHOULDER_VAS:
        off = va_to_offset(va, sections, image_base)
        expected = ORIGINAL_SHOULDER_BYTES[va]
        if bytes(data[off : off + len(expected)]) != expected:
            raise ValueError(f"Unexpected bytes at shoulder read site {va:#010x}.")

    # Find code cave
    cave_off = find_code_cave(data, sections, image_base, needed=CAVE_TOTAL_SIZE)
    if cave_off is None:
        raise ValueError("No code cave found in .text section")

    cave_va = offset_to_va(cave_off, sections, image_base)

    # Format strings
    max_factor_str = f"{max_distance:.2f}"
    zoom_speed_str = f"{zoom_speed:.2f}"

    # Build payloads
    cave_code = build_cave(cave_va, height, shoulder, max_factor_str, zoom_speed_str)

    # JMP patch at height patch site (6 bytes: JMP rel + NOP)
    jmp_patch = bytearray(b'\xE9')
    jmp_patch += struct.pack('<i', cave_va - (PATCH_VA + 5))
    jmp_patch += b'\x90'

    # CVar registration pushes (5 bytes: PUSH address)
    max_factor_push_patch = b'\x68' + struct.pack('<I', cave_va + CAVE_MAX_FACTOR_STR_OFFSET)
    zoom_speed_push_patch = b'\x68' + struct.pack('<I', cave_va + CAVE_ZOOM_SPEED_STR_OFFSET)

    # Shoulder offset reads (6 bytes: fld dword ptr [shoulder_val_va])
    shoulder_read_patch = b'\xD9\x05' + struct.pack('<I', cave_va + CAVE_SHOULDER_VAL_OFFSET)

    # Backup
    backup = exe_path + '.bak'
    msgs = []
    if not os.path.exists(backup):
        shutil.copy2(exe_path, backup)
        msgs.append(f"Backup saved: {os.path.basename(backup)}")
    else:
        msgs.append(f"Backup already exists (not overwriting)")

    # Write code cave
    data[cave_off : cave_off + len(cave_code)] = cave_code

    # Write height JMP
    data[patch_off : patch_off + len(jmp_patch)] = jmp_patch

    # Write CVar pushes
    data[max_factor_push_off : max_factor_push_off + len(max_factor_push_patch)] = max_factor_push_patch
    data[zoom_speed_push_off : zoom_speed_push_off + len(zoom_speed_push_patch)] = zoom_speed_push_patch

    # Write shoulder reads
    for va in READ_SHOULDER_VAS:
        off = va_to_offset(va, sections, image_base)
        data[off : off + len(shoulder_read_patch)] = shoulder_read_patch

    with open(exe_path, 'wb') as f:
        f.write(data)

    msgs.append("Patched! Camera height, shoulder offset, max distance, and zoom speed successfully customized.")
    return "\n".join(msgs)


def update_values(exe_path, height, shoulder, max_distance, zoom_speed):
    """
    Update the values inside the code cave on an already-patched exe.

    Returns a status message string.
    """
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    image_base, sections = parse_pe(data)
    cave_va = find_existing_cave_va(data, sections, image_base)
    if cave_va is None:
        raise ValueError("Not patched yet. Apply the patch first.")

    height_off = va_to_offset(cave_va + CAVE_HEIGHT_VAL_OFFSET, sections, image_base)
    shoulder_off = va_to_offset(cave_va + CAVE_SHOULDER_VAL_OFFSET, sections, image_base)
    max_factor_off = va_to_offset(cave_va + CAVE_MAX_FACTOR_STR_OFFSET, sections, image_base)
    zoom_speed_off = va_to_offset(cave_va + CAVE_ZOOM_SPEED_STR_OFFSET, sections, image_base)

    # Check if max factor CVar push is redirected to see if this is definitive or legacy
    max_factor_push_off = va_to_offset(PUSH_MAX_FACTOR_VA, sections, image_base)
    is_definitive = False
    if data[max_factor_push_off] == 0x68:
        target_va = struct.unpack_from('<I', data, max_factor_push_off + 1)[0]
        if cave_va <= target_va < cave_va + CAVE_TOTAL_SIZE:
            is_definitive = True

    if not is_definitive:
        raise ValueError("Legacy patch detected. Please click 'Restore Backup' and apply a fresh patch.")

    backup = exe_path + '.bak'
    if not os.path.exists(backup):
        shutil.copy2(exe_path, backup)

    data[height_off:height_off + 4] = struct.pack('<f', height)
    data[shoulder_off:shoulder_off + 4] = struct.pack('<f', shoulder)

    max_factor_str = f"{max_distance:.2f}".encode('ascii').ljust(8, b'\x00')
    zoom_speed_str = f"{zoom_speed:.2f}".encode('ascii').ljust(8, b'\x00')
    data[max_factor_off : max_factor_off + 8] = max_factor_str
    data[zoom_speed_off : zoom_speed_off + 8] = zoom_speed_str

    with open(exe_path, 'wb') as f:
        f.write(data)

    return "Camera parameters updated successfully."


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
