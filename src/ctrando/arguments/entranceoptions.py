"""Entrance Shuffler Options"""
import argparse
import functools
import typing

from ctrando.overworlds.owexitdata import OWExitClass as OWExit
from ctrando.arguments import argumenttypes as aty


class EntranceShufflerOptions:
    _default_shuffle_entrances: typing.ClassVar[bool] = False
    # _default_preserve_dungeons: typing.ClassVar[bool] = False
    # _default_preserve_shops: typing.ClassVar[bool] = False
    # Note: Entrance Rando does not have the default Tyrano Lair exit.
    #       Instead, the Lair Ruins by default goes to Tyrano Lair and
    #       LV portal by default goes to Lair Ruins.  So if you want to
    #       make Tyrano Lair a preserved spot, use "lair_ruins".
    _default_preserve_spots: typing.ClassVar[tuple[OWExit, ...]] = (
        # Recruits
        OWExit.MANORIA_CATHEDRAL, OWExit.GUARDIA_CASTLE_1000,
        OWExit.MILLENNIAL_FAIR, OWExit.GUARDIA_CASTLE_600, OWExit.CURSED_WOODS,
        OWExit.DACTYL_NEST, OWExit.PROTO_DOME, OWExit.NORTH_CAPE, OWExit.DEATH_PEAK,
        # Other Dungeons
        OWExit.HECKRAN_CAVE, OWExit.VORTEX_PT, OWExit.ZENAN_BRIDGE_600_NORTH,
        OWExit.DENADORO_MTS, OWExit.MAGUS_LAIR, OWExit.ARRIS_DOME,
        OWExit.FACTORY_RUINS, OWExit.NORTHERN_RUINS_600, OWExit.NORTHERN_RUINS_1000,
        OWExit.GIANTS_CLAW, OWExit.OZZIES_FORT, OWExit.SUNKEN_DESERT,
        OWExit.SUN_PALACE, OWExit.GENO_DOME, OWExit.REPTITE_LAIR,
        OWExit.LAIR_RUINS,  # OWExit.TYRANO_LAIR,
        OWExit.TERRA_CAVE, OWExit.LAST_VILLAGE_COMMONS,
        OWExit.ZEAL_PALACE, OWExit.BLACKBIRD, OWExit.WEST_CAPE,
        # Important exits that are annoying to bury
        OWExit.CHORAS_CARPENTER_600, OWExit.LUCCAS_HOUSE,
        OWExit.SUN_KEEP_PREHISTORY, OWExit.SUN_KEEP_2300,
        OWExit.PORRE_MAYOR_1000, OWExit.PORRE_ELDER_600,
        OWExit.FIONAS_VILLA, OWExit.FIONAS_SHRINE,
        OWExit.SNAIL_STOP, OWExit.KEEPERS_DOME, OWExit.TATAS_HOUSE,
    )
    _default_vanilla_spots: typing.ClassVar[tuple[OWExit, ...]] = ()
    _num_preserve_spots_groups: typing.ClassVar[int] = 5

    @classmethod
    def get_argument_spec(cls) -> aty.ArgSpec:
        spec: aty.ArgSpec =  {
            "shuffle_entrances": aty.FlagArg("Whether to shuffle entrances or not"),
            "preserve_spots": aty.arg_multiple_from_enum(
                OWExit, cls._default_preserve_spots,
                "Spots which are to be shuffled among themselves"
            ),
            "rest_vanilla": aty.FlagArg("Only shuffle locations in preserve_spots"),
            "vanilla_spots": aty.arg_multiple_from_enum(
                OWExit, cls._default_vanilla_spots,
                "Spots guaranteed to not be shuffled. Takes precedence over preserve_spots"
            ),
            "shuffle_gates": aty.FlagArg("Shuffle where (non-algetty) portals lead to"),
            "separate_gate_eras": aty.FlagArg("Shuffled gates must go to different eras"),
            "lair_ruins_default_spot": aty.arg_from_enum(
                OWExit, OWExit.LAST_VILLAGE_RESIDENCE,
                "Default (vanilla) overworld exit to lair ruins portal"
            )
        }

        for ind in range(1, cls._num_preserve_spots_groups):
            arg_name = f"preserve_spots_{ind}"
            spec[arg_name] = aty.arg_multiple_from_enum(
                OWExit, tuple(),
                f"Spots which are to be shuffled among themselves (Group {ind})"
            )

        return spec

    def __init__(
            self,
            shuffle_entrances: bool = _default_shuffle_entrances,
            preserve_spots: tuple[OWExit, ...] = _default_preserve_spots,
            vanilla_spots: tuple[OWExit, ...] = _default_vanilla_spots,
            rest_vanilla: bool = False,
            shuffle_gates: bool = False,
            separate_gate_eras: bool = False,
            lair_ruins_default_spot: OWExit = OWExit.LAST_VILLAGE_RESIDENCE,
            **kwargs
    ):
        self.shuffle_entrances = shuffle_entrances
        preserve_groups: list[set[OWExit]] = [
            set(preserve_spots)
        ]

        for ind in range(1, self._num_preserve_spots_groups):
            arg_name = f"preserve_spots_{ind}"
            pool = kwargs.get(arg_name, set())
            if pool:
                preserve_groups.append(set(pool))

        vanilla_spot_temp: set[OWExit] = {spot for spot in vanilla_spots}
        vanilla_spot_temp.update(
            [OWExit.MAGIC_CAVE_OPEN, OWExit.MAGIC_CAVE_CLOSED]
        )

        ungrouped = {x for x in OWExit if x != OWExit.TYRANO_LAIR}
        grouped: set[OWExit] = set()
        for ind, group in enumerate(preserve_groups):
            # Remove all previously seen/vanilla elements from the current group to prevent overlap
            group.difference_update(grouped.union(vanilla_spot_temp))
            grouped.update(group)
            ungrouped.difference_update(group)

        if rest_vanilla:
            vanilla_spot_temp.update(ungrouped)
        else:
            preserve_groups.append(ungrouped.difference(vanilla_spot_temp))

        self.vanilla_spots = tuple(x for x in OWExit if x in vanilla_spot_temp)
        self.preserve_groups = [
            tuple(x for x in OWExit if x in group) for group in preserve_groups
        ]

        for group in self.preserve_groups + [self.vanilla_spots]:
            if OWExit.TYRANO_LAIR in group:
                raise ValueError("Use \"lair_ruins\" in place of \"tyrano_lair\"")

        self.shuffle_gates = shuffle_gates
        self.separate_gate_eras = separate_gate_eras

        bad_lair_ruins_spots = (
            OWExit.MAGIC_CAVE_OPEN, OWExit.MAGIC_CAVE_CLOSED,
            OWExit.SUNKEN_DESERT, OWExit.GIANTS_CLAW,
            OWExit.TYRANO_LAIR
        )
        if lair_ruins_default_spot in bad_lair_ruins_spots:
            raise ValueError("Invalid Lair Ruins spot.")
        self.lair_ruins_default_spot = lair_ruins_default_spot

    @classmethod
    def add_group_to_parser(cls, parser: argparse.ArgumentParser):
        group = parser.add_argument_group(
            "Entrance Shuffler Options",
            "Options for how overworld entrances are shuffled."
        )

        for attr_name, arg in cls.get_argument_spec().items():
            arg.add_to_argparse(aty.attr_name_to_arg_name(attr_name), group)

    @classmethod
    def extract_from_namespace(cls, namespace: argparse.Namespace) -> typing.Self:
        attr_names = cls.get_argument_spec().keys()
        return aty.extract_from_namespace(cls, arg_names=attr_names, namespace=namespace)
