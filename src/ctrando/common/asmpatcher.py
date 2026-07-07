from typing import Optional

from ctrando.asm import assemble, instructions as inst
from ctrando.asm.instructions import AddressingMode as AM
from ctrando.common import (byteops, ctrom, freespace)


def apply_jmp_patch(
        patch: assemble.ASMList,
        hook_addr: int,
        ct_rom: ctrom.CTRom,
        return_addr: Optional[int] = None,
        hint: int = 0
):
    """Apply patch at position which jumps and jumps back."""

    routine_b = assemble.assemble(patch)
    routine_addr = ct_rom.space_manager.get_free_addr(len(routine_b), hint)

    hook = [
        inst.JMP(byteops.to_rom_ptr(routine_addr), AM.LNG),
    ]
    hook_b = assemble.assemble(hook)

    ct_rom.seek(hook_addr)
    ct_rom.write(hook_b)
    if return_addr is not None:
        nop_len = return_addr - ct_rom.tell()
        payload = bytes.fromhex('EA'*nop_len)
        ct_rom.write(payload)

    ct_rom.seek(routine_addr)
    ct_rom.write(routine_b, freespace.FSWriteType.MARK_USED)


def add_jsl_routine(
        routine: assemble.ASMList,
        ct_rom: ctrom.CTRom,
        hint: int = 0,
        force_bank: bool = False
) -> int:
    """
    Adds a subroutine which should be called with JSL.
    Returns the file address (not rom) of the routine.
    """

    routine_b = assemble.assemble(routine)
    routine_addr = ct_rom.space_manager.get_free_addr(len(routine_b), hint)

    if force_bank and (routine_addr >> 16) != (hint >> 16):
        raise ctrom.freespace.FreeSpaceError(f"Not enough space in bank {hint >> 16:02X} (need {len(rt_b)})")


    ct_rom.seek(routine_addr)
    ct_rom.write(routine_b, freespace.FSWriteType.MARK_USED)


    return routine_addr


def apply_jsr_patch(
        jsr_routine: assemble.ASMList,
        ct_rom: ctrom.CTRom,
        hook_addr: int,
) -> int:
    """Insert a JSR to a new routine at hook_addr.  Returns routines addr."""

    rt_b = assemble.assemble(jsr_routine)
    rt_addr = ct_rom.space_manager.get_free_addr(
        len(rt_b), hook_addr & 0xFF0000
    )
    if rt_addr >> 16 != hook_addr >> 16:
        raise ctrom.freespace.FreeSpaceError(f"Not enough space in bank {hook_addr >> 16:02X} (need {len(rt_b)})")

    hook_b = inst.JSR(rt_addr & 0xFFFF, AM.ABS).to_bytearray()
    ct_rom.seek(rt_addr)
    ct_rom.write(rt_b, ctrom.freespace.FSWriteType.MARK_USED)

    ct_rom.seek(hook_addr)
    ct_rom.write(hook_b)
