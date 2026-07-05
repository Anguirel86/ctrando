"""Randomize who can equip what."""
from ctrando.arguments import gearrandooptions
from ctrando.common import ctenums, random
from ctrando.items import itemdata


_restrictions: tuple[ctenums.ItemID, ...] = (
    ctenums.ItemID.CHARM_TOP,
    ctenums.ItemID.BLACK_ROCK, ctenums.ItemID.BLUE_ROCK, ctenums.ItemID.SILVERROCK,
    ctenums.ItemID.WHITE_ROCK, ctenums.ItemID.GOLD_ROCK,
    ctenums.ItemID.HELM_END_94, ctenums.ItemID.ARMOR_END_7B,
    ctenums.ItemID.ACCESSORY_END_BC
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


def get_armor_classes(item_man: itemdata.ItemDB) -> dict[int, list[ctenums.ItemID]]:

    ret_dict: dict[int, list[ctenums.ItemID]] = dict()
    available_item_ids = (
        ctenums.ItemID(ind) for ind in range(ctenums.ItemID.HIDE_TUNIC, ctenums.ItemID.ACCESSORY_END_BC)
        if ctenums.ItemID(ind) not in _restrictions
    )

    for item_id in available_item_ids:
        item = item_man[item_id]
        equip_byte = item.secondary_stats.get_equippable_by_byte()

        ret_dict[equip_byte] = ret_dict.get(equip_byte, []) + [item_id]

    return ret_dict


def apply_total_equip_rando(
        item_man: itemdata.ItemDB,
        equip_options: gearrandooptions.EquipRandoOptions,
        rng: random.RNGType
):
    available_item_ids = (
        ctenums.ItemID(ind) for ind in range(ctenums.ItemID.HIDE_CAP, ctenums.ItemID.ACCESSORY_END_BC)
        if ctenums.ItemID(ind) not in _restrictions
    )
    for item_id in available_item_ids:
        item = item_man[item_id]
        equip_chars: list[ctenums.CharID] = []
        for char_id in ctenums.CharID:
            gain_chance = equip_options.equip_chance_dict[char_id]
            if rng.random() < gain_chance:
                equip_chars.append(char_id)

        item.secondary_stats.set_equipable_by(equip_chars)


def apply_equip_type_rando(
        item_man: itemdata.ItemDB,
        equip_options: gearrandooptions.EquipRandoOptions,
        rng: random.RNGType
):
    item_classes = get_armor_classes(item_man)
    for armor_class, item_ids in item_classes.items():
        base_item = item_man[item_ids[0]]
        armor_type = get_armor_type(base_item)
        equipped_by = item_man[item_ids[0]].secondary_stats.get_equipable_by()

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

        for item_id in item_ids:
            item_man[item_id].secondary_stats.set_equipable_by(new_equipped_by)


def apply_equipable_rando(
        item_man: itemdata.ItemDB,
        equip_options: gearrandooptions.EquipRandoOptions,
        rng: random.RNGType
):
    if equip_options.equipable_rando_scheme == gearrandooptions.EquipRandoScheme.VANILLA:
        return

    if equip_options.equipable_rando_scheme == gearrandooptions.EquipRandoScheme.RANDOM_ALL:
        apply_total_equip_rando(item_man, equip_options, rng)
    elif equip_options.equipable_rando_scheme == gearrandooptions.EquipRandoScheme.RANDOM_TYPE:
        apply_equip_type_rando(item_man, equip_options, rng)
    else:
        raise ValueError
