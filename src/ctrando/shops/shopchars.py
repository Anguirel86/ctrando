"""Module for implementing visible shop characters"""
from ctrando.asm.assemble import assemble, ASMList
from ctrando.asm.instructions import AddressingMode as AM
import ctrando.asm.instructions as inst
from ctrando.common import asmpatcher, byteops, ctrom

# $0D5F range stores character IDs
# $0D68 range stores index in the bottom display
# $73, $75 are counters used (I think) for equipability
# We want to write missing characters/indic into the rest of the ranges while
# not incrementing $73, $75

# Subroutine 0xC2E017 does palette mangling for out of party people
# Need to insert this at first load and when switching from equip to shop

#                      --------sub start--------
# C2816A  08             PHP
# C2816B  E2 30          SEP #$30
# C2816D  A2 00          LDX #$00
# C2816F  9B             TXY
# C28170  86 73          STX $73
# C28172  86 75          STX $75
# C28174  BD 80 29       LDA $2980,X
# C28177  30 10          BMI $C28189
# C28179  99 5F 0D       STA $0D5F,Y
# C2817C  8A             TXA
# C2817D  99 68 0D       STA $0D68,Y
# C28180  C8             INY
# C28181  E0 03          CPX #$03
# C28183  B0 02          BCS $C28187
# C28185  E6 73          INC $73
# C28187  E6 75          INC $75
# C28189  E8             INX
# C2818A  E0 09          CPX #$09
# C2818C  90 E6          BCC $C28174
# C2818E  28             PLP
# C2818F  60             RTS
#                      ----------------


_num_recruit_dir = 0x6A
def patch_shop_visibility(
    ct_rom: ctrom.CTRom
):
    """Add missing characters to shop display"""
    # When the routine finishes, Y has the index into the range.  X is temp looping
    # Possible temp addrs: $06, $08, $16, $18, $22
    #   - $06, $08, $16, $18 used as temp vars later on
    #   - $22 is zeroed and used in a later subroutine
    #   - Probably more, but it's scary.
    #   - Slow mult/div (0x2A-ish range) are probably safe too

    hook_rom_addr = 0xC2816A
    hook_addr = byteops.to_file_ptr(hook_rom_addr)
    return_rom_addr, return_addr = hook_rom_addr + 4, hook_addr + 4

    block_end = byteops.to_file_ptr(0xC28190)
    shop_pcid_start_abs = 0x0D5F
    shop_display_index_start_abs = 0x0D68
    max_range_check_dir = _num_recruit_dir  # 0x16
    old_rt: ASMList = [
        inst.PHP(),
        inst.SEP(0x30),
        inst.LDX(0x00, AM.IMM8),
        inst.TXY(),
        inst.STX(0x73, AM.DIR),
        inst.STX(0x75, AM.DIR),
        "start_loop",
        inst.LDA(0x2980, AM.ABS_X),
        inst.BMI("end_loop"),
        inst.STA(shop_pcid_start_abs, AM.ABS_Y),
        inst.TXA(),
        inst.STA(shop_display_index_start_abs, AM.ABS_Y),
        inst.INY(),
        inst.CPX(0x03, AM.IMM8),
        inst.BCS("skip_incr"),
        inst.INC(0x73, AM.DIR),
        "skip_incr",
        inst.INC(0x75, AM.DIR),
        "end_loop",
        inst.INX(),
        inst.CPX(0x09, AM.IMM8),
        inst.BCC("start_loop")
    ]

    rt: ASMList = [
        inst.STY(max_range_check_dir, AM.DIR),
        inst.LDA(0, AM.IMM8),
        inst.TAX(),
        "comp_loop_st",
        inst.CPY(7, AM.IMM8),
        inst.BCS("out"),
        inst.CMP(shop_pcid_start_abs, AM.ABS_X),
        inst.BEQ("comp_loop_end"),
        inst.INX(),
        inst.CPX(max_range_check_dir, AM.DIR),
        inst.BCC("comp_loop_st"),
        inst.STA(shop_pcid_start_abs, AM.ABS_Y),
        inst.PHA(),
        inst.TYA(),
        inst.STA(shop_display_index_start_abs, AM.ABS_Y),
        inst.PLA(),
        inst.INY(),
        "comp_loop_end",
        inst.CMP(6, AM.IMM8),
        inst.BCS("out"),
        inst.INC(mode=AM.NO_ARG),
        inst.LDX(0, AM.IMM8),
        inst.BRA("comp_loop_st"),
        "out",
        inst.PLP(),
        inst.JMP(return_rom_addr, AM.LNG)
    ]

    asmpatcher.apply_jmp_patch(
        old_rt+rt,
        # old_rt + [inst.PLP(), inst.JMP(return_rom_addr, AM.LNG)],
        hook_addr, ct_rom, return_addr)
    ct_rom.seek(return_addr)
    ct_rom.write(inst.RTS().to_bytearray())
    block_start = ct_rom.tell()
    ct_rom.space_manager.mark_block(
        (block_start, block_end), ctrom.freespace.FSWriteType.MARK_FREE
    )

    # print(block_end-block_start)

    modify_shop_palettes(ct_rom)

def modify_shop_palettes(
        ct_rom: ctrom.CTRom
):
    # First Load paleettes:
    # C28139  20 75 98       JSR $9875
    # C2D52B  20 CA DA       JSR $DACA  # Better

    # bank02_rt: ASMList = [
    #     inst.JSR(0xE058, AM.ABS),
    #     inst.RTL()
    # ]
    #
    # bank02_addr = asmpatcher.add_jsl_routine(
    #     bank02_rt, ct_rom, 0x020000, True
    #)
    # C2DB91  A9 2F          LDA #$2F
    # C2DB93  8D 13 0D       STA $0D13
    # C2DB96  28             PLP
    # C2DB97  60             RTS
    #                      ----------------

    orig_code: ASMList = [
        inst.LDA(0x2F, AM.IMM8),
        inst.STA(0x0D13, AM.ABS),
    ]

    new_gray_out_rt: ASMList = [
        # inst.SEP(0x20),
        # Old code
        # New code
        inst.LDX(0x1004, AM.IMM16),
        inst.STX(0x02, AM.DIR),
        inst.LDX(_num_recruit_dir, AM.DIR),
        inst.STX(0x04, AM.DIR),
        "loop_st",
        inst.LDX(0x04, AM.DIR),
        inst.LDA(0x104D, AM.ABS_X),
        inst.BMI("end"),
        inst.STA(0x00, AM.DIR),
        inst.JSL(0xFFF628, AM.LNG),
        inst.STX(0x00, AM.DIR),
        # inst.JSL(byteops.to_rom_ptr(bank02_addr), AM.LNG),
        inst.INC(0x04, AM.DIR),
        inst.LDA(0x04, AM.DIR),
        inst.CMP(0x1055, AM.ABS),
        inst.BCC("loop_st"),
        "end",
    ]

    rt = orig_code + new_gray_out_rt + [inst.PLP(), inst.JMP(0xC2DB97, AM.LNG)]

    asmpatcher.apply_jmp_patch(rt,
                               0x02DB91,
                               ct_rom, None, 0x410000)

    gray_out_rt_abs = 0xE017  # Bank C2
    hook_addr = 0x02D52B
    new_rt: ASMList = [
        inst.JSR(0xDACA, AM.ABS),
        inst.JSR(gray_out_rt_abs, AM.ABS),
        inst.RTS()
    ]

    # C2D6F9  A5 54          LDA $54
    # C2D6FB  85 79          STA $79
    # C2D6FD  A5 80          LDA $80
    # C2D6FF  85 54          STA $54

    orig_code = [
        inst.LDA(0x54, AM.DIR),
        inst.STA(0x79, AM.DIR),
    ]

    rt = new_gray_out_rt + orig_code + [inst.JMP(0xC2D6FD, AM.LNG)]
    asmpatcher.apply_jmp_patch(
        rt, 0x02D6F9, ct_rom
    )

