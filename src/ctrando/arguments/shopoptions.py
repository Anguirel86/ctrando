import argparse
import enum
import functools
import typing

from ctrando.arguments import argumenttypes
from ctrando.common import ctenums

class ShopInventoryType(enum.StrEnum):
    VANILLA = "vanilla"
    SHUFFLE = "shuffle"
    FULL_RANDOM = "full_random"
    TIERED_RANDOM = "tiered_random"


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
                available_pool=[
                    x for x in ctenums.ItemID if x not in cls.unused_items
                ]
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
        }

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        """Add Shop/Item options to parser."""
        group = parser.add_argument_group(
            "Shop/Item Options",
            "Items related to item prices and shop inventory"
        )

        argumenttypes.add_str_enum_to_group(
            group, "--shop-inventory-randomization",
            ShopInventoryType,
        )

        argumenttypes.add_str_enum_to_group(
            group, "--shop-capacity-randomization",
            ShopCapacityType,
            help_str=(
                "Only considered if --shop-inventory-randomization is"
                "not \"vanilla\" or \"shuffle\""
            )
        )

        group.add_argument(
            "--not-buyable-items",
            nargs="*",
            type=functools.partial(argumenttypes.str_to_enum, enum_type=ctenums.ItemID),
            default=argparse.SUPPRESS
        )

        group.add_argument(
            "--not-sellable-items",
            nargs="*",
            type=functools.partial(argumenttypes.str_to_enum, enum_type=ctenums.ItemID),
            default=argparse.SUPPRESS
        )

        argumenttypes.add_str_enum_to_group(
            group, "--item-base-prices",
            ItemBasePrice,
        )

        argumenttypes.add_str_enum_to_group(
            group, "--item-price-randomization",
            ItemSalePrice,
        )

        group.add_argument(
            "--item-price-min-multiplier",
            type=float, default=argparse.SUPPRESS,
            help="minimum price multiplier (default 0.50) that an item's price can roll"
        )

        group.add_argument(
            "--item-price-max-multiplier",
            type=float, default=argparse.SUPPRESS,
            help="maximum price multiplier (default 2.00) that an item's price can roll"
        )

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace):
        attr_names = [
            "shop_inventory_randomization", "shop_capacity_randomization",
            "not_buyable_items", "not_sellable_items",
            "item_base_prices",
            "item_price_randomization",
            "item_price_min_multiplier", "item_price_max_multiplier"
        ]

        init_dict: dict[str, typing.Any] = dict()

        for attr_name in attr_names:
            if hasattr(namespace, attr_name):
                init_dict[attr_name] = getattr(namespace, attr_name)

        return ShopOptions(**init_dict)
