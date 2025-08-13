"""Module for working with Weapon/Armor Effects"""
from collections.abc import Sequence
from io import BytesIO

from ctrando.asm import assemble, instructions as inst
from ctrando.asm.instructions import AddressingMode as AM
from ctrando.common import asmpatcher, byteops, cttypes as cty, ctrom
from ctrando.common.freespace import FSWriteType


class EffectMod(cty.SizedBinaryData):
    SIZE = 3
    ROM_RW = cty.AbsPointerRW(0x01EB3E) # C1EB3D  BF 05 2A CC    LDA $CC2A05,X

_vanilla_effect_start = 0x0C2A05
_vanilla_effect_count = 0x39
_max_vanilla_routine_index = 0x42

_current_damage_offset = 0xAD89
_current_attack_status_offset = 0xAE9B
_current_attacker_offset = 0xB1F4

_crown_offset = 0x5E51
_crown_bit = 0x80


def get_spellslinger_effect(effect_id: int, damage_divisor: int) -> EffectMod:
    if not 1 <= damage_divisor < 0xFF:
        raise ValueError
    return EffectMod(bytes([effect_id, 0, damage_divisor]))



def gather_vanilla_effects(ct_rom: ctrom.CTRom) -> list[EffectMod]:
    effects = [
        EffectMod.read_from_ctrom(ct_rom, ind) for ind in range(_vanilla_effect_count)
    ]

    return effects


def gather_new_effects_and_rts() -> tuple[list[EffectMod], list[assemble.ASMList]]:
    routines = [
        get_venus_bow_rt(),
        get_spellslinger_rt(),
    ]

    effects = [
        EffectMod(bytes([_max_vanilla_routine_index+1, 0, 0])),
        get_spellslinger_effect(_max_vanilla_routine_index+2, 2),
        # Armor
        EffectMod(bytes([0x26, 0x44, 0])),  # Shield + Barrier
        EffectMod(bytes([0, 0, 0])),        # Weird elem aegis exception
        EffectMod(bytes([0, 1, 0])),        # Crown
        EffectMod(bytes([0, 2, 0])),        # Tiara
    ]

    return effects, routines


def add_independent_sunshades_effect(ct_rom: ctrom.CTRom):
    """
    Adds an additional effect which grants +25% damage but is independent of
    the status granted by the sunshades.

    Notes
    -----
    Byte $5E51, X in player battle data is unused and unread/unwritten during
    battle.  We will make bit 0x80 of this data hook give the damage boost.
    """

    slow_mult_rom_addr = 0xC1FDBF
    slow_div_rom_addr = 0xC1FDD3

    # After damage calc:
    # - 8-bit A, 16-bit X/Y
    # - The damage is held in $2C.
    # The primspecs effect is here:
    #     C1E592  BD 4E 5E       LDA $5E4E,X
    #     C1E595  1D 53 5E       ORA $5E53,X
    #     C1E598  89 08          BIT #$08
    #     C1E59A  F0 1A          BEQ $C1E5B6
    #     C1E59C  A6 2C          LDX $2C
    #     C1E59E  86 28          STX $28
    #     C1E5A0  A2 02 00       LDX #$0002
    #     C1E5A3  86 2A          STX $2A
    #     C1E5A5  20 2A C9       JSR $C92A
    #     C1E5A8  A6 2C          LDX $2C
    #     C1E5AA  86 28          STX $28
    #     C1E5AC  A2 03 00       LDX #$0003
    #     C1E5AF  86 2A          STX $2A
    #     C1E5B1  20 0B C9       JSR $C90B
    #     C1E5B4  80 22          BRA $C1E5D8
    # --- Sunshades routine ---
    # Checking for poison status to reduce damage.  Hook here.
    hook_rom_addr = 0xC1E5D8
    hook_file_addr = byteops.to_file_ptr(hook_rom_addr)
    #     C1E5D8  AE F4 B1       LDX $B1F4
    #     C1E5DB  BD 4B 5E       LDA $5E4B,X
    return_rom_addr = 0xC1E5DE
    #     C1E5DE  89 40          BIT #$40

    # Coming in with 8-bit A and 16-bit X/Y
    rt: assemble.ASMList = [
        inst.LDA(_crown_offset, AM.ABS_X),
        inst.BIT(_crown_bit, AM.IMM8),
        inst.BEQ("end"),
        inst.LDX(0x2C, AM.DIR),
        inst.STX(0x28, AM.DIR),
        inst.LDX(0x0004, AM.IMM16),
        inst.STX(0x2A, AM.DIR),
        inst.JSL(slow_div_rom_addr, AM.LNG),
        inst.LDX(0x2C, AM.DIR),
        inst.STX(0x28, AM.DIR),
        inst.LDX(0x0005, AM.IMM16),
        inst.STX(0x2A, AM.DIR),
        inst.JSL(slow_mult_rom_addr, AM.LNG),
        "end",
        inst.LDX(0xB1F4, AM.ABS),
        inst.LDA(0x5E4B, AM.ABS_X),
        inst.JMP(return_rom_addr, AM.LNG)
    ]

    asmpatcher.apply_jmp_patch(rt, hook_file_addr, ct_rom, None, 0x410000)

def patch_additional_armor_effects(ct_rom: ctrom.CTRom,
                                   effect_mod_start_file: int ):
    """
    Allow armor effects to be more varied.

    Notes
    -----
    Current armor effects are XX YY 00
    - XX is an index into character stats
    - YY is a bitmask to OR with the given byte of stats
    - The third byte is always 00

    The change will have armor effects as XX YY ZZ
    - If XX != 00, perform the above routine (00 is not a valid target for a bitmask)
    - If XX == 00, use YY as a pointer to an effect routine and ZZ as an optional argument
    """

    effect_mod_start_rom = byteops.to_rom_ptr(effect_mod_start_file)

    # Armor effects all follow the same format, checked before battle.
    # FDB599  AD 77 5E       LDA $5E77          # Load "has effect" from equip
    # FDB59C  C9 01          CMP #$01
    # FDB59E  D0 18          BNE $FDB5B8        # If not, get out.
    # FDB5A0  AD 76 5E       LDA $5E76          # Load "effect_id" from equip
    # FDB5A3  0A             ASL
    # FDB5A4  18             CLC
    # FDB5A5  6D 76 5E       ADC $5E76          # Triple to find offset into effectmods
    # FDB5A8  AA             TAX
    # --- Hook here
    # FDB5A9  BF 6F 3B 41    LDA $413B6F,X      # Load byte 0  (offset)
    # --- Early return + 0x04 bytes
    # FDB5AD  A8             TAY
    # FDB5AE  B9 2D 5E       LDA $5E2D,Y
    # FDB5B1  1F 70 3B 41    ORA $413B70,X      # Or that byte of stat memory with byte 1
    # FDB5B5  99 2D 5E       STA $5E2D,Y        # Store back
    # --- Late return + 0x0F bytes
    return_rom_addr = 0xFDB5B8
    return_file_addr = byteops.to_file_ptr(return_rom_addr)
    # FDB5B8  AD F7 5E       LDA $5EF7

    def make_effect_rt(battle_index: int, hook_rom_addr: int):
        # Entering with
        # - 8 bit A, 16-bit X/Y
        # - Byte0 of EffectMod in A
        pc_stat_base = 0x5E2D + 0x80*battle_index
        local_crown_offset = _crown_offset - 0x5E2D
        local_status_offset = 0x5E50 - 0x5E2D
        local_haste_offset = local_status_offset + 2
        element_offset = 0x3F
        early_return_rom_addr = hook_rom_addr + 4
        late_return_rom_addr = hook_rom_addr + 15
        rt: assemble.ASMList = [
            inst.LDA(effect_mod_start_rom, AM.LNG_X),
            inst.CMP(0x00, AM.IMM8),
            inst.BEQ("new_rt"),
            inst.JMP(early_return_rom_addr, AM.LNG),
            "new_rt",
            # For now only aegis
            inst.LDA(effect_mod_start_rom+1, AM.LNG_X),
            inst.CMP(0x00, AM.IMM8),
            inst.BNE("crown"),
            inst.LDA(0x00, AM.IMM8),
            inst.STA(pc_stat_base + element_offset, AM.ABS),
            inst.STA(pc_stat_base + element_offset + 1, AM.ABS),
            inst.STA(pc_stat_base + element_offset + 2, AM.ABS),
            inst.STA(pc_stat_base + element_offset + 3, AM.ABS),
            inst.JMP(late_return_rom_addr, AM.LNG),
            "crown",
            inst.DEC(mode=AM.NO_ARG),
            inst.BNE("tiara"),
            inst.LDA(0x80, AM.IMM8),
            inst.TSB(pc_stat_base+local_crown_offset, AM.ABS),
            inst.LDA(0xFF, AM.IMM8),
            inst.TSB(pc_stat_base+local_status_offset, AM.ABS),
            inst.JMP(late_return_rom_addr, AM.LNG),
            "tiara",
            inst.DEC(mode=AM.NO_ARG),
            inst.BNE("end"),
            inst.LDA(0x80, AM.IMM8),
            inst.TSB(pc_stat_base + local_haste_offset, AM.ABS),
            inst.LDA(0xFF, AM.IMM8),
            inst.TSB(pc_stat_base + local_status_offset, AM.ABS),
            "end",
            inst.JMP(late_return_rom_addr, AM.LNG),

        ]
        return rt

    # FDB5A9  BF 6F 3B 41    LDA $413B6F,X  # PC0, armor
    # FDB5C8  BF 6F 3B 41    LDA $413B6F,X  # PC1, armor
    # FDB5E7  BF 6F 3B 41    LDA $413B6F,X  # PC2, armor
    # FDB607  BF 6F 3B 41    LDA $413B6F,X  # PC0, helm
    # FDB626  BF 6F 3B 41    LDA $413B6F,X  # PC1, helm
    # FDB645  BF 05 2A CC    LDA $CC2A05,X  # PC2, helm
    hook_pc_pairs: list[tuple[int, int]] = [
        (0xFDB5A9, 0),
        (0xFDB5C8, 1),
        (0xFDB5E7, 2),
        (0xFDB607, 0),
        (0xFDB626, 1),
        (0xFDB645, 2),
    ]

    for rom_hook, pc_id in hook_pc_pairs:
        file_hook = byteops.to_file_ptr(rom_hook)
        rt = make_effect_rt(pc_id, rom_hook)
        asmpatcher.apply_jmp_patch(rt, file_hook, ct_rom)




def expand_effect_mods(
        ct_rom: ctrom.CTRom,
):
    """
    Allow more effects.

    Notes
    -----
    You can't move everything to a new bank because there are too many bank $C1-local
    subroutines.  Effect data itself will move to another spot, but a different
    pointer table (different bank) is used for the new effects.
    """

    effects = gather_vanilla_effects(ct_rom)
    additional_effects, additional_effect_routines = gather_new_effects_and_rts()

    effects += additional_effects

    # Write out new effects.
    new_size = len(effects)*EffectMod.SIZE
    new_eff_start = ct_rom.space_manager.get_free_addr(
        new_size, 0x410000
    )

    payload = b''.join(x for x in effects)
    ct_rom.seek(new_eff_start)
    ct_rom.write(payload, FSWriteType.MARK_USED)

    addr_offset_dict: dict[int, int] = {
        # Weapon effects
        0x01EB2E: 1, 0x01EB36: 2, 0x01EB3E: 0,
        # Armor effects --
        # FDB5A9  BF 05 2A CC    LDA $CC2A05,X  # PC1
        # FDB5B1  1F 06 2A CC    ORA $CC2A06,X
        # 0x3DB5AA: 0,
        0x3DB5B2: 1,
        # FDB5C8  BF 05 2A CC    LDA $CC2A05,X  # PC2
        # FDB5D0  1F 06 2A CC    ORA $CC2A06,X
        # 0x3DB5C9: 0,
        0x3DB5D1: 1,
        # FDB5E7  BF 05 2A CC    LDA $CC2A05,X  # PC3
        # FDB5EF  1F 06 2A CC    ORA $CC2A06,X
        # 0x3DB5E8: 0,
        0x3DB5F0: 1,
        # Helm Effects --
        # FDB607  BF 05 2A CC    LDA $CC2A05,X  # PC1
        # FDB60F  1F 06 2A CC    ORA $CC2A06,X
        # 0x3DB608: 0,
        0x3DB610: 1,
        # FDB626  BF 05 2A CC    LDA $CC2A05,X  # PC2
        # FDB62E  1F 06 2A CC    ORA $CC2A06,X
        # 0x3DB627: 0,
        0x3DB62F: 1,
        # FDB645  BF 05 2A CC    LDA $CC2A05,X
        # FDB64D  1F 06 2A CC    ORA $CC2A06,X
        # 0x3DB646: 0,
        0x3DB64E: 1,
    }

    rom_addr = byteops.to_rom_ptr(new_eff_start)
    for addr, offset in addr_offset_dict.items():
        ct_rom.seek(addr)
        ct_rom.write(int.to_bytes(rom_addr+offset, 3, "little"))


    # C1EB3D  BF 05 2A CC    LDA $CC2A05,X
    # ----- Replace these four bytes
    # C1EB41  85 20          STA $20
    # C1EB43  0A             ASL
    # C1EB44  AA             TAX
    # -----
    # C1EB45  FC 61 FA       JSR ($FA61,X)
    # C1EB48  60             RTS
    hook_addr = 0x01EB41

    # 2) Collect the new effect routines
    effect_rts: list[bytes] = [
        assemble.assemble(routine) for routine in additional_effect_routines
    ]

    # 3) Allocate space for new routines
    effect_rt_lens: list[int] = [len(routine_b) for routine_b in effect_rts]

    def make_bank_switch_rt(ptr_table_rom_st: int):
        # Enter with 8-bit A, 16-bit X/Y
        effect_switch_rt: assemble.ASMList = [
            # Replace hook bytes
            inst.STA(0x20, AM.DIR),
            inst.CMP(_max_vanilla_routine_index + 1, AM.IMM8),
            inst.BCS("new_bank"),
            inst.ASL(mode=AM.NO_ARG),
            inst.TAX(),
            inst.JMP(0xC1EB45, AM.LNG),  # Back to vanilla JSR
            "new_bank",
            inst.SEC(),
            inst.SBC(_max_vanilla_routine_index+1, AM.IMM8),
            inst.ASL(mode=AM.NO_ARG),
            inst.TAX(),
            inst.JSR(ptr_table_rom_st & 0xFFFF, AM.ABS_X_16),
            inst.JMP(0xC1EB48, AM.LNG)  # To vanilla RTS
        ]
        return effect_switch_rt

    dummy_rt = make_bank_switch_rt(0)
    bank_switch_rt_size = len(assemble.assemble(dummy_rt))
    total_size = sum(effect_rt_lens) + 2 * len(effect_rts) + bank_switch_rt_size

    payload_addr = ct_rom.space_manager.get_free_addr(total_size, 0x410000)

    # 4) Write out the new routines
    real_bank_switch_rt = make_bank_switch_rt(byteops.to_rom_ptr(payload_addr))
    real_bank_switch_rt_b = assemble.assemble(real_bank_switch_rt)

    if additional_effect_routines:
        first_ptr = (payload_addr + len(additional_effect_routines) * 2) & 0xFFFF
        rt_b = b''.join(rt for rt in effect_rts)
        ptrs = [first_ptr]
        for length in effect_rt_lens[:-1]:
            ptrs.append(ptrs[-1] + length)

        ptr_b = b''.join(int.to_bytes(ptr, 2, "little")
                         for ptr in ptrs)
    else:
        rt_b = ptr_b = b''

    payload = ptr_b + rt_b + real_bank_switch_rt_b
    if len(payload) != total_size:
        print(len(payload), total_size, len(real_bank_switch_rt_b))
        raise ValueError


    bank_switch_addr = payload_addr + len(rt_b) + len(ptr_b)
    bank_switch_addr = byteops.to_rom_ptr(bank_switch_addr)
    hook: assemble.ASMList = [inst.JMP(byteops.to_rom_ptr(bank_switch_addr), AM.LNG)]
    hook_b = assemble.assemble(hook)

    ct_rom.seek(payload_addr)
    ct_rom.write(payload, FSWriteType.MARK_USED)

    ct_rom.seek(hook_addr)
    ct_rom.write(hook_b)

    patch_additional_armor_effects(ct_rom, new_eff_start)
    add_independent_sunshades_effect(ct_rom)


def get_venus_bow_rt() -> assemble.ASMList:
    rt: assemble.ASMList = [
        inst.LDX(777, AM.IMM16),
        inst.STX(_current_damage_offset, AM.ABS),
        inst.RTS()
    ]

    return rt


# Compare Crisis
#                      --------sub start--------
# C1F0D9  7B             TDC
# C1F0DA  AE F4 B1       LDX $B1F4  # Player ID
# C1F0DD  C2 20          REP #$20
# C1F0DF  BD 30 5E       LDA $5E30,X  # HP
# C1F0E2  85 28          STA $28
# C1F0E4  7B             TDC
# C1F0E5  E2 20          SEP #$20
# C1F0E7  A2 0A 00       LDX #$000A
# C1F0EA  86 2A          STX $2A
# C1F0EC  20 2A C9       JSR $C92A    # HP / 10
# C1F0EF  A6 32          LDX $32      # Remainder
# C1F0F1  86 28          STX $28
# C1F0F3  AE 89 AD       LDX $AD89    # Damage
# C1F0F6  86 2A          STX $2A
# C1F0F8  20 0B C9       JSR $C90B    # Remainder (1s dig) * Damage
# C1F0FB  A6 2C          LDX $2C      # Result
# C1F0FD  86 28          STX $28
# C1F0FF  A5 1E          LDA $1E      # 2nd Arg (3rd byte)
# C1F101  AA             TAX
# C1F102  86 2A          STX $2A
# C1F104  20 2A C9       JSR $C92A    # 1s dig * damage / arg
# C1F107  A6 2C          LDX $2C
# C1F109  8E 89 AD       STX $AD89    # Store result in damage
# C1F10C  60             RTS
#                      ----------------

def get_spellslinger_rt() -> assemble.ASMList:
    slow_mult_rom_addr = 0xC1FDBF
    slow_div_rom_addr = 0xC1FDD3

    mp_offset = 0x5E36

    rt: assemble.ASMList = [
        inst.TDC(),
        inst.LDX(_current_attacker_offset, AM.ABS),
        inst.REP(0x20),
        inst.LDA(mp_offset, AM.ABS_X),
        inst.STA(0x28, AM.DIR),
        inst.TDC(),
        inst.SEP(0x20),
        inst.LDX(0x000A, AM.IMM16),
        inst.STX(0x2A, AM.DIR),
        inst.JSL(slow_div_rom_addr, AM.LNG),
        inst.LDX(0x32, AM.DIR),  # rem
        inst.STX(0x28, AM.DIR),
        inst.LDX(_current_damage_offset, AM.ABS),
        inst.STX(0x2A, AM.DIR),
        inst.JSL(slow_mult_rom_addr, AM.LNG),
        inst.LDX(0x2C, AM.DIR),
        inst.STX(0x28, AM.DIR),
        inst.LDA(0x1E, AM.DIR),
        inst.TAX(),
        inst.STX(0x2A, AM.DIR),
        inst.JSL(slow_div_rom_addr, AM.LNG),
        inst.LDX(0x2C, AM.DIR),
        inst.STX(_current_damage_offset, AM.ABS),
        inst.RTS()
    ]

    return rt




def get_on_crit_rt() -> assemble.ASMList:
    """
    Add a routine that gives some effect on a critical hit.

    Notes
    -----
    EffectMod is XX YY ZZ (YY, ZZ args)
    - YY
    """
    rt: assemble.ASMList = [
        inst.LDA(_current_attack_status_offset, AM.ABS),
        inst.AND(0x80, AM.IMM8),
        inst.BEQ("end"),

        "end",
        inst.RTS()
    ]


if __name__ == "__main__":
    ct_rom = ctrom.CTRom.from_file("/home/ross/Documents/ct.sfc")

    start = EffectMod.ROM_RW.get_data_start_from_ctrom(ct_rom)
    print(f"{start:06X}")
    input()
    for ind in range(_vanilla_effect_count):
        effect = EffectMod.read_from_ctrom(ct_rom, ind)
        print(f"{ind:02X}: {effect}")
