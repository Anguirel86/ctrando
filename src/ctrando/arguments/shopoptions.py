import argparse
import enum
import functools
import typing

from ctrando.arguments import argumenttypes
from ctrando.common import ctenums, distribution
from ctrando.common.ctenums import ItemID


class ShopInventoryType(enum.StrEnum):
    VANILLA = "vanilla"
    SHUFFLE = "shuffle"
    FULL_RANDOM = "full_random"
    TIERED_RANDOM = "tiered_random"
    CUSTOM_RANDOM = "custom_random"


class ShopCapacityType(enum.StrEnum):
    VANILLA = "vanilla"
    SHUFFLE = "shuffle"
    RANDOM = "random"


class ItemBasePrice(enum.StrEnum):
    VANILLA = "vanilla"
    BALANCED = "balanced"
    MAX = "max"


class ItemSalePrice(enum.StrEnum):
    VANILLA = "vanilla"
    RANDOM = "random"
    RANDOM_MULTIPLIER = "random_multiplier"

_shop_keyword_dict: dict[str, typing.Sequence[ctenums.ItemID]] = {
    item_id.name.lower(): (item_id,) for item_id in ctenums.ItemID
}
_shop_keyword_dict.update({
    "all": tuple(x for x in ctenums.ItemID),
    "cons_all": tuple(x for x in ctenums.ItemID
                       if ctenums.ItemID.ACCESSORY_END_BC < x <ctenums.ItemID.PETAL),
    "gear_all": tuple(x for x in ctenums.ItemID if x < ctenums.ItemID.ACCESSORY_END_BC),
    "cons_d": (ctenums.ItemID.POWER_MEAL, ctenums.ItemID.TONIC),
    "cons_c": (
        ctenums.ItemID.MID_TONIC, ctenums.ItemID.SHELTER,
        ctenums.ItemID.REVIVE, ctenums.ItemID.HEAL,
    ),
    "cons_b": (ctenums.ItemID.FULL_TONIC, ctenums.ItemID.ETHER,
               ctenums.ItemID.ETHER),
    "cons_a": (
        ctenums.ItemID.MID_ETHER, ctenums.ItemID.POWER_TAB,
        ctenums.ItemID.MAGIC_TAB, ctenums.ItemID.LAPIS,
        ctenums.ItemID.SHIELD, ctenums.ItemID.BARRIER
    ),
    "cons_s": (
        ctenums.ItemID.FULL_ETHER, ctenums.ItemID.FULL_ETHER, ctenums.ItemID.FULL_ETHER,
        ctenums.ItemID.HYPERETHER, ctenums.ItemID.HYPERETHER,
        ctenums.ItemID.ELIXIR, ctenums.ItemID.ELIXIR,
        ctenums.ItemID.MEGAELIXIR
    ),
    "gear_starter": (
        ctenums.ItemID.HIDE_TUNIC, ctenums.ItemID.HIDE_CAP,
        ctenums.ItemID.KARATE_GI, ctenums.ItemID.WOOD_SWORD,
        ctenums.ItemID.BRONZEEDGE, ctenums.ItemID.AIR_GUN,
        ctenums.ItemID.BRONZE_BOW, ctenums.ItemID.TIN_ARM,
        ctenums.ItemID.DARKSCYTHE,
    ),
    "weapon_d": (
        ctenums.ItemID.IRON_BLADE, ctenums.ItemID.STEELSABER,
        ctenums.ItemID.LODE_SWORD, ctenums.ItemID.BOLT_SWORD,
        ctenums.ItemID.IRON_BOW, ctenums.ItemID.IRON_BOW,
        ctenums.ItemID.LODE_BOW, ctenums.ItemID.LODE_BOW,
        ctenums.ItemID.DART_GUN, ctenums.ItemID.DART_GUN,
        ctenums.ItemID.AUTO_GUN, ctenums.ItemID.AUTO_GUN,
    ) + (ctenums.ItemID.HAMMER_ARM, ctenums.ItemID.MIRAGEHAND)*2,
    "weapon_c": (
        ctenums.ItemID.RED_KATANA, ctenums.ItemID.FLINT_EDGE, ctenums.ItemID.AEON_BLADE,
        ctenums.ItemID.ROBIN_BOW, ctenums.ItemID.SAGE_BOW, ctenums.ItemID.SAGE_BOW,
        ctenums.ItemID.PLASMA_GUN, ctenums.ItemID.RUBY_GUN, ctenums.ItemID.RUBY_GUN,
        ctenums.ItemID.STONE_ARM, ctenums.ItemID.DOOMFINGER, ctenums.ItemID.MAGMA_HAND,
        ctenums.ItemID.FLASHBLADE, ctenums.ItemID.PEARL_EDGE, ctenums.ItemID.PEARL_EDGE
    ),
    "weapon_b": (
        ctenums.ItemID.DEMON_EDGE, ctenums.ItemID.ALLOYBLADE, ctenums.ItemID.STAR_SWORD,
        ctenums.ItemID.DREAM_BOW, ctenums.ItemID.COMETARROW, ctenums.ItemID.COMETARROW,
        ctenums.ItemID.DREAM_GUN, ctenums.ItemID.MEGABLAST, ctenums.ItemID.MEGABLAST,
        ctenums.ItemID.BIG_HAND, ctenums.ItemID.KAISER_ARM, ctenums.ItemID.GIGA_ARM,
        ctenums.ItemID.RUNE_BLADE, ctenums.ItemID.DEMON_HIT, ctenums.ItemID.BRAVESWORD
    ),
    "weapon_a": (
        ctenums.ItemID.VEDICBLADE, ctenums.ItemID.KALI_BLADE, ctenums.ItemID.SHIVA_EDGE,
        ctenums.ItemID.SLASHER_2,
    ) + (
        ctenums.ItemID.SONICARROW, ctenums.ItemID.SIREN
    )*2 + (
        ctenums.ItemID.SHOCK_WAVE, ctenums.ItemID.TERRA_ARM, ctenums.ItemID.BRAVESWORD,
        ctenums.ItemID.STARSCYTHE
    )*4,
    "weapon_s": (
        ctenums.ItemID.RAINBOW, ctenums.ItemID.VALKERYE, ctenums.ItemID.WONDERSHOT,
        ctenums.ItemID.CRISIS_ARM, ctenums.ItemID.DOOMSICKLE, ctenums.ItemID.MASAMUNE_2
    ),
    "armor_d": (
        ctenums.ItemID.BRONZEMAIL, ctenums.ItemID.MAIDENSUIT, ctenums.ItemID.IRON_SUIT,
        ctenums.ItemID.BRONZEHELM, ctenums.ItemID.IRON_HELM, ctenums.ItemID.BERET
    ),
    "armor_c": (
        ctenums.ItemID.TITAN_VEST, ctenums.ItemID.GOLD_SUIT, ctenums.ItemID.DARK_MAIL,
        ctenums.ItemID.MIST_ROBE, ctenums.ItemID.GOLD_HELM, ctenums.ItemID.ROCK_HELM,
    ),
    "armor_b": (
        ctenums.ItemID.RUBY_VEST, ctenums.ItemID.MESO_MAIL, ctenums.ItemID.LUMIN_ROBE,
        ctenums.ItemID.FLASH_MAIL, ctenums.ItemID.WHITE_VEST, ctenums.ItemID.BLACK_VEST,
        ctenums.ItemID.BLUE_VEST, ctenums.ItemID.RED_VEST, ctenums.ItemID.CERATOPPER,
        ctenums.ItemID.GLOW_HELM, ctenums.ItemID.TABAN_HELM
    ),
    "armor_a": (
        ctenums.ItemID.LODE_VEST, ctenums.ItemID.AEON_SUIT, ctenums.ItemID.TABAN_VEST, ctenums.ItemID.WHITE_MAIL,
        ctenums.ItemID.BLACK_MAIL, ctenums.ItemID.BLUE_MAIL, ctenums.ItemID.RED_MAIL,
        ctenums.ItemID.LODE_HELM, ctenums.ItemID.AEON_HELM, ctenums.ItemID.DOOM_HELM,
        ctenums.ItemID.DARK_HELM, ctenums.ItemID.RBOW_HELM, ctenums.ItemID.MERMAIDCAP,
        ctenums.ItemID.SIGHT_CAP, ctenums.ItemID.MEMORY_CAP, ctenums.ItemID.TIME_HAT
    ),
    "armor_s": (
        ctenums.ItemID.ZODIACCAPE, ctenums.ItemID.NOVA_ARMOR, ctenums.ItemID.PRISMDRESS,
        ctenums.ItemID.MOON_ARMOR, ctenums.ItemID.GLOOM_CAPE, ctenums.ItemID.TABAN_SUIT,
        ctenums.ItemID.VIGIL_HAT, ctenums.ItemID.PRISM_HELM, ctenums.ItemID.GLOOM_HELM,
        ctenums.ItemID.HASTE_HELM,ctenums.ItemID.SAFE_HELM
    ),
    "accessory_d": (ctenums.ItemID.WALLET, ctenums.ItemID.CHARM_TOP, ctenums.ItemID.THIRD_EYE),
    "accessory_c": (ctenums.ItemID.RIBBON, ctenums.ItemID.POWERGLOVE, ctenums.ItemID.DEFENDER, ctenums.ItemID.SIGHTSCOPE),
    "accessory_b": (
        ctenums.ItemID.BANDANA, ctenums.ItemID.POWERSCARF, ctenums.ItemID.MAGICSCARF,
        ctenums.ItemID.MUSCLERING, ctenums.ItemID.BERSERKER, ctenums.ItemID.RAGE_BAND
    ),
    "accessory_a": (
        ctenums.ItemID.HIT_RING, ctenums.ItemID.POWER_RING, ctenums.ItemID.MAGIC_RING,
        ctenums.ItemID.FRENZYBAND, ctenums.ItemID.WALL_RING, ctenums.ItemID.MAGIC_SEAL,
        ctenums.ItemID.SPEED_BELT, ctenums.ItemID.SILVERSTUD, ctenums.ItemID.SILVERERNG
    ),
    "accessory_s": (
        ctenums.ItemID.GREENDREAM, ctenums.ItemID.POWER_SEAL, ctenums.ItemID.GOLD_ERNG,
        ctenums.ItemID.GOLD_STUD, ctenums.ItemID.SUN_SHADES, ctenums.ItemID.PRISMSPECS,
        ctenums.ItemID.DASH_RING, ctenums.ItemID.AMULET, ctenums.ItemID.FLEA_VEST,
        ctenums.ItemID.DRAGON_TEAR, ctenums.ItemID.VALOR_CREST
    ) + (
        ctenums.ItemID.POWER_SEAL, ctenums.ItemID.POWER_SEAL,
        ctenums.ItemID.SUN_SHADES, ctenums.ItemID.FLEA_VEST,
    ),
    "rock": (
        ctenums.ItemID.BLUE_ROCK, ctenums.ItemID.BLACK_ROCK, ctenums.ItemID.GOLD_ROCK,
        ctenums.ItemID.WHITE_ROCK, ctenums.ItemID.SILVERROCK
    ),
    "key_nonprogression": (
        ctenums.ItemID.PETAL, ctenums.ItemID.FANG, ctenums.ItemID.HORN,
        ctenums.ItemID.FEATHER, ctenums.ItemID.PETALS_2, ctenums.ItemID.FANGS_2,
        ctenums.ItemID.HORNS_2, ctenums.ItemID.FEATHERS_2,
    ),
    "key_progression": (
        ctenums.ItemID.C_TRIGGER, ctenums.ItemID.CLONE, ctenums.ItemID.PENDANT,
        ctenums.ItemID.PENDANT_CHARGE, ctenums.ItemID.DREAMSTONE, ctenums.ItemID.RUBY_KNIFE,
        ctenums.ItemID.JETSOFTIME, ctenums.ItemID.TOOLS, ctenums.ItemID.RAINBOW_SHELL,
        ctenums.ItemID.PRISMSHARD, ctenums.ItemID.JERKY, ctenums.ItemID.JERKY,
        ctenums.ItemID.BENT_HILT, ctenums.ItemID.BENT_SWORD, ctenums.ItemID.HERO_MEDAL,
        ctenums.ItemID.MASAMUNE_1, ctenums.ItemID.TOMAS_POP, ctenums.ItemID.MOON_STONE,
        ctenums.ItemID.SUN_STONE, ctenums.ItemID.BIKE_KEY, ctenums.ItemID.SEED,
        ctenums.ItemID.GATE_KEY, ctenums.ItemID.RACE_LOG
    )
})
_shop_item_dist_generator = distribution.DistributionGenerator[ctenums.ItemID](
    _shop_keyword_dict
)
def get_shop_distribution(spec_str: str):
    return _shop_item_dist_generator.generate_distribution(spec_str)


class ShopOptions:
    _default_shop_inventory: typing.ClassVar[ShopInventoryType] = ShopInventoryType.VANILLA
    _default_shop_capacity: typing.ClassVar[ShopCapacityType] = ShopCapacityType.VANILLA
    _default_not_buyable: typing.ClassVar[tuple[ctenums.ItemID, ...]] = (
        ctenums.ItemID.SLASHER,
        ctenums.ItemID.MASAMUNE_1, ctenums.ItemID.MASAMUNE_2,
        ctenums.ItemID.BENT_HILT, ctenums.ItemID.BENT_SWORD,
        ctenums.ItemID.SLASHER_2, ctenums.ItemID.TABAN_VEST,
        ctenums.ItemID.TABAN_HELM, ctenums.ItemID.TABAN_SUIT,
        ctenums.ItemID.OZZIEPANTS, ctenums.ItemID.BANDANA,
        ctenums.ItemID.RIBBON, ctenums.ItemID.POWERGLOVE,
        ctenums.ItemID.DEFENDER, ctenums.ItemID.MAGICSCARF,
        ctenums.ItemID.AMULET, ctenums.ItemID.DASH_RING,
        ctenums.ItemID.HIT_RING, ctenums.ItemID.POWER_RING,
        ctenums.ItemID.MAGIC_RING, ctenums.ItemID.WALL_RING,
        ctenums.ItemID.SILVERERNG, ctenums.ItemID.GOLD_ERNG,
        ctenums.ItemID.SILVERSTUD, ctenums.ItemID.GOLD_STUD, ctenums.ItemID.SIGHTSCOPE,
        ctenums.ItemID.CHARM_TOP, ctenums.ItemID.RAGE_BAND,
        ctenums.ItemID.FRENZYBAND, ctenums.ItemID.THIRD_EYE,
        ctenums.ItemID.WALLET, ctenums.ItemID.GREENDREAM,
        ctenums.ItemID.BERSERKER, ctenums.ItemID.POWERSCARF,
        ctenums.ItemID.SPEED_BELT, ctenums.ItemID.BLACK_ROCK,
        ctenums.ItemID.BLUE_ROCK, ctenums.ItemID.SILVERROCK,
        ctenums.ItemID.WHITE_ROCK, ctenums.ItemID.GOLD_ROCK,
        ctenums.ItemID.HERO_MEDAL, ctenums.ItemID.MUSCLERING,
        ctenums.ItemID.FLEA_VEST, ctenums.ItemID.MAGIC_SEAL,
        ctenums.ItemID.POWER_SEAL, ctenums.ItemID.SUN_SHADES,
        ctenums.ItemID.PRISMSPECS, ctenums.ItemID.PETAL,
        ctenums.ItemID.HORN, ctenums.ItemID.FANG, ctenums.ItemID.FEATHER,
        ctenums.ItemID.SEED, ctenums.ItemID.BIKE_KEY, ctenums.ItemID.PENDANT,
        ctenums.ItemID.GATE_KEY, ctenums.ItemID.PRISMSHARD, ctenums.ItemID.C_TRIGGER,
        ctenums.ItemID.TOOLS, ctenums.ItemID.JERKY, ctenums.ItemID.RACE_LOG,
        ctenums.ItemID.MOON_STONE, ctenums.ItemID.SUN_STONE, ctenums.ItemID.DREAMSTONE,
        ctenums.ItemID.RUBY_KNIFE, ctenums.ItemID.YAKRA_KEY, ctenums.ItemID.CLONE,
        ctenums.ItemID.TOMAS_POP, ctenums.ItemID.PETALS_2, ctenums.ItemID.FANGS_2,
        ctenums.ItemID.HORNS_2, ctenums.ItemID.FEATHERS_2,
        ctenums.ItemID.PENDANT_CHARGE, ctenums.ItemID.RAINBOW_SHELL,
        ctenums.ItemID.JETSOFTIME,
        ctenums.ItemID.DRAGON_TEAR, ctenums.ItemID.VALOR_CREST,
    )
    forced_not_buyable: typing.ClassVar[tuple[ctenums.ItemID, ...]] = (
        ctenums.ItemID.MASAMUNE_1, ctenums.ItemID.MASAMUNE_2,
        ctenums.ItemID.BENT_HILT, ctenums.ItemID.BENT_SWORD,
        ctenums.ItemID.HERO_MEDAL,
        ctenums.ItemID.SEED, ctenums.ItemID.BIKE_KEY, ctenums.ItemID.PENDANT,
        ctenums.ItemID.GATE_KEY, ctenums.ItemID.PRISMSHARD, ctenums.ItemID.C_TRIGGER,
        ctenums.ItemID.TOOLS, ctenums.ItemID.JERKY, ctenums.ItemID.RACE_LOG,
        ctenums.ItemID.MOON_STONE, ctenums.ItemID.SUN_STONE, ctenums.ItemID.DREAMSTONE,
        ctenums.ItemID.RUBY_KNIFE, ctenums.ItemID.YAKRA_KEY, ctenums.ItemID.CLONE,
        ctenums.ItemID.TOMAS_POP,
        ctenums.ItemID.PENDANT_CHARGE, ctenums.ItemID.RAINBOW_SHELL,
        ctenums.ItemID.SCALING_LEVEL, ctenums.ItemID.JETSOFTIME
    )
    unused_items: typing.ClassVar[tuple[ctenums.ItemID, ...]] = (
        ctenums.ItemID.MASAMUNE_0_ATK, ctenums.ItemID.OBJECTIVE_1,
        ctenums.ItemID.OBJECTIVE_2, ctenums.ItemID.OBJECTIVE_3,
        ctenums.ItemID.OBJECTIVE_4, ctenums.ItemID.OBJECTIVE_5,
        ctenums.ItemID.OBJECTIVE_6, ctenums.ItemID.OBJECTIVE_7,
        ctenums.ItemID.OBJECTIVE_8, ctenums.ItemID.APITEM,
        ctenums.ItemID.UNUSED_4A, ctenums.ItemID.UNUSED_56,
        ctenums.ItemID.UNUSED_57, ctenums.ItemID.UNUSED_58,
        ctenums.ItemID.UNUSED_59, ctenums.ItemID.UNUSED_EC,
        ctenums.ItemID.UNUSED_ED, ctenums.ItemID.UNUSED_EE,
        ctenums.ItemID.UNUSED_EF, ctenums.ItemID.UNUSED_F0,
        ctenums.ItemID.UNUSED_F1,
        # maybe put these in a different category
        ctenums.ItemID.NONE, ctenums.ItemID.WEAPON_END_5A,
        ctenums.ItemID.ARMOR_END_7B, ctenums.ItemID.HELM_END_94,
        ctenums.ItemID.ACCESSORY_END_BC,
        ctenums.ItemID.SCALING_LEVEL,
        ctenums.ItemID.BUCKETFRAG
    )
    _default_item_base_price: typing.ClassVar[ItemBasePrice] = ItemBasePrice.VANILLA
    _default_item_price: typing.ClassVar[ItemSalePrice] = ItemSalePrice.VANILLA
    _default_item_price_min_multiplier: typing.ClassVar[float] = 0.5
    _default_item_price_max_multiplier: typing.ClassVar[float] = 2.0
    _default_item_price_randomization_exclusions: typing.ClassVar[list[ctenums.ItemID]] = []
    _default_guaranteed_shop_items: typing.ClassVar[tuple[ctenums.ItemID, ...]] = tuple()
    _default_shop_item_spec: str = """
    30: [cons_c], 5: [cons_b], 2: [cons_a], 1:[cons_s],
    5: [weapon_d], 10: [weapon_c], 5: [weapon_b], 2: [weapon_a], 1:[weapon_s],
    5: [armor_d], 10: [armor_c], 5: [armor_b], 2:[armor_a], 1:[ armor_s],
    5: [accessory_d], 10: [accessory_c],
    5: [accessory_b], 2:[accessory_a], 1:[accessory_s],
    1: [rock],
    1: [key_progression],
    2: [key_nonprogression],
    """
    _default_shop_item_dist: distribution.Distribution[ctenums.ItemID] = get_shop_distribution(
        _default_shop_item_spec
    )
    _default_show_all_chars_in_shop: typing.ClassVar[bool] = False

    def __init__(
            self,
            shop_inventory_randomization: ShopInventoryType = _default_shop_inventory,
            shop_capacity_randomization: ShopCapacityType = _default_shop_capacity,
            not_buyable_items: typing.Optional[list[ctenums.ItemID]] = None,
            not_sellable_items: typing.Optional[list[ctenums.ItemID]] = None,
            item_base_prices: ItemBasePrice = _default_item_base_price,
            item_price_randomization: ItemSalePrice = _default_item_price,
            item_price_min_multiplier: float = _default_item_price_min_multiplier,
            item_price_max_multiplier: float = _default_item_price_max_multiplier,
            item_price_randomization_exclusions: typing.Optional[list[ctenums.ItemID]] = None,
            guaranteed_shop_items: typing.Sequence[ctenums.ItemID] = _default_guaranteed_shop_items,
            custom_shop_item_spec: distribution.Distribution[ctenums.ItemID] = _default_shop_item_dist,
            show_all_chars_in_shop: bool = _default_show_all_chars_in_shop
    ):
        self.shop_inventory_randomization = shop_inventory_randomization
        self.shop_capacity_randomization = shop_capacity_randomization

        if not_buyable_items is None:
            not_buyable_items = self._default_not_buyable
        self.not_buyable_items = list(not_buyable_items)

        if not_sellable_items is None:
            not_sellable_items = self._default_not_buyable
        self.not_sellable_items = list(not_sellable_items)

        self.item_base_prices = item_base_prices
        self.item_price_randomization = item_price_randomization

        if item_price_min_multiplier <= 0:
            raise ValueError

        if item_price_max_multiplier <= 0 or item_price_max_multiplier < item_price_min_multiplier:
            raise ValueError

        self.item_price_min_multiplier = item_price_min_multiplier
        self.item_price_max_multiplier = item_price_max_multiplier

        if item_price_randomization_exclusions is None:
            item_price_randomization_exclusions = list(self._default_item_price_randomization_exclusions)
        self.item_price_randomization_exclusions = list(item_price_randomization_exclusions)

        self.guaranteed_shop_items = list(guaranteed_shop_items)
        self.custom_shop_item_spec = custom_shop_item_spec
        self.show_all_chars_in_shop = show_all_chars_in_shop

    @classmethod
    def get_argument_spec(cls) -> argumenttypes.ArgSpec:

        available_item_pool = [x for x in ctenums.ItemID
                               if x not in cls.unused_items]

        return {
            "shop_inventory_randomization": argumenttypes.arg_from_enum(
                ShopInventoryType, cls._default_shop_inventory,
                help_text="How shop inventory should be randomized"
            ),
            "shop_capacity_randomization": argumenttypes.arg_from_enum(
                ShopCapacityType, cls._default_shop_capacity,
                help_text="How shop capacity should be randomized"
            ),
            "not_buyable_items": argumenttypes.arg_multiple_from_enum(
                ctenums.ItemID, cls._default_not_buyable,
                help_text="Items which can never appear in shops",
                # available_pool=[
                #     x for x in ctenums.ItemID if x not in cls.unused_items
                # ]
            ),
            "not_sellable_items": argumenttypes.arg_multiple_from_enum(
                ctenums.ItemID, cls._default_not_buyable,
                help_text="Items which can never be sold",
                available_pool=[
                    x for x in ctenums.ItemID if x not in cls.unused_items
                ]
            ),
            "item_base_prices": argumenttypes.arg_from_enum(
                ItemBasePrice, ItemBasePrice.VANILLA,
                help_text="Unmodified price of items"
            ),
            "item_price_randomization": argumenttypes.arg_from_enum(
                ItemSalePrice, ItemSalePrice.VANILLA,
                help_text="How item prices should be randomized"
            ),
            "item_price_min_multiplier": argumenttypes.DiscreteNumericalArg(
                0.05, 10.00, 0.05, cls._default_item_price_min_multiplier,
                "minimum price multiplier that an item's price can roll",
                type_fn=float
            ),
            "item_price_max_multiplier": argumenttypes.DiscreteNumericalArg(
                0.05, 10.00, 0.05, cls._default_item_price_max_multiplier,
                "maximum price multiplier that an item's price can roll",
                type_fn=float
            ),
            "guaranteed_shop_items": argumenttypes.arg_multiple_from_enum(
                ctenums.ItemID, cls._default_guaranteed_shop_items,
                "Items guaranteed to appear in some shop",
                available_pool=[
                    x for x in ctenums.ItemID if x not in cls.unused_items
                ],
                allow_duplicates=True
            ),
            "custom_shop_item_spec": argumenttypes.StringArgument(
                "Distribution for shop items",
                parser=get_shop_distribution,
                default_value="""
                30: [cons_c], 5: [cons_b], [2:cons_a], [1: cons_s],
                5: [weapon_d], 10: [weapon_c], 5: [weapon_b], [2:weapon_a], [1: weapon_s],
                5: [armor_d], 10: [armor_c], 5: [armor_b], [2:armor_a], [1: armor_s],
                5: [accessory_d], 10: [accessory_c],
                5: [accessory_b], [2:accessory_a], [1: accessory_s],
                1: [accessory_rock]
                1: [key_progression]
                2: [key_nonprogression]
                """
            ),
            "show_all_chars_in_shop": argumenttypes.FlagArg(
                "All characters will be shown when shopping."
            )
        }

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        """Add Shop/Item options to parser."""

        group = parser.add_argument_group(
            "Shop/Item Options",
            "Items related to item prices and shop inventory"
        )

        for attr_name, arg in cls.get_argument_spec().items():
            arg.add_to_argparse(
                argumenttypes.attr_name_to_arg_name(attr_name),
                group
            )

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace):
        return argumenttypes.extract_from_namespace(
            cls, arg_names=cls.get_argument_spec().keys(), namespace=namespace
        )
