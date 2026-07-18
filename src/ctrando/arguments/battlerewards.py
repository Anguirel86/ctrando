import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import enum
import typing

from ctrando.arguments import argumenttypes
from ctrando.common import ctenums, distribution


class EnemyPoolType(enum.StrEnum):
    VANILLA = "vanilla"
    ALL = "all"
    MIDBOSSES = "midbosses"
    BOSSES = "bosses"
    BOSSES_NO_LAVOS = "bosses_no_lavos"
    NORMAL_ENEMIES = "normal_enemies"
    HARD_ENEMIES = "hard_enemies"
    CUSTOM = "custom"


class RewardPoolType(enum.StrEnum):
    VANILLA = "vanilla"
    SHUFFLE = "shuffle"
    RANDOM = "random"


_unusable_items: frozenset[ctenums.ItemID] = frozenset([
    ctenums.ItemID.SCALING_LEVEL, ctenums.ItemID.OBJECTIVE_1,
    ctenums.ItemID.OBJECTIVE_2, ctenums.ItemID.OBJECTIVE_3, ctenums.ItemID.OBJECTIVE_4,
    ctenums.ItemID.OBJECTIVE_5, ctenums.ItemID.OBJECTIVE_6, ctenums.ItemID.OBJECTIVE_7,
    ctenums.ItemID.OBJECTIVE_7, ctenums.ItemID.OBJECTIVE_8, ctenums.ItemID.APITEM,
    ctenums.ItemID.MASAMUNE_0_ATK,
    ctenums.ItemID.UNUSED_56, ctenums.ItemID.UNUSED_57, ctenums.ItemID.UNUSED_58,
    ctenums.ItemID.UNUSED_59, ctenums.ItemID.WEAPON_END_5A, ctenums.ItemID.ARMOR_END_7B,
    ctenums.ItemID.HELM_END_94, ctenums.ItemID.ACCESSORY_END_BC,
    ctenums.ItemID.UNUSED_EC, ctenums.ItemID.UNUSED_ED,
    ctenums.ItemID.UNUSED_EE, ctenums.ItemID.UNUSED_EF, ctenums.ItemID.UNUSED_F0,
    ctenums.ItemID.UNUSED_F1,]
)
def get_unusable_items() -> frozenset[ctenums.ItemID]:
    return _unusable_items


class RewardGroup(typing.Protocol):
    def get_enemy_pool_type(self) -> EnemyPoolType:
        ...

    def get_reward_pool_type(self) -> RewardPoolType:
        ...

    def get_rate(self) -> float:
        ...

    def get_custom_enemy_pool(self) -> Sequence[ctenums.EnemyID]:
        ...

    def get_custom_reward_pool(self) -> distribution.Distribution[ctenums.ItemID] | None:
        ...

    def get_stat_attr_name(self) -> str:
        ...



@dataclass()
class DropGroup:
    drop_enemy_pool: EnemyPoolType
    drop_reward_pool: RewardPoolType
    drop_rate: float = 1.0
    custom_drop_enemy_pool: Sequence[ctenums.EnemyID] = tuple()
    custom_drop_reward_pool: distribution.Distribution[ctenums.ItemID] | None = None

    def get_enemy_pool_type(self) -> EnemyPoolType:
        return self.drop_enemy_pool

    def get_reward_pool_type(self) -> RewardPoolType:
        return self.drop_reward_pool

    def get_rate(self) -> float:
        return self.drop_rate

    def get_custom_enemy_pool(self) -> Sequence[ctenums.EnemyID]:
        return list(self.custom_drop_enemy_pool)

    def get_custom_reward_pool(self) -> distribution.Distribution[ctenums.ItemID] | None:
        return self.custom_drop_reward_pool

    def get_stat_attr_name(self) -> str:
        return "drop_item"

    @staticmethod
    def make_group_attr_name(attr_name: str, index: int):
        suffix = f"_{index + 1}" if index > 0 else ""
        return attr_name+suffix

    @classmethod
    def get_argument_spec(cls, ind: int = 0) -> argumenttypes.ArgSpec:
        ret_dict: dict[str, argumenttypes.Argument] = {}
        suffix = f"_{ind + 1}" if ind > 0 else ""

        group_suffix = f"(Group {ind + 1})"

        default_enemy_pool = EnemyPoolType.VANILLA if ind == 0 else EnemyPoolType.CUSTOM
        ret_dict["drop_enemy_pool" + suffix] = argumenttypes.arg_from_enum(
            EnemyPoolType, default_enemy_pool,
            "Pool of enemies which can have a dropped item " + group_suffix,
        )

        default_reward_pool = RewardPoolType.VANILLA
        ret_dict["drop_reward_pool" + suffix] = argumenttypes.arg_from_enum(
            RewardPoolType, default_reward_pool,
            "Method of choosing enemy dropped items " + group_suffix,
        )

        ret_dict["drop_rate" + suffix] = argumenttypes.DiscreteNumericalArg(
            0.0, 1.0, 0.01, 1.0,
            "Percentage (decimal) of enemies in the drop pool which have a dropped item " + group_suffix,
            type_fn=float
        )

        ret_dict["custom_drop_enemy_pool" + suffix] = argumenttypes.arg_multiple_from_enum(
            ctenums.EnemyID, tuple(),
            f"Enemies for group {ind} drops",
            allow_duplicates=False
        )

        # ret_dict["custom_drop_reward_pool" + suffix] = argumenttypes.arg_multiple_from_enum(
        #     ctenums.ItemID, tuple(),
        #     f"Custom rewards for group {ind} drops",
        #     available_pool=[x for x in ctenums.ItemID if x not in _unusable_items],
        #     allow_duplicates=True
        # )

        ret_dict["custom_drop_reward_pool" + suffix] = argumenttypes.DistArgument(
            ctenums.ItemID, None,
            f"Custom rewards for group {ind} drops",
            available_pool=[x for x in ctenums.ItemID if x not in _unusable_items],
            keyword_dict=dict()
        )

        return ret_dict

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace, ind: int = 0):
        base_spec = cls.get_argument_spec(0)
        group_spec = cls.get_argument_spec(ind)

        kwargs: dict[str, typing.Any] = dict()

        for attr_name in base_spec.keys():
            group_attr_name = cls.make_group_attr_name(attr_name, ind)
            default = group_spec[group_attr_name].default_value
            kwargs[attr_name] = getattr(namespace, group_attr_name, default)

        return DropGroup(**kwargs)


@dataclass()
class CharmGroup:
    charm_enemy_pool: EnemyPoolType
    charm_reward_pool: RewardPoolType
    charm_rate: float = 1.0
    custom_charm_enemy_pool: Sequence[ctenums.EnemyID] = tuple()
    custom_charm_reward_pool: Sequence[ctenums.ItemID] = tuple()

    def get_enemy_pool_type(self) -> EnemyPoolType:
        return self.charm_enemy_pool

    def get_reward_pool_type(self) -> RewardPoolType:
        return self.charm_reward_pool

    def get_rate(self) -> float:
        return self.charm_rate

    def get_custom_enemy_pool(self) -> Sequence[ctenums.EnemyID]:
        return list(self.custom_charm_enemy_pool)

    def get_custom_reward_pool(self) -> Sequence[ctenums.ItemID]:
        return self.custom_charm_reward_pool

    def get_stat_attr_name(self) -> str:
        return "charm_item"

    @staticmethod
    def make_group_attr_name(attr_name: str, index: int):
        suffix = f"_{index + 1}" if index > 0 else ""
        return attr_name+suffix

    @classmethod
    def get_argument_spec(cls, ind: int = 0) -> argumenttypes.ArgSpec:
        ret_dict: dict[str, argumenttypes.Argument] = {}
        suffix = f"_{ind + 1}" if ind > 0 else ""

        group_suffix = f"(Group {ind + 1})"

        default_enemy_pool = EnemyPoolType.VANILLA if ind == 0 else EnemyPoolType.CUSTOM
        ret_dict["charm_enemy_pool" + suffix] = argumenttypes.arg_from_enum(
            EnemyPoolType, default_enemy_pool,
            "Pool of enemies which can have a charmable item " + group_suffix,
        )

        default_reward_pool = RewardPoolType.VANILLA
        ret_dict["charm_reward_pool" + suffix] = argumenttypes.arg_from_enum(
            RewardPoolType, default_reward_pool,
            "Method of choosing enemy charmable items " + group_suffix,
        )

        ret_dict["charm_rate" + suffix] = argumenttypes.DiscreteNumericalArg(
            0.0, 1.0, 0.01, 1.0,
            "Percentage (decimal) of enemies in the charm pool which have a charmable item " + group_suffix,
            type_fn=float
        )

        ret_dict["custom_charm_enemy_pool" + suffix] = argumenttypes.arg_multiple_from_enum(
            ctenums.EnemyID, tuple(),
            f"Enemies for group {ind} charms",
            allow_duplicates=False
        )

        ret_dict["custom_charm_reward_pool" + suffix] = argumenttypes.DistArgument(
            ctenums.ItemID, None,
            f"Custom rewards for group {ind} charms",
            available_pool=[x for x in ctenums.ItemID if x not in _unusable_items],
            keyword_dict=dict()
        )

        # ret_dict["custom_charm_reward_pool" + suffix] = argumenttypes.arg_multiple_from_enum(
        #     ctenums.ItemID, tuple(),
        #     f"Custom rewards for group {ind} charms",
        #     available_pool=[x for x in ctenums.ItemID if x not in _unusable_items],
        #     allow_duplicates=True
        # )

        return ret_dict

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace, ind: int = 0):
        base_spec = cls.get_argument_spec(0)
        group_spec = cls.get_argument_spec(ind)

        kwargs: dict[str, typing.Any] = dict()

        for attr_name in base_spec.keys():
            group_attr_name = cls.make_group_attr_name(attr_name, ind)
            default = group_spec[group_attr_name].default_value
            kwargs[attr_name] = getattr(namespace, group_attr_name, default)

        return CharmGroup(**kwargs)



class DropOptions:
    _default_mark_dropping_enemies: typing.ClassVar[bool] = False
    description: typing.ClassVar[str] = "Settings which modify enemy drops"

    def __init__(
            self,
            drop_groups: Sequence[DropGroup] | None = None,
            mark_dropping_enemies=_default_mark_dropping_enemies
    ):
        if drop_groups is None:
            drop_groups = [
                DropGroup.extract_from_namespace(argparse.Namespace(), 0)]

        self.drop_groups = list(drop_groups)
        self.mark_dropping_enemies = mark_dropping_enemies

    @classmethod
    def get_argument_spec(cls) -> argumenttypes.ArgSpec:
        ret_dict: dict[str, argumenttypes.Argument] = {}

        for ind in range(4):
            group_dict = DropGroup.get_argument_spec(ind)
            ret_dict.update(group_dict)

        attr_name = "mark_dropping_enemies"
        ret_dict[attr_name] = argumenttypes.FlagArg(
            "Append a \"D\" to enemy names which have a drop")

        return ret_dict

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        """Adds this as a group to the parser."""
        group = parser.add_argument_group(
            title="Enemy Drop Settings",
            description=cls.description
        )

        arg_spec = cls.get_argument_spec()
        for attr_name, arg in arg_spec.items():
            arg_name = argumenttypes.attr_name_to_arg_name(attr_name)
            arg.add_to_argparse(arg_name, group)

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace):
        groups: list[DropGroup] = []
        for ind in range(4):
            groups.append(
                DropGroup.extract_from_namespace(namespace, ind)
            )

        mark_enemy_drops = getattr(namespace, "mark_dropping_enemies", False)
        return DropOptions(groups, mark_enemy_drops)


class CharmOptions:

    _attr_names: typing.ClassVar[tuple[str, ...]] = (
        "charm_enemy_pool", "charm_reward_pool",
        "charm_rate", "mark_charmable_enemies"
    )
    _help_dict: typing.ClassVar[dict[str, str]] = {
        "charm_enemy_pool": "Pool of enemies which can have a charmable item",
        "charm_reward_pool": "Method of choosing enemy charmable items",
        "charm_rate": "Percentage (decimal) of enemies in the charm pool which have a charmable item",
        "mark_charmable_enemies": "Alter enemy names to indicate a charmable item"
    }
    name: typing.ClassVar[str] = "Enemy charm settings"
    description: typing.ClassVar[str] = "Settings which modify enemy charms"
    def __init__(
            self,
            charm_groups: Sequence[CharmGroup] | None = None,
            mark_charmable_enemies: bool = False
    ):
        if charm_groups is None:
            charm_groups = [
                CharmGroup.extract_from_namespace(argparse.Namespace(), 0)
            ]

        self.charm_groups = list(charm_groups)
        self.mark_charmable_enemies = mark_charmable_enemies

    @classmethod
    def get_argument_spec(cls) -> argumenttypes.ArgSpec:
        ret_dict: dict[str, argumenttypes.Argument] = {}

        for ind in range(4):
            group_dict = CharmGroup.get_argument_spec(ind)
            ret_dict.update(group_dict)

        attr_name = "mark_charmable_enemies"
        ret_dict[attr_name] = argumenttypes.FlagArg(cls._help_dict[attr_name])

        return ret_dict

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        """Adds this as a group to the parser."""
        group = parser.add_argument_group(
            title=cls.name, description=cls.description
        )

        arg_spec = cls.get_argument_spec()
        for attr_name, arg in arg_spec.items():
            arg_name = argumenttypes.attr_name_to_arg_name(attr_name)
            arg.add_to_argparse(arg_name, group)

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace):
        groups: list[CharmGroup] = []
        for ind in range(4):
            groups.append(CharmGroup.extract_from_namespace(namespace, ind))

        mark_enemy_drops = getattr(namespace, "mark_charmable_enemies", False)
        return CharmOptions(groups, mark_enemy_drops)


@dataclass
class XPTPGRewards:
    xp_scale: float = 1.0
    tp_scale: float = 1.0
    g_scale: float = 1.0
    split_xp: bool = False
    split_tp: bool = False
    fix_tp_doubling: bool = False
    xp_penalty_level: int = 99
    xp_penalty_percent: int = 0
    level_cap: int = 60
    boss_xp_factor: float = 1.0
    boss_tp_factor: float = 1.0
    midboss_reward_factor: float = 1.0
    normalize_boss_xp: bool = False

    _help_dict: typing.ClassVar[dict[str, str]] = {
        'xp_scale': "Factor by which to scale XP earned in battle",
        'tp_scale': "Factor by which to scale TP earned in battle",
        'g_scale': "Factor by which to scale G earned in battle",
        'split_xp': "XP is split among living party members rather than shared evenly",
        'split_tp': "TP is split among living party members rather than shared evenly",
        'fix_tp_doubling': "TP rewards are not duplicated for every gained tech level",
        "xp_penalty_level": "Levels past this level become more difficult to obtain",
        "xp_penalty_percent": "For each level beyond the penalty, the requirement grows by this percent",
        "level_cap": "Levels beyond the level cap will have prohibitively large requirements.",
        "boss_xp_factor": "Boss xp is additionally multiplied by this factor",
        "boss_tp_factor": "Boss tp is additionally multiplied by this factor",
        "midboss_reward_factor": "Midboss xp/tp is additionally multiplied by this factor",
        "normalize_boss_xp": "Boss xp is proportional to their level"
    }
    _arg_names: typing.ClassVar[tuple[str, ...]] = (
        'xp_scale', 'tp_scale', 'g_scale', 'split_xp', 'split_tp',
        'fix_tp_doubling', "xp_penalty_level", "xp_penalty_percent",
        "level_cap", "boss_xp_factor", "boss_tp_factor" "midboss_reward_factor",
        "normalize_boss_xp"
    )

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        """Adds this as a group to the parser."""
        group = parser.add_argument_group(
            title="Battle Rewards Settings",
            description="Settings which modify post-battle rewards."
        )

        argumenttypes.add_dataclass_to_group(
            cls, group, help_dict=cls._help_dict
        )

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace) -> typing.Self:
        return argumenttypes.extract_dataclass_from_namespace(cls, namespace)

    @classmethod
    def get_argument_spec(cls) -> argumenttypes.ArgSpec:

        ret_dict: dict[str, argumenttypes.Argument[typing.Any]] = {}

        for arg_name in ("xp_scale", "tp_scale"):
            ret_dict[arg_name] = argumenttypes.DiscreteNumericalArg(
                0.50, 10.00, 0.05, 4.0,
                cls._help_dict[arg_name], type_fn=float
            )

        for arg_name in ("split_tp", "fix_tp_doubling"):
            ret_dict[arg_name] = argumenttypes.FlagArg(cls._help_dict[arg_name])

        arg_name = "xp_penalty_level"
        ret_dict[arg_name] = argumenttypes.DiscreteNumericalArg(
            1, 99, 1, 40,
            cls._help_dict[arg_name], type_fn=int
        )

        arg_name = "xp_penalty_percent"
        ret_dict[arg_name] = argumenttypes.DiscreteNumericalArg(
            0, 100, 1, 15,
            cls._help_dict[arg_name], type_fn=int
        )

        arg_name = "level_cap"
        ret_dict[arg_name] = argumenttypes.DiscreteNumericalArg(
            1, 99, 1, 50,
            cls._help_dict[arg_name], type_fn=int
        )

        for arg_name in (
                "boss_xp_factor", "boss_xp_factor", "midboss_reward_factor"):
            ret_dict[arg_name] = argumenttypes.DiscreteNumericalArg(
                0.0, 5.0, 0.25, 2.0,
                cls._help_dict[arg_name], type_fn=float
            )

        arg_name = "normalize_boss_xp"
        ret_dict[arg_name] = argumenttypes.FlagArg(
            cls._help_dict[arg_name]
        )

        return ret_dict



class BattleRewards:
    def __init__(
            self,
            xp_tp_rewards: XPTPGRewards = XPTPGRewards(),
            drop_options: DropOptions = DropOptions(),
            charm_options: CharmOptions = CharmOptions(),
    ):
        self.xp_tp_rewards = xp_tp_rewards
        self.drop_options = drop_options
        self.charm_options = charm_options

    @classmethod
    def get_argument_spec(cls) -> dict[str, argumenttypes.Argument]:
        ret_dict: argumenttypes.ArgSpec = dict()
        ret_dict["xp_tp_rewards"] = XPTPGRewards.get_argument_spec()
        ret_dict["drop_options"] = DropOptions.get_argument_spec()
        ret_dict["charm_options"] = CharmOptions.get_argument_spec()

        return ret_dict

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        XPTPGRewards.add_group_to_parser(parser)
        DropOptions.add_group_to_parser(parser)
        CharmOptions.add_group_to_parser(parser)

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace) -> typing.Self:
        return cls(
            XPTPGRewards.extract_from_namespace(namespace),
            DropOptions.extract_from_namespace(namespace),
            CharmOptions.extract_from_namespace(namespace)
        )
