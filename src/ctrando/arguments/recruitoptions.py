"""Options for how recruits are obtained"""

import argparse
import dataclasses
import typing

from ctrando.arguments import argumenttypes
from ctrando.common import ctenums


@dataclasses.dataclass
class RecruitData:
    min_level: int | None
    min_tech_level: int | None

    def __post_init__(self):
        if self.min_level is None:
            self.min_level = 1
        if self.min_tech_level is None:
            self.min_tech_level = 0

        self.min_level = sorted([1, self.min_level, 99])[1]
        self.min_tech_level = sorted([0, self.min_tech_level, 8])[1]


class RecruitOptions:
    _default_starter_data = RecruitData(1, 0)
    _default_fair_data = RecruitData(1, 0)
    _default_cathedral_data = RecruitData(5, 0)
    _default_castle_data = RecruitData(5, 1)
    _default_trial_data = RecruitData(7, 1)
    _default_proto_data = RecruitData(10, 2)
    _default_north_cape_data = RecruitData(37, 3)
    _default_burrow_data = RecruitData(18, 2)
    _default_dactyl_data = RecruitData(20, 2)
    _default_death_peak_data = RecruitData(37, 8)
    _default_yakra_box_data = RecruitData(25, 3)
    _default_scale_level_to_leader: bool = False
    _default_scale_techlevel_to_leader: bool = False
    _default_scale_gear: bool = False
    _name_default_dict = {
        "starter": _default_starter_data,
        "fair": _default_fair_data,
        "cathedral": _default_cathedral_data,
        "castle": _default_castle_data,
        "trial": _default_trial_data,
        "proto": _default_proto_data,
        "north_cape": _default_north_cape_data,
        "burrow": _default_burrow_data,
        "dactyl": _default_dactyl_data,
        "death_peak": _default_death_peak_data,
        "yakra_box": _default_yakra_box_data
    }
    _spot_attr_name_dict = {
        ctenums.RecruitID.STARTER: "starter",
        ctenums.RecruitID.MILLENNIAL_FAIR: "fair",
        ctenums.RecruitID.CATHEDRAL: "cathedral",
        ctenums.RecruitID.CASTLE: "castle",
        ctenums.RecruitID.CRONO_TRIAL: "trial",
        ctenums.RecruitID.PROTO_DOME: "proto",
        ctenums.RecruitID.NORTH_CAPE: "north_cape",
        ctenums.RecruitID.FROGS_BURROW: "burrow",
        ctenums.RecruitID.DACTYL_NEST: "dactyl",
        ctenums.RecruitID.DEATH_PEAK: "death_peak",
        ctenums.RecruitID.YAKRA_BOX: "yakra_box"
    }
    def __init__(
            self,
            starter_data: RecruitData = _default_starter_data,
            fair_data: RecruitData = _default_fair_data,
            cathedral_data: RecruitData = _default_cathedral_data,
            castle_data: RecruitData = _default_castle_data,
            trial_data: RecruitData = _default_trial_data,
            proto_data: RecruitData = _default_proto_data,
            north_cape_data: RecruitData = _default_north_cape_data,
            burrow_data: RecruitData = _default_burrow_data,
            dactyl_data: RecruitData = _default_dactyl_data,
            death_peak_data: RecruitData = _default_death_peak_data,
            yakra_box_data: RecruitData = _default_yakra_box_data,
            scale_level_to_leader: bool = _default_scale_level_to_leader,
            scale_techlevel_to_leader: bool = _default_scale_techlevel_to_leader,
            scale_gear: bool = _default_scale_gear
    ):
        self.starter_data = starter_data
        self.fair_data = fair_data
        self.cathedral_data = cathedral_data
        self.castle_data = castle_data
        self.trial_data = trial_data
        self.proto_data = proto_data
        self.north_cape_data = north_cape_data
        self.burrow_data = burrow_data
        self.dactyl_data = dactyl_data
        self.death_peak_data = death_peak_data
        self.yakra_box_data = yakra_box_data
        self.scale_level_to_leader = scale_level_to_leader
        self.scale_techlevel_to_leader = scale_techlevel_to_leader
        self.scale_gear = scale_gear

    def get_spot_data(self, recruit_id: ctenums.RecruitID) -> RecruitData:
        attr_suffix = self._spot_attr_name_dict[recruit_id]
        attr_name = f"{attr_suffix}_data"
        return getattr(self, attr_name)

    @classmethod
    def get_argument_spec(cls) -> argumenttypes.ArgSpec:
        ret_dict: argumenttypes.ArgSpec = {}

        for name, data in cls._name_default_dict.items():
            ret_dict[f"{name}_min_level"] = argumenttypes.DiscreteNumericalArg(
                1, 99, 1, data.min_level,
                f"Minimum level at which the {name} recruit can join (default: {data.min_level})",
                type_fn=int
            )
            ret_dict[f"{name}_min_techlevel"] = argumenttypes.DiscreteNumericalArg(
                0, 8, 1, data.min_tech_level,
                f"Minimum techlevel at which the {name} recruit can join (default: {data.min_tech_level})",
                type_fn=int
            )

        ret_dict["minimum_recruits"] = argumenttypes.FlagArg(
            "All recruits are given a min level of 1 and min tech level of 0, overrides other settings"
        )
        ret_dict["scale_level_to_leader"] = argumenttypes.FlagArg(
            "Recruits are scaled to the level of the lead character (but not below the spot minimum)"
        )
        ret_dict["scale_techlevel_to_leader"] = argumenttypes.FlagArg(
            "Recruits are scaled to the tech level of the lead character (but not below the spot minimum)"
        )
        ret_dict["scale_gear"] = argumenttypes.FlagArg(
            "Recruit gear is scaled based on the level at which they are recruited"
        )

        return ret_dict

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        """Add recruit option group to parser"""
        group = parser.add_argument_group(
            "Recruit Options",
            "Options related to the power of new recruits"
        )

        for name, defaults in cls._name_default_dict.items():
            default_val = defaults.min_level
            name = name.replace("_", "-")
            group.add_argument(
                f"--{name}-min-level",
                action="store", type=int,
                default=argparse.SUPPRESS,
                help=f"Minimum level at which the {name} recruit can join (default: {default_val})"
            )

            default_val = defaults.min_tech_level
            group.add_argument(
                f"--{name}-min-techlevel",
                action="store", type=int,
                default=argparse.SUPPRESS,
                help=f"Minimum tech level at which the {name} recruit can join (default: {default_val})"
            )

        group.add_argument(
            "--minimum-recruits", action="store_true",
            default=argparse.SUPPRESS,
            help="All recruits are given a min level of 1 and min tech level of 0.  Overrides other min settings."
        )

        group.add_argument(
            "--scale-level-to-leader", action="store_true",
            default=argparse.SUPPRESS,
            help="Recruits are scaled to the level level of the lead character (but not below the spot minimum)"
        )
        group.add_argument(
            "--scale-techlevel-to-leader", action="store_true",
            default=argparse.SUPPRESS,
            help="Recruits are scaled to the tech level of the lead character (but not below the spot minimum)"
        )
        group.add_argument(
            "--scale-gear", action="store_true",
            default=argparse.SUPPRESS,
            help="Recruit gear is scaled based on the level at which they are recruited."
        )

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace):
        kwarg_dict: dict[str, typing.Any] = dict()

        for name, defaults in cls._name_default_dict.items():
            min_level = defaults.min_level
            min_tech_level = defaults.min_tech_level

            if hasattr(namespace, "minimum_recruits"):
                min_level = 1
                min_tech_level = 0
            else:
                if hasattr(namespace, f"{name}_min_level"):
                    min_level = getattr(namespace, f"{name}_min_level")

                if hasattr(namespace, f"{name}_min_techlevel"):
                    min_tech_level = getattr(namespace, f"{name}_min_techlevel")

            kwarg_dict[f"{name}_data"] = RecruitData(min_level, min_tech_level)

        # scale_level_to_leader = cls._default_scale_level_to_leader
        if hasattr(namespace, "scale_level_to_leader"):
            kwarg_dict["scale_level_to_leader"] = getattr(namespace, "scale_level_to_leader")

        if hasattr(namespace, "scale_techlevel_to_leader"):
            kwarg_dict["scale_techlevel_to_leader"] = getattr(namespace, "scale_techlevel_to_leader")

        if hasattr(namespace, "scale_gear"):
            kwarg_dict["scale_gear"] = getattr(namespace, "scale_gear")

        return cls(**kwarg_dict)
