"""Module for Gear Randomization Options"""
import argparse
from collections.abc import Iterable
import enum
import functools
import itertools
import typing

from ctrando.arguments import argumenttypes as aty
from ctrando.common.ctenums import ItemID, WeaponEffects as WE, BoostID
from ctrando.common import distribution, ctenums


class BronzeFistPolicy(enum.StrEnum):
    """Policies to Handle BronzeFist"""
    VANILLA = "vanilla"
    REMOVE = "remove"
    CRIT_4x = "4x_crit"
    RANDOM_OTHER = "random_other"


class DSItem(enum.Enum):
    """Possible DS Items from Gear Rando"""
    # Weapons
    DREAMSEEKER = enum.auto()
    # STARDUST_BOW = enum.auto()
    VENUS_BOW = enum.auto()
    TURBOSHOT = enum.auto()
    SPELLSLINGER = enum.auto()
    DRAGON_ARM = enum.auto()
    APOCALYPSE_ARM = enum.auto()
    DINOBLADE = enum.auto()
    JUDGEMENT_SCYTHE = enum.auto()
    DREAMREAPER = enum.auto()
    # Armors
    REPTITE_DRESS = enum.auto()
    DRAGON_ARMOR = enum.auto()
    REGAL_PLATE = enum.auto()
    REGAL_GOWN =  enum.auto()
    SHADOWPLUME_ROBE = enum.auto()
    ELEMENTAL_AEGIS = enum.auto()
    SAURIAN_LEATHERS = enum.auto()
    # Helmets
    DRAGONHEAD = enum.auto()
    REPTITE_TIARA = enum.auto()
    MASTERS_CROWN = enum.auto()
    ANGELS_TIARA = enum.auto()
    # Accessories
    VALOR_CREST = enum.auto()
    DRAGONS_TEAR = enum.auto()
    CHAMPIONS_BADGE = enum.auto()


_weapon_effect_symbol_dict: dict[str, list[WE]] = {
    "no_change": [WE.INVALID_NO_CHANGE],
    "none": [WE.NONE],
    "wonder": [WE.WONDERSHOT],
    "doom": [WE.DOOMSICKLE],
    "crisis": [WE.CRISIS],
    "stop_60": [WE.STOP_60],
    "slow_60": [WE.SLOW_60],
    "chaos_80": [WE.CHAOS_80],
    "stop_80_machines": [WE.STOP_80_MACHINES],
    "4x_crit": [WE.CRIT_4X],
    "9999_crit": [WE.CRIT_9999],
    "777_dmg": [WE.VENUS_BOW],
    "crisis_mp": [WE.SPELLSLINGER],
    "valiant": [WE.VALIANT],
    "mp_crit": [WE.MP_CRIT],
    "mp_crit4x": [WE.MP_CRIT4X],
    "hp_leech_5": [WE.HP_LEECH_5],
    "hp_leech_10": [WE.HP_LEECH_10],
    "mp_leech_2": [WE.MP_LEECH_2],
    "mp_leech_5": [WE.MP_LEECH_5],

}
_weapon_effect_dist_generator = distribution.DistributionGenerator[WE](_weapon_effect_symbol_dict)
def get_weapon_effect_distribution(spec_str: str):
    return _weapon_effect_dist_generator.generate_distribution(spec_str)


_boost_symbol_dict: dict[str, list[BoostID]] = {
    "no_change": [BoostID.INVALID_NO_CHANGE],
    "none": [BoostID.NOTHING],
    "speed_1": [BoostID.SPEED_1],
    "hit_2": [BoostID.HIT_2],
    "power_2": [BoostID.POWER_2],
    "stamina_2": [BoostID.STAMINA_2],
    "magic_2": [BoostID.MAGIC_2],
    "mdef_5": [BoostID.MDEF_5],
    "speed_3": [BoostID.SPEED_3],
    "hit_10": [BoostID.HIT_10],
    "power_6": [BoostID.POWER_6],
    "magic_6": [BoostID.MAGIC_6],
    "mdef_10": [BoostID.MDEF_10],
    "power_4": [BoostID.POWER_4],
    "speed_2": [BoostID.SPEED_2],
    "mdef_20": [BoostID.MDEF_20],
    "stamina_6": [BoostID.STAMINA_6],
    "magic_4": [BoostID.MAGIC_4],
    "mdef_12": [BoostID.MDEF_12],
    "magic_mdef_5": [BoostID.MAG_MDEF_5],
    "power_stamina_10": [BoostID.POWER_STAMINA_10],
    # MDEF_5_DUP = 0x14
    "mdef_stamina_10": [BoostID.MDEF_STAMINA_10],
    "mdef_9": [BoostID.MDEF_9],
    "magic_10": [BoostID.MAGIC_10],
    "power_10": [BoostID.POWER_10],
    "speed_power_3": [BoostID.SPD_POW_3],
    "power_5": [BoostID.POWER_5],
    "magic_5": [BoostID.MAGIC_5]
}
_boost_dist_generator = distribution.DistributionGenerator[BoostID](_boost_symbol_dict)
def get_stat_boot_distribution(spec_str: str):
    return _boost_dist_generator.generate_distribution(spec_str)


def weapon_pool_verify(in_string: str) -> ItemID:
    """return stringified weapon name + verificaion"""
    item_id = aty.str_to_enum(in_string, ItemID)
    if not 0 < item_id < ItemID.WEAPON_END_5A:
        raise ValueError(f"{in_string} is not a weapon")

    return item_id


class GearRandoWeaponPool(enum.StrEnum):
    NONE = "none"
    ALL = "all"
    CUSTOM = "custom"


class GearRandoScheme(enum.StrEnum):
    NO_CHANGE = "no_change"
    SHUFFLE = "shuffle"
    SHUFFLE_LINKED = "shuffle_linked"
    RANDOM = "random"


class WeaponRandoGroup:
    def __init__(
            self,
            pool: Iterable[ItemID],
            effect_scheme: GearRandoScheme,
            boost_scheme: GearRandoScheme,
            forced_effects: Iterable[WE],
            random_effect_spec: str,
            forced_boosts: Iterable[BoostID],
            random_boost_spec: str
    ):
        self.pool = pool
        self.effect_scheme = effect_scheme
        self.boost_scheme = boost_scheme
        self.forced_effects = list(forced_effects)
        self.random_effect_spec = random_effect_spec
        self.forced_boosts = list(forced_boosts)
        self.random_boost_spec = random_boost_spec


class GearRandoOptions:
    _default_weapon_pool: typing.ClassVar[tuple[ItemID, ...]] = tuple()
    _default_rando_scheme: typing.ClassVar[GearRandoScheme] = GearRandoScheme.SHUFFLE_LINKED
    # (
    #     ItemID.RAINBOW, ItemID.SHIVA_EDGE, ItemID.SWALLOW, ItemID.RED_KATANA, ItemID.SLASHER,
    #     ItemID.VALKERYE, ItemID.SIREN, ItemID.SONICARROW,
    #     ItemID.WONDERSHOT, ItemID.SHOCK_WAVE, ItemID.PLASMA_GUN,
    #     ItemID.TERRA_ARM, ItemID.CRISIS_ARM,
    #     ItemID.MASAMUNE_1, ItemID.MASAMUNE_2, ItemID.BRAVESWORD, ItemID.RUNE_BLADE, ItemID.DEMON_HIT, ItemID.PEARL_EDGE,
    #     ItemID.IRON_FIST, ItemID.BRONZEFIST,
    #     ItemID.DOOMSICKLE
    # )
    all_weapons: typing.ClassVar[tuple[ItemID,...]] = (
        ItemID.WOOD_SWORD, ItemID.IRON_BLADE, ItemID.STEELSABER, ItemID.LODE_SWORD,
        ItemID.RED_KATANA, ItemID.FLINT_EDGE, ItemID.DARK_SABER, ItemID.AEON_BLADE,
        ItemID.DEMON_EDGE, ItemID.ALLOYBLADE, ItemID.STAR_SWORD, ItemID.VEDICBLADE,
        ItemID.KALI_BLADE, ItemID.SHIVA_EDGE, ItemID.BOLT_SWORD, ItemID.SLASHER,
        ItemID.BRONZE_BOW, ItemID.IRON_BOW, ItemID.LODE_BOW, ItemID.ROBIN_BOW,
        ItemID.SAGE_BOW, ItemID.DREAM_BOW, ItemID.COMETARROW, ItemID.SONICARROW,
        ItemID.VALKERYE, ItemID.SIREN, ItemID.AIR_GUN, ItemID.DART_GUN,
        ItemID.AUTO_GUN, ItemID.PICOMAGNUM, ItemID.PLASMA_GUN, ItemID.RUBY_GUN,
        ItemID.DREAM_GUN, ItemID.MEGABLAST, ItemID.SHOCK_WAVE, ItemID.WONDERSHOT,
        ItemID.GRAEDUS, ItemID.TIN_ARM, ItemID.HAMMER_ARM, ItemID.MIRAGEHAND,
        ItemID.STONE_ARM, ItemID.DOOMFINGER, ItemID.MAGMA_HAND, ItemID.MEGATONARM,
        ItemID.BIG_HAND, ItemID.KAISER_ARM, ItemID.GIGA_ARM, ItemID.TERRA_ARM,
        ItemID.CRISIS_ARM, ItemID.BRONZEEDGE, ItemID.IRON_SWORD, ItemID.MASAMUNE_1,
        ItemID.FLASHBLADE, ItemID.PEARL_EDGE, ItemID.RUNE_BLADE, ItemID.BRAVESWORD,
        ItemID.MASAMUNE_2, ItemID.DEMON_HIT, ItemID.FIST, ItemID.FIST_2, ItemID.FIST_3,
        ItemID.IRON_FIST, ItemID.BRONZEFIST, ItemID.DARKSCYTHE, ItemID.HURRICANE,
        ItemID.STARSCYTHE, ItemID.DOOMSICKLE, ItemID.MOP, ItemID.SWALLOW,
        ItemID.SLASHER_2, ItemID.RAINBOW
    )
    _default_ds_item_pool: typing.ClassVar[tuple[DSItem]] = tuple(DSItem)
    _default_ds_replacement_chance: int = 50
    _default_bronze_fist_policy: typing.ClassVar[BronzeFistPolicy] = BronzeFistPolicy.VANILLA

    _default_forced_weapon_effects: typing.ClassVar[tuple[WE, ...]] = tuple()
    _default_forced_stat_boosts: typing.ClassVar[tuple[BoostID, ...]] = tuple()
    _default_random_weapon_effect_spec: typing.ClassVar[str] = (
        "80: none,"
        "15: [stop_60, chaos_80, slow_60],"
        "4: [4x_crit, wonder, doom, crisis, crisis_mp],"
        "1: [9999_crit, 777_dmg]"
    )
    _default_random_stat_boost_spec: typing.ClassVar[str] = (
        "64: none,"
        "20: [stamina_2, hit_2, magic_2, power_2],"
        "10: [stamina_6, power_4, magic_4, hit_10, mdef_5, speed_1],"
        "5: [power_stamina_10, mdef_stamina_10, mdef_12, speed_2, magic_10],"
        "1: [speed_3, mdef_20]"
    )

    _main_arg_names: typing.ClassVar[tuple[str, ...]] = (
        "ds_item_pool", "ds_replacement_chance", "bronze_fist_policy"
    )
    _weapon_group_arg_names = (
        "weapon_rando_pool", "weapon_rando_effect_scheme",
        "weapon_rando_stat_boost_scheme", "forced_weapon_effects",
        "forced_weapon_stat_boosts", "random_weapon_effect_spec",
        "random_weapon_stat_boost_spec"
    )

    def __init__(
            self,
            ds_item_pool: typing.Sequence[DSItem] = _default_ds_item_pool,
            ds_replacement_chance: int = _default_ds_replacement_chance,
            bronze_fist_policy: BronzeFistPolicy = _default_bronze_fist_policy,
            weapon_rando_pool: typing.Sequence[ItemID] = _default_weapon_pool,
            weapon_rando_effect_scheme: GearRandoScheme = _default_rando_scheme,
            weapon_rando_stat_boost_scheme: GearRandoScheme = _default_rando_scheme,
            forced_weapon_effects: Iterable[WE] = _default_forced_weapon_effects,
            forced_weapon_stat_boosts: Iterable[BoostID] = _default_forced_stat_boosts,
            random_weapon_effect_spec: str = _default_random_weapon_effect_spec,
            random_weapon_stat_boost_spec: str = _default_random_stat_boost_spec,
            **kwargs,
    ):
        self.ds_item_pool: tuple[DSItem, ...] = tuple(ds_item_pool)
        self.ds_replacement_chance = ds_replacement_chance
        self.weapon_rando_pool = weapon_rando_pool
        self.weapon_rando_scheme = weapon_rando_effect_scheme
        self.bronze_fist_policy = bronze_fist_policy

        self.rando_groups: list[WeaponRandoGroup] = [
            WeaponRandoGroup(
                weapon_rando_pool, weapon_rando_effect_scheme,
                weapon_rando_stat_boost_scheme,
                forced_weapon_effects, random_weapon_effect_spec,
                forced_weapon_stat_boosts, random_weapon_stat_boost_spec
            )
        ]
        group_ind = 2
        while True:
            suffix = f"_{group_ind}"
            arg_name = f"weapon_rando_pool"+suffix

            if arg_name in kwargs:
                pool = kwargs[arg_name]
                effect_scheme = kwargs.get("weapon_rando_effect_scheme"+suffix,
                                           self._default_rando_scheme)
                boost_scheme = kwargs.get("weapon_rando_stat_boost_scheme"+suffix,
                                          self._default_rando_scheme)
                forced_effects = kwargs.get("forced_weapon_effects"+suffix,
                                            self._default_forced_weapon_effects)
                random_effects = kwargs.get("random_weapon_effect_spec"+suffix,
                                            self._default_random_weapon_effect_spec)
                forced_boosts = kwargs.get("forced_weapon_stat_boosts" + suffix,
                                           self._default_forced_stat_boosts)
                random_boosts = kwargs.get("random_weapon_stat_boost_spec" + suffix,
                                           self._default_random_stat_boost_spec
                )
                self.rando_groups.append(
                    WeaponRandoGroup(pool, effect_scheme, boost_scheme, forced_effects, random_effects,
                                     forced_boosts, random_boosts)
                )
            else:
                break
            group_ind += 1

    @classmethod
    def get_argument_spec(cls) -> aty.ArgSpec:
        spec_dict = {
            "ds_item_pool": aty.arg_multiple_from_enum(
                DSItem, cls._default_ds_item_pool,"DS Items which may appear"
            ),
            "ds_replacement_chance": aty.DiscreteNumericalArg(
                0, 100, 5, cls._default_ds_replacement_chance,
                "Percent chance (e.g. 10 for 10 percent) to replace an item with a ds counterpart",
                type_fn=int
            ),
            "bronze_fist_policy": aty.arg_from_enum(
                BronzeFistPolicy, BronzeFistPolicy.VANILLA,
                "How to modify BronzeFist pre-shuffle"
            ),
        }
        for ind in range(3):
            suffix = "" if ind == 0 else f"_{ind+1}"
            group_dict= {
                "weapon_rando_pool"+suffix: aty.MultipleDiscreteSelection(
                    cls.all_weapons, cls._default_weapon_pool,
                    "Weapons whose effects will be shuffled",
                    choice_from_str_fn=functools.partial(aty.str_to_enum, enum_type=ItemID),
                    str_from_choice_fn=functools.partial(aty.enum_to_str, enum_type=ItemID)
                ),
                "weapon_rando_effect_scheme"+suffix: aty.arg_from_enum(
                    GearRandoScheme, cls._default_rando_scheme,
                    "How to randomize weapon effects", True
                ),
                "weapon_rando_stat_boost_scheme"+suffix: aty.arg_from_enum(
                    GearRandoScheme, cls._default_rando_scheme,
                    "How to randomize weapon stat boosts", True
                ),
                "forced_weapon_effects"+suffix: aty.MultipleDiscreteSelection(
                    _weapon_effect_dist_generator.singleton_dict.values(),
                    cls._default_forced_weapon_effects,
                    "Effects guaranteed to exist in the weapon rando pool",
                    lambda x: _weapon_effect_dist_generator.singleton_dict[x],
                    lambda x: _weapon_effect_dist_generator.singleton_dict_inv[x],
                    allow_duplicates=True
                ),
                "forced_weapon_stat_boosts"+suffix: aty.MultipleDiscreteSelection(
                    _boost_dist_generator.singleton_dict.values(),
                    cls._default_forced_stat_boosts,
                    "Stat boosts guaranteed to exist in the weapon rando pool",
                    lambda x: _boost_dist_generator.singleton_dict[x],
                    lambda x: _boost_dist_generator.singleton_dict_inv[x],
                    allow_duplicates=True
                ),
                "random_weapon_effect_spec"+suffix: aty.StringArgument(
                    "Distribution for choosing random effects after the forced ones",
                    _weapon_effect_dist_generator.validate_string,
                    cls._default_random_weapon_effect_spec
                ),
                "random_weapon_stat_boost_spec"+suffix: aty.StringArgument(
                    "Distribution for choosing random stat boosts after the forced ones",
                    _boost_dist_generator.validate_string,
                    cls._default_random_stat_boost_spec
                )
            }
            spec_dict.update(group_dict)

        return spec_dict

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):

        group = parser.add_argument_group(
            "Gear Randomization Options",
            "Options for how the stats of weapons may be randomized"
        )

        group.add_argument(
            "--ds-item-pool",
            nargs="*",
            help="DS Items which may appear.",
            type=functools.partial(aty.str_to_enum, enum_type=DSItem),
            default=argparse.SUPPRESS
        )

        group.add_argument(
            "--ds-replacement-chance",
            action="store", type=int,
            help="Percent chance (e.g. 10 for 10 percent) to replace an item with a ds counterpart.",
            default=argparse.SUPPRESS
        )

        aty.add_str_enum_to_group(group, "--bronze-fist-policy",
                                  BronzeFistPolicy,
                                  help_str="How to modify BronzeFist pre-shuffle")

        num_groups = 16
        spec_dict = cls.get_argument_spec()
        for ind in range(num_groups):
            suffix = "" if ind==0 else f"_{ind+1}"

            for arg_name in cls._weapon_group_arg_names:
                arg = spec_dict[arg_name]
                if ind != 0:
                    arg.help_text = argparse.SUPPRESS
                argparse_name = aty.attr_name_to_arg_name(arg_name+suffix)
                arg.add_to_argparse(argparse_name, group)



    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace) -> typing.Self:
        arg_names = list(cls._main_arg_names) + list(cls._weapon_group_arg_names)
        for ind in range(16):
            arg_names += [
                x+f"_{ind}" for x in cls._weapon_group_arg_names
            ]
        obj = aty.extract_from_namespace(cls,arg_names, namespace)
        return obj


class EquipRandoScheme(enum.StrEnum):
    VANILLA = "vanilla"
    RANDOM_TYPE = "random_type"
    RANDOM_ALL = "random_all"


class ArmorTypes(enum.StrEnum):
    NORMAL = "normal"
    DRESS = "dress"
    HEAVY_ARMOR = "heavy_armor"
    PERSONAL = "personal"

class EquipRandoOptions:
    _default_equipable_rando_scheme: typing.ClassVar[EquipRandoScheme] = EquipRandoScheme.VANILLA
    _default_char_gain_type_percent: typing.ClassVar[float] = 50.0
    _default_char_lose_type_percent: typing.ClassVar[float] = 50.0
    _default_gain_equip_percent: typing.ClassVar[float] = 50.0


    def __init__(
            self,
            equipable_rando_scheme: EquipRandoScheme = _default_equipable_rando_scheme,
            equip_type_gain_chance_dict: dict[tuple[ctenums.CharID, ArmorTypes], float] | None = None,
            equip_type_lose_chance_dict: dict[tuple[ctenums.CharID, ArmorTypes], float] | None = None,
            equip_chance_dict: dict[ctenums.CharID, float] | None = None
    ):
        self.equipable_rando_scheme = equipable_rando_scheme
        self.equip_type_gain_chance_dict =  {
            (char, armor_type): self._default_char_gain_type_percent
            for char, armor_type in itertools.product(ctenums.CharID, ArmorTypes)
        }
        if equip_type_gain_chance_dict is not None:
            self.equip_type_gain_chance_dict.update(equip_type_gain_chance_dict)

        self.equip_type_lose_chance_dict = {
            (char, armor_type): self._default_char_lose_type_percent
            for char, armor_type in itertools.product(ctenums.CharID, ArmorTypes)
        }
        if equip_type_lose_chance_dict is not None:
            self.equip_type_lose_chance_dict.update(equip_type_lose_chance_dict)

        self.equip_chance_dict = {
            char_id: self._default_gain_equip_percent for char_id in ctenums.CharID
        }
        if equip_chance_dict is not None:
            self.equip_chance_dict.update(equip_chance_dict)


    @classmethod
    def get_argument_spec(cls) -> aty.ArgSpec:
        spec: aty.ArgSpec = {
            "equipable_rando_scheme": aty.arg_from_enum(
                EquipRandoScheme, cls._default_equipable_rando_scheme,
                "Method for choosing who can equip what"
            )
        }

        for armor_type in ArmorTypes:
            if armor_type != ArmorTypes.NORMAL:
                modifiers = ["lose"]
            else:
                modifiers = ["gain", "lose"]

            chars = list(ctenums.CharID)
            for char, modifier in itertools.product(chars, modifiers):
                default = cls._default_char_gain_type_percent if modifier == "gain" \
                        else cls._default_char_lose_type_percent
                attr_name = f"{char.name.lower()}_{modifier}_equip_{armor_type}_percent"
                spec[attr_name] = aty.DiscreteNumericalArg(
                    0, 100, 5,
                    int(default),
                    f"Chance for {char.name.lower()} to {modifier} use of {armor_type} type gear (random_type scheme)",
                    type_fn=int
                )


        for char_id in ctenums.CharID:
            attr_name = f"{char_id.name.lower()}_can_equip_percent"
            spec[attr_name] = aty.DiscreteNumericalArg(
                0, 100, 5, int(cls._default_gain_equip_percent),
                f"Chance for {char_id.name.lower()} to be able to equip an armor (random_all scheme)",
                type_fn=int
            )

        return spec

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        group = parser.add_argument_group("Equipability Randomization Settings")
        for attr_name, arg in cls.get_argument_spec().items():
            arg_name = aty.attr_name_to_arg_name(attr_name)
            arg.add_to_argparse(arg_name, group)


    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace) -> typing.Self:
        equipable_rando_scheme = getattr(namespace, "equipable_rando_scheme", cls._default_equipable_rando_scheme)

        gain_equip_type_dict: dict[tuple[ctenums.CharID, ArmorTypes], float] = dict()
        lose_equip_type_dict: dict[tuple[ctenums.CharID, ArmorTypes], float] = dict()
        for char_id, armor_type in itertools.product(ctenums.CharID, ArmorTypes):
            char_name = char_id.name.lower()
            attr_name = f"{char_name}_gain_equip_{armor_type}_percent"
            if hasattr(namespace, attr_name):
                gain_equip_type_dict[(char_id, armor_type)] = getattr(namespace, attr_name)

            attr_name = f"{char_name}_lose_equip_{armor_type}_percent"
            if hasattr(namespace, attr_name):
                lose_equip_type_dict[(char_id, armor_type)] = getattr(namespace, attr_name)

        can_equip_dict: dict[ctenums.CharID, float] = dict()
        for char_id in ctenums.CharID:
            char_name = char_id.name.lower()
            attr_name = f"{char_name}_can_equip_percent"
            if hasattr(namespace, attr_name):
                can_equip_dict[char_id] = getattr(namespace, attr_name)


        return cls(equipable_rando_scheme, gain_equip_type_dict, lose_equip_type_dict, can_equip_dict)
