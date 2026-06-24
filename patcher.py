"""
CameraReforged — WoW 3.3.5a Camera Patcher (Definitive Edition Engine - Phase 3)

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

# Phase 3: CVar registration hook
CVAR_INIT_VA = 0x0051D9B0
ORIGINAL_CVAR_INIT_BYTES = bytes([0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x80, 0x00, 0x00, 0x00])

# Cave offsets inside .rdata
CAVE_HEIGHT_VAL_OFFSET     = 0
CAVE_SHOULDER_VAL_OFFSET   = 4
CAVE_MAX_FACTOR_STR_OFFSET = 8
CAVE_ZOOM_SPEED_STR_OFFSET = 16
CAVE_HEIGHT_NAME_OFFSET    = 24
CAVE_HEIGHT_DEF_OFFSET     = 42
CAVE_SHOULDER_NAME_OFFSET  = 47
CAVE_SHOULDER_DEF_OFFSET   = 71
CAVE_FUNCTIONS_OFFSET      = 76

# Defaults
DEFAULT_HEIGHT = 0.5
DEFAULT_SHOULDER = 0.0
DEFAULT_MAX_FACTOR = 2.6
DEFAULT_ZOOM_SPEED = 20.0


class Assembler:
    """A lightweight absolute/relative x86 assembler helper for generating machine code."""
    def __init__(self, start_va):
        self.va = start_va
        self.buf = bytearray()
        self.labels = {}
        self.jumps = [] # list of (offset, label_name/absolute_target, jump_type)

    def label(self, name):
        self.labels[name] = self.va + len(self.buf)

    def write(self, data):
        self.buf.extend(data)

    def jmp_rel8(self, name, cond_op=None):
        pos = len(self.buf)
        if cond_op is None:
            cond_op = b'\xEB'
        self.buf.extend(cond_op)
        self.buf.append(0)
        self.jumps.append((pos + len(cond_op), name, 'rel8'))

    def jmp_rel32(self, target, cond_op=None):
        pos = len(self.buf)
        if cond_op is None:
            cond_op = b'\xE9'
        self.buf.extend(cond_op)
        self.buf.extend(b'\x00\x00\x00\x00')
        self.jumps.append((pos + len(cond_op), target, 'rel32'))

    def call_abs(self, target):
        pos = len(self.buf)
        self.buf.append(0xE8)
        self.buf.extend(b'\x00\x00\x00\x00')
        self.jumps.append((pos + 1, target, 'call32'))

    def push_abs(self, target):
        pos = len(self.buf)
        self.buf.append(0x68)
        self.buf.extend(b'\x00\x00\x00\x00')
        self.jumps.append((pos + 1, target, 'abs32'))

    def resolve(self):
        for pos, target, jtype in self.jumps:
            if isinstance(target, str):
                target_va = self.labels[target]
            else:
                target_va = target
            curr_va = self.va + pos
            if jtype == 'rel8':
                rel = target_va - (curr_va + 1)
                assert -128 <= rel <= 127, f"Rel8 jump to {target} out of range ({rel})"
                self.buf[pos] = rel & 0xFF
            elif jtype == 'rel32':
                rel = target_va - (curr_va + 4)
                struct.pack_into('<i', self.buf, pos, rel)
            elif jtype == 'call32':
                rel = target_va - (curr_va + 4)
                struct.pack_into('<i', self.buf, pos, rel)
            elif jtype == 'abs32':
                struct.pack_into('<I', self.buf, pos, target_va)
        return bytes(self.buf)


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
    """Find a run of 0x00/0xCC/0x90 in the .text section (used to detect legacy locations)."""
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
    """If legacy patched, recover the legacy code cave VA from the JMP."""
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    if data[patch_off] != 0xE9:
        return None
    rel = struct.unpack_from('<i', data, patch_off + 1)[0]
    return PATCH_VA + 5 + rel


def get_section_cave(data, sections, image_base, section_name, needed_size):
    """
    Find a cave in a section by looking at the padding between virt_size and raw_size.
    If the padding is not large enough, falls back to scanning the end of the section raw data for runs of 0x00/0xCC/0x90.
    """
    target = section_name.lower().strip()
    for name, virt_addr, virt_size, raw_offset, raw_size in sections:
        clean_name = name.lower().replace('.', '').strip()
        is_match = False
        if target == 'text':
            is_match = clean_name in ('text', 'code')
        else:
            is_match = (clean_name == target)

        if is_match:
            # Method 1: Check if there's enough space in the section alignment padding
            aligned_rva = (virt_addr + virt_size + 15) & ~15
            if aligned_rva + needed_size <= virt_addr + raw_size:
                cave_va = image_base + aligned_rva
                cave_off = raw_offset + (aligned_rva - virt_addr)
                return cave_va, cave_off
            
            # Method 2: Scan the end of the section for a run of 0x00/0xCC/0x90
            end   = raw_offset + raw_size
            start = max(raw_offset, end - 4096)
            run_start = None
            run_len   = 0
            for i in range(start, end):
                if data[i] in (0x00, 0xCC, 0x90):
                    if run_start is None:
                        run_start = i
                    run_len += 1
                    if run_len >= needed_size:
                        cave_off = run_start
                        cave_va = image_base + virt_addr + (cave_off - raw_offset)
                        return cave_va, cave_off
                else:
                    run_start = None
                    run_len   = 0
                    
    raise ValueError(f"Could not find a suitable cave in section '{section_name}' of size {needed_size}")


# ---------------------------------------------------------------------------
# High-level API for the GUI
# ---------------------------------------------------------------------------

def check_status(exe_path):
    """
    Check the patch status of a WoW executable.

    Returns:
        (status, values) where status is one of:
        - "unpatched"      — original bytes intact, values are stock defaults
        - "patched"        — both detours present, values are the current float/string settings
        - "patched_legacy" — legacy height-only patch, must restore first
        - "unknown"        — unexpected bytes at patch site, values are defaults
    """
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    try:
        image_base, sections = parse_pe(data)
        
        # Check height patch site
        patch_off = va_to_offset(PATCH_VA, sections, image_base)
        actual_height_bytes = bytes(data[patch_off:patch_off + len(ORIGINAL_BYTES)])

        # Check cvar init patch site
        cvar_init_off = va_to_offset(CVAR_INIT_VA, sections, image_base)
        actual_cvar_bytes = bytes(data[cvar_init_off:cvar_init_off + len(ORIGINAL_CVAR_INIT_BYTES)])

        is_patched_height = (actual_height_bytes[0] == 0xE9)
        is_patched_cvar   = (actual_cvar_bytes[0] == 0xE9)

        if not is_patched_height and not is_patched_cvar:
            if actual_height_bytes == ORIGINAL_BYTES and actual_cvar_bytes == ORIGINAL_CVAR_INIT_BYTES:
                return ("unpatched", (0.0, 0.0, 1.0, 8.33))
            return ("unknown", (0.0, 0.0, 1.0, 8.33))

        if is_patched_height and not is_patched_cvar:
            # Legacy height-only patch
            cave_va = find_existing_cave_va(data, sections, image_base)
            if cave_va:
                height_off = va_to_offset(cave_va + 23, sections, image_base)
                cur_height = struct.unpack_from('<f', data, height_off)[0]
                return ("patched_legacy", (cur_height, 0.0, 1.0, 8.33))
            return ("patched_legacy", (0.5, 0.0, 1.0, 8.33))

        if is_patched_height and is_patched_cvar:
            # Definitive Edition patch
            data_cave_va, data_cave_off = get_section_cave(data, sections, image_base, 'data', 80)
            
            cur_height = struct.unpack_from('<f', data, data_cave_off + CAVE_HEIGHT_VAL_OFFSET)[0]
            cur_shoulder = struct.unpack_from('<f', data, data_cave_off + CAVE_SHOULDER_VAL_OFFSET)[0]
            
            max_factor_bytes = data[data_cave_off + CAVE_MAX_FACTOR_STR_OFFSET : data_cave_off + CAVE_MAX_FACTOR_STR_OFFSET + 8]
            cur_max_factor = float(max_factor_bytes.split(b'\x00')[0].decode('ascii'))
            
            zoom_speed_bytes = data[data_cave_off + CAVE_ZOOM_SPEED_STR_OFFSET : data_cave_off + CAVE_ZOOM_SPEED_STR_OFFSET + 8]
            cur_zoom_speed = float(zoom_speed_bytes.split(b'\x00')[0].decode('ascii'))
            
            return ("patched", (cur_height, cur_shoulder, cur_max_factor, cur_zoom_speed))

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
    actual_height_bytes = bytes(data[patch_off:patch_off + len(ORIGINAL_BYTES)])
    if actual_height_bytes != ORIGINAL_BYTES:
        if actual_height_bytes[0] == 0xE9:
            raise ValueError("Already patched. Use 'Update Settings' to change parameters.")
        raise ValueError("Unexpected bytes at height patch site. Wrong WoW version?")

    # 2. Verify CVar init patch site
    cvar_init_off = va_to_offset(CVAR_INIT_VA, sections, image_base)
    actual_cvar_bytes = bytes(data[cvar_init_off:cvar_init_off + len(ORIGINAL_CVAR_INIT_BYTES)])
    if actual_cvar_bytes != ORIGINAL_CVAR_INIT_BYTES:
        raise ValueError("Unexpected bytes at CVar initialization function entry.")

    # 3. Verify registration and shoulder offset patch sites
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

    # Get caves
    try:
        code_cave_va, code_cave_off = get_section_cave(data, sections, image_base, 'text', 160)
        modify_rdata_exec = False
    except ValueError:
        # Fallback: Find code cave in .rdata and mark it executable
        code_cave_va, code_cave_off = get_section_cave(data, sections, image_base, 'rdata', 160)
        modify_rdata_exec = True

    data_cave_va, data_cave_off = get_section_cave(data, sections, image_base, 'data', 80)

    # Format strings
    max_factor_str = f"{max_distance:.2f}".encode('ascii').ljust(8, b'\x00')
    zoom_speed_str = f"{zoom_speed:.2f}".encode('ascii').ljust(8, b'\x00')

    # Build data cave payload buffer (80 bytes)
    cave_buf = bytearray(80)

    # Write static variables & strings
    struct.pack_into('<f', cave_buf, CAVE_HEIGHT_VAL_OFFSET, height)
    struct.pack_into('<f', cave_buf, CAVE_SHOULDER_VAL_OFFSET, shoulder)
    cave_buf[CAVE_MAX_FACTOR_STR_OFFSET : CAVE_MAX_FACTOR_STR_OFFSET + 8] = max_factor_str
    cave_buf[CAVE_ZOOM_SPEED_STR_OFFSET : CAVE_ZOOM_SPEED_STR_OFFSET + 8] = zoom_speed_str
    
    # Write CVar strings
    cvar_height_name_bytes = b"test_cameraHeight\x00"
    cvar_height_def_bytes = f"{height:.2f}\x00".encode('ascii')
    cvar_shoulder_name_bytes = b"test_cameraOverShoulder\x00"
    cvar_shoulder_def_bytes = f"{shoulder:.2f}\x00".encode('ascii')

    cave_buf[CAVE_HEIGHT_NAME_OFFSET : CAVE_HEIGHT_NAME_OFFSET + len(cvar_height_name_bytes)] = cvar_height_name_bytes
    cave_buf[CAVE_HEIGHT_DEF_OFFSET : CAVE_HEIGHT_DEF_OFFSET + len(cvar_height_def_bytes)] = cvar_height_def_bytes
    cave_buf[CAVE_SHOULDER_NAME_OFFSET : CAVE_SHOULDER_NAME_OFFSET + len(cvar_shoulder_name_bytes)] = cvar_shoulder_name_bytes
    cave_buf[CAVE_SHOULDER_DEF_OFFSET : CAVE_SHOULDER_DEF_OFFSET + len(cvar_shoulder_def_bytes)] = cvar_shoulder_def_bytes

    # Assemble code
    asm = Assembler(code_cave_va)

    # ── height_callback ──
    asm.label("height_callback")
    asm.write(b'\x8B\x44\x24\x04')           # mov eax, [esp + 4] (CVar*)
    asm.write(b'\xD9\x40\x2C')               # fld dword ptr [eax + 2Ch] (valueFloat)
    asm.write(b'\xD9\x1D' + struct.pack('<I', data_cave_va + CAVE_HEIGHT_VAL_OFFSET))
    asm.write(b'\x31\xC0\x40')               # xor eax, eax; inc eax
    asm.write(b'\xC3')                       # ret

    # ── shoulder_callback ──
    asm.label("shoulder_callback")
    asm.write(b'\x8B\x44\x24\x04')           # mov eax, [esp + 4] (CVar*)
    asm.write(b'\xD9\x40\x2C')               # fld dword ptr [eax + 2Ch] (valueFloat)
    asm.write(b'\xD9\x1D' + struct.pack('<I', data_cave_va + CAVE_SHOULDER_VAL_OFFSET))
    asm.write(b'\x31\xC0\x40')               # xor eax, eax; inc eax
    asm.write(b'\xC3')                       # ret

    # ── cvar_init_hook ──
    asm.label("cvar_init_hook")
    asm.write(b'\x60')                       # pushad
    
    # Register test_cameraHeight
    asm.write(b'\x6A\x00')                   # push 0 (a9)
    asm.write(b'\x6A\x00')                   # push 0 (a8)
    asm.write(b'\x6A\x00')                   # push 0 (a7)
    asm.write(b'\x6A\x00')                   # push 0 (a6)
    asm.push_abs("height_callback")
    asm.push_abs(data_cave_va + CAVE_HEIGHT_DEF_OFFSET)
    asm.write(b'\x6A\x01')                   # push 1 (flags)
    asm.write(b'\x6A\x00')                   # push 0 (desc)
    asm.push_abs(data_cave_va + CAVE_HEIGHT_NAME_OFFSET)
    asm.call_abs(0x00767FC0)                 # call CVars_Register
    asm.write(b'\x83\xC4\x24')               # add esp, 24h
    
    # Register test_cameraOverShoulder
    asm.write(b'\x6A\x00')                   # push 0 (a9)
    asm.write(b'\x6A\x00')                   # push 0 (a8)
    asm.write(b'\x6A\x00')                   # push 0 (a7)
    asm.write(b'\x6A\x00')                   # push 0 (a6)
    asm.push_abs("shoulder_callback")
    asm.push_abs(data_cave_va + CAVE_SHOULDER_DEF_OFFSET)
    asm.write(b'\x6A\x01')                   # push 1 (flags)
    asm.write(b'\x6A\x00')                   # push 0 (desc)
    asm.push_abs(data_cave_va + CAVE_SHOULDER_NAME_OFFSET)
    asm.call_abs(0x00767FC0)                 # call CVars_Register
    asm.write(b'\x83\xC4\x24')               # add esp, 24h
    
    asm.write(b'\x61')                       # popad
    asm.write(b'\x55')                       # push ebp
    asm.write(b'\x8B\xEC')                   # mov ebp, esp
    asm.write(b'\x81\xEC\x80\x00\x00\x00')   # sub esp, 80h
    asm.jmp_rel32(0x0051D9B9)

    # ── camera_height_hook ──
    asm.label("camera_height_hook")
    asm.write(b'\xD9\x05' + struct.pack('<I', data_cave_va + CAVE_HEIGHT_VAL_OFFSET))
    asm.write(b'\xD8\x45\xD4')               # fadd dword ptr [ebp-2Ch]
    asm.write(b'\xD9\x5D\xD4')               # fstp dword ptr [ebp-2Ch]
    asm.write(b'\xD9\x05\x70\x16\x9F\x00')   # fld dword ptr [0x009F1670]
    asm.jmp_rel32(0x006070d1)

    code_bytes = asm.resolve()
    assert len(code_bytes) <= 160, f"Code size {len(code_bytes)} exceeds functions allocation space!"

    # Modify .rdata PE characteristics to include EXECUTE (if using fallback)
    if modify_rdata_exec:
        e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
        coff = e_lfanew + 4
        optional_size = struct.unpack_from('<H', data, coff + 16)[0]
        opt = coff + 20
        sec_start = opt + optional_size

        rdata_hdr_off = None
        for i in range(len(sections)):
            off = sec_start + i * 40
            name = data[off:off+8].rstrip(b'\x00').decode('ascii', errors='replace')
            if 'rdata' in name.lower():
                rdata_hdr_off = off
                break
        if rdata_hdr_off is not None:
            charac = struct.unpack_from('<I', data, rdata_hdr_off + 36)[0]
            charac |= 0x20000000 # EXECUTE
            struct.pack_into('<I', data, rdata_hdr_off + 36, charac)

    # Patch instructions:
    # 1. Detour CVars_Initialize (9 bytes)
    cvar_init_hook_va = code_cave_va + asm.labels["cvar_init_hook"]
    cvar_jmp_patch = b'\xE9' + struct.pack('<i', cvar_init_hook_va - (CVAR_INIT_VA + 5)) + b'\x90\x90\x90\x90'
    data[cvar_init_off : cvar_init_off + 9] = cvar_jmp_patch

    # 2. Detour Camera Height (6 bytes)
    camera_height_hook_va = code_cave_va + asm.labels["camera_height_hook"]
    height_jmp_patch = b'\xE9' + struct.pack('<i', camera_height_hook_va - (PATCH_VA + 5)) + b'\x90'
    data[patch_off : patch_off + 6] = height_jmp_patch

    # 3. Patch max factor and zoom speed pushes (5 bytes each)
    data[max_factor_push_off : max_factor_push_off + 5] = b'\x68' + struct.pack('<I', data_cave_va + CAVE_MAX_FACTOR_STR_OFFSET)
    data[zoom_speed_push_off : zoom_speed_push_off + 5] = b'\x68' + struct.pack('<I', data_cave_va + CAVE_ZOOM_SPEED_STR_OFFSET)

    # 4. Patch shoulder reads (6 bytes each)
    shoulder_read_patch = b'\xD9\x05' + struct.pack('<I', data_cave_va + CAVE_SHOULDER_VAL_OFFSET)
    for va in READ_SHOULDER_VAS:
        off = va_to_offset(va, sections, image_base)
        data[off : off + 6] = shoulder_read_patch

    # Backup management
    backup = exe_path + '.bak'
    msgs = []
    if not os.path.exists(backup):
        shutil.copy2(exe_path, backup)
        msgs.append(f"Backup saved: {os.path.basename(backup)}")
    else:
        msgs.append(f"Backup already exists (not overwriting)")

    # Write code bytes into code cave padding
    data[code_cave_off : code_cave_off + len(code_bytes)] = code_bytes

    # Write the entire cave_buf into data cave padding
    data[data_cave_off : data_cave_off + len(cave_buf)] = cave_buf

    with open(exe_path, 'wb') as f:
        f.write(data)

    msgs.append("Patched! Native CVar registration and camera parameters successfully configured.")
    return "\n".join(msgs)


def update_values(exe_path, height, shoulder, max_distance, zoom_speed):
    """
    Update the values inside the code cave on an already-patched exe.

    Returns a status message string.
    """
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    image_base, sections = parse_pe(data)
    
    # Check if patched
    patch_off = va_to_offset(PATCH_VA, sections, image_base)
    cvar_init_off = va_to_offset(CVAR_INIT_VA, sections, image_base)
    if data[patch_off] != 0xE9 or data[cvar_init_off] != 0xE9:
        raise ValueError("Not patched yet. Apply the patch first.")

    data_cave_va, data_cave_off = get_section_cave(data, sections, image_base, 'data', 80)

    # Backup
    backup = exe_path + '.bak'
    if not os.path.exists(backup):
        shutil.copy2(exe_path, backup)

    # Write floats
    struct.pack_into('<f', data, data_cave_off + CAVE_HEIGHT_VAL_OFFSET, height)
    struct.pack_into('<f', data, data_cave_off + CAVE_SHOULDER_VAL_OFFSET, shoulder)

    # Write strings
    max_factor_str = f"{max_distance:.2f}".encode('ascii').ljust(8, b'\x00')
    zoom_speed_str = f"{zoom_speed:.2f}".encode('ascii').ljust(8, b'\x00')
    data[data_cave_off + CAVE_MAX_FACTOR_STR_OFFSET : data_cave_off + CAVE_MAX_FACTOR_STR_OFFSET + 8] = max_factor_str
    data[data_cave_off + CAVE_ZOOM_SPEED_STR_OFFSET : data_cave_off + CAVE_ZOOM_SPEED_STR_OFFSET + 8] = zoom_speed_str

    # Update CVar default strings too
    cvar_height_def_bytes = f"{height:.2f}\x00".encode('ascii')
    cvar_shoulder_def_bytes = f"{shoulder:.2f}\x00".encode('ascii')
    data[data_cave_off + CAVE_HEIGHT_DEF_OFFSET : data_cave_off + CAVE_HEIGHT_DEF_OFFSET + len(cvar_height_def_bytes)] = cvar_height_def_bytes
    data[data_cave_off + CAVE_SHOULDER_DEF_OFFSET : data_cave_off + CAVE_SHOULDER_DEF_OFFSET + len(cvar_shoulder_def_bytes)] = cvar_shoulder_def_bytes

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
