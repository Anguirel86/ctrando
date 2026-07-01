"""Randomize who can equip what."""
from ctrando.arguments import gearrandooptions
from ctrando.common import ctenums, random
from ctrando.items import itemdata


_restrictions: tuple[ctenums.ItemID, ...] = (
    ctenums.ItemID.CHARM_TOP,
    ctenums.ItemID.BLACK_ROCK, ctenums.ItemID.BLUE_ROCK, ctenums.ItemID.SILVERROCK,
    ctenums.ItemID.WHITE_ROCK, ctenums.ItemID.GOLD_ROCK
)

def get_armor_type(item: itemdata.Item) -> gearrandooptions.ArmorTypes:
    boys_byte = 0x9A  # 0x80 | 0x10 | 0x08 | 0x02
    girls_byte = 0x64  # 0x40 | 0x20 | 0x04

    equip_byte = item.secondary_stats.get_equippable_by_byte()
    if equip_byte == girls_byte:
        return gearrandooptions.ArmorTypes.DRESS
    if equip_byte == boys_byte:
        return gearrandooptions.ArmorTypes.HEAVY_ARMOR
    if equip_byte == 0xFE:
        return gearrandooptions.ArmorTypes.NORMAL
    if bin(equip_byte).count("1") == 1:
        return gearrandooptions.ArmorTypes.PERSONAL

    raise ValueError


def apply_equip_type_rando(
        item_man: itemdata.ItemDB,
        equip_options: gearrandooptions.EquipRandoOptions,
        rng: random.RNGType
):
    item_classes: dict[gearrandooptions.ArmorTypes, list[ctenums.ItemID]] = {
        x: [] for x in gearrandooptions.ArmorTypes
    }

    boys_byte = 0x9A   # 0x80 | 0x10 | 0x08 | 0x02
    girls_byte = 0x64  # 0x40 | 0x20 | 0x04

    available_item_ids = (
        ctenums.ItemID(ind) for ind in range(ctenums.ItemID.HIDE_CAP, ctenums.ItemID.ACCESSORY_END_BC)
        if ctenums.ItemID(ind) not in _restrictions
    )
    for item_id in available_item_ids:
        item = item_man[item_id]
        armor_type = get_armor_type(item)
        equipped_by = item.secondary_stats.get_equipable_by()
        new_equipped_by: list[ctenums.CharID] = []
        for char_id in ctenums.CharID:
            if char_id in equipped_by:
                lose_chance = equip_options.equip_type_lose_chance_dict[(char_id, armor_type)]
                is_lost = rng.random() < lose_chance
                if not is_lost:
                    new_equipped_by.append(char_id)
            else:
                gain_chance = equip_options.equip_type_gain_chance_dict[(char_id, armor_type)]
                is_gained = rng.random() < gain_chance
                if is_gained:
                    new_equipped_by.append(char_id)

        item.secondary_stats.set_equipable_by(new_equipped_by)


def apply_equipable_rando(
        item_man: itemdata.ItemDB,
        equip_options: gearrandooptions.EquipRandoOptions
):
    ...


def main():
    from ctrando.common import ctrom
    import random
    ct_rom = ctrom.CTRom.from_file("/home/ross/Documents/ct.sfc")
    item_man = itemdata.ItemDB.from_rom(ct_rom.getbuffer())
    opts = gearrandooptions.EquipRandoOptions()

    apply_equip_type_rando(item_man, opts, random.Random("aasdfjhe4lajhblc"))
    pass


if __name__ == "__main__":
    main()