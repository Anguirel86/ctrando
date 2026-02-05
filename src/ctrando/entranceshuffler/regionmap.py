import typing
from itertools import combinations, permutations

from ctrando.arguments import logicoptions
from ctrando.common import ctenums, memory
from ctrando.common.ctenums import CharID, ItemID, RecruitID
from ctrando.entranceshuffler import locregions, owregions
from ctrando.entranceshuffler.locregions import LocRegion
from ctrando.entranceshuffler.owregions import OWRegion
from ctrando.overworlds.owexitdata import OWExitClass as OWExit
from ctrando.locations.locexitdata import LocOWExits as LocExit
from ctrando.logic import logictypes, logicfactory
from ctrando.recruits import recruitassign


from collections.abc import Iterable


# The idea is that ExitConnectors will be shuffled, but there are other
# types of connections between regions which will not be.
class ExitConnector:
    """ExitConnectors are explicit about which OW exit goes where."""
    def __init__(
            self,
            from_exit: OWExit,
            to_exit: LocExit,
            rule: logictypes.LogicRule | None = None,
            reversible: bool = True
    ):
        self.from_exit = from_exit
        self.to_exit = to_exit
        if rule is None:
            self.rule = logictypes.LogicRule()
        else:
            self.rule = logictypes.LogicRule(rule.get_access_rule())
        self.reversible = reversible


class RegionConnector:
    """RegionConnectors just use region names to specify a connection"""
    def __init__(
            self,
            from_region_name: str,
            to_region_name: str,
            link_name: str,
            rule: logictypes.LogicRule | None = None,
            reversible: bool = True
    ):
        self.from_region_name = from_region_name
        self.to_region_name = to_region_name
        self.link_name = link_name
        if rule is None:
            self.rule = logictypes.LogicRule()
        else:
            self.rule = logictypes.LogicRule(rule.get_access_rule())
        self.reversible = reversible


class MapConnector:
    def __init__(
            self,
            from_name: str,
            to_name,
            rule: logictypes.LogicRule,
            link_name: str | None = None
    ):
        self.from_name = from_name
        self.to_name = to_name
        self.rule = logictypes.LogicRule(rule.get_access_rule())
        self.link_name = link_name


class RegionMap:
    """Graph of all regions"""
    def __init__(
            self,
            ow_regions: Iterable[owregions.OWRegion],
            loc_regions: Iterable[locregions.LocRegion],
            exit_connectors: Iterable[ExitConnector],
            region_connectors: Iterable[RegionConnector],
    ):
        self.ow_region_dict: dict[str, OWRegion] = dict()
        self.ow_exit_dict: dict[OWExit, str] = dict()

        for region in ow_regions:
            if region.name in self.ow_region_dict:
                raise ValueError("Duplicate OW Region Name.")
            self.ow_region_dict[region.name] = region
            for ow_exit in region.ow_exits:
                self.ow_exit_dict[ow_exit] = region.name

        self.loc_region_dict: dict[str, LocRegion] = dict()
        for region in loc_regions:
            if region.name in self.loc_region_dict or region.name in self.ow_region_dict:
                raise ValueError("Duplicate Loc Region Name: " + region.name)
            self.loc_region_dict[region.name] = region

        self.name_connector_dict: dict[str, list[RegionConnector]] = dict()

        for x in list(self.ow_region_dict.keys())+list(self.loc_region_dict.keys()):
            self.name_connector_dict[x] = []

        for exit_connector in exit_connectors:
            ow_exit = exit_connector.from_exit
            loc_exit = exit_connector.to_exit
            ow_name: str | None = None
            loc_name: str | None = None

            for name, ow_region in self.ow_region_dict.items():
                if ow_exit in ow_region.ow_exits:
                    ow_name = name

            for name, loc_region in self.loc_region_dict.items():
                if loc_exit in loc_region.loc_exits:
                    loc_name = name

            if ow_name is not None and loc_name is not None:
                self.name_connector_dict[ow_name].append(
                    RegionConnector(ow_name, loc_name,
                                    f"{str(exit_connector.from_exit)}(loc)",
                                    exit_connector.rule)
                )
                if exit_connector.reversible:
                    self.name_connector_dict[loc_name].append(
                        RegionConnector(
                            loc_name, ow_name,
                            str(exit_connector.from_exit),
                            exit_connector.rule
                        )
                    )
            else:
                pass
                # print(f"Warning: {exit_connector.from_exit}, [{ow_name}, {ow_exit}] [{loc_name}, {loc_exit}]")

        for region_connector in region_connectors:
            self.name_connector_dict[region_connector.from_region_name].append(
                RegionConnector(region_connector.from_region_name,
                                region_connector.to_region_name,
                                region_connector.link_name,
                                region_connector.rule)
            )
            if region_connector.reversible:
                self.name_connector_dict[region_connector.to_region_name].append(
                    RegionConnector(region_connector.to_region_name,
                                    region_connector.from_region_name,
                                    region_connector.link_name,
                                    region_connector.rule)
                )

        self.region_connectors = region_connectors

    def get_treasure_group_dict(self) -> dict[str, list[ctenums.TreasureID]]:
        ret_dict: dict[str, list[ctenums.TreasureID]] = dict()
        for name, region in self.loc_region_dict.items():
            if region.reward_spots:
                ret_dict[name] = list(region.reward_spots)

        return ret_dict

    def add_loc_region(self, region: LocRegion):
        region_name = region.name
        if region_name in self.loc_region_dict:
            raise ValueError

        self.loc_region_dict[region_name] = region
        if region_name not in self.name_connector_dict:
            self.name_connector_dict[region_name] = []


    def add_region_connector(self, connector: RegionConnector):
        if connector.from_region_name not in self.name_connector_dict:
            raise ValueError

        self.name_connector_dict[connector.from_region_name].append(
            RegionConnector(connector.from_region_name, connector.to_region_name,
                            connector.link_name, connector.rule, False)
        )

        if connector.reversible:
            if connector.to_region_name not in self.name_connector_dict:
                raise ValueError

            self.name_connector_dict[connector.to_region_name].append(
                RegionConnector(connector.to_region_name, connector.from_region_name,
                                connector.link_name, connector.rule, False)
            )


_charge_rule = logicfactory.ProgressiveRule([ctenums.ItemID.PENDANT, ctenums.ItemID.PENDANT_CHARGE])
_masa_rule = logicfactory.ProgressiveRule([ctenums.ItemID.MASAMUNE_1, ctenums.ItemID.MASAMUNE_2])

def get_default_exit_connectors() -> list[ExitConnector]:
    return [
        # truce_1000_overworld
        ExitConnector(OWExit.VORTEX_PT, LocExit.HECKRAN_CAVE_WHIRLPOOL),
        ExitConnector(OWExit.CRONOS_HOUSE, LocExit.CRONOS_HOUSE),
        ExitConnector(OWExit.TRUCE_SINGLE_RESIDENCE, LocExit.TRUCE_SINGLE_RESIDENCE),
        ExitConnector(OWExit.TRUCE_INN_1000, LocExit.TRUCE_INN_1000),
        ExitConnector(OWExit.TRUCE_TICKET_OFFICE, LocExit.TRUCE_TICKET_OFFICE),
        ExitConnector(OWExit.TRUCE_SCREAMING_RESIDENCE, LocExit.TRUCE_SCREAMING_RESIDENCE),
        ExitConnector(OWExit.MILLENNIAL_FAIR, LocExit.MILLENNIAL_FAIR),
        ExitConnector(OWExit.TRUCE_MARKET_1000, LocExit.TRUCE_MARKET_1000),
        ExitConnector(OWExit.TRUCE_MAYOR, LocExit.TRUCE_MAYOR),
        ExitConnector(OWExit.LUCCAS_HOUSE, LocExit.LUCCAS_HOUSE),
        ExitConnector(OWExit.GUARDIA_FOREST_SOUTH_1000, LocExit.GUARDIA_FOREST_SOUTH_1000),
        ExitConnector(OWExit.ZENAN_BRIDGE_1000_NORTH, LocExit.ZENAN_BRIDGE_1000_NORTH),
        # guardia_castle_1000_overworld
        ExitConnector(OWExit.GUARDIA_CASTLE_1000, LocExit.GUARDIA_CASTLE_1000),
        ExitConnector(OWExit.GUARDIA_FOREST_NORTH_1000, LocExit.GUARDIA_FOREST_NORTH_1000),
        # porre_1000_ow
        ExitConnector(OWExit.ZENAN_BRIDGE_1000_SOUTH, LocExit.ZENAN_BRIDGE_1000_SOUTH),
        ExitConnector(OWExit.PORRE_INN_1000, LocExit.PORRE_INN_1000),
        ExitConnector(OWExit.PORRE_MARKET_1000, LocExit.PORRE_MARKET_1000),
        ExitConnector(OWExit.SNAIL_STOP, LocExit.SNAIL_STOP),
        ExitConnector(OWExit.PORRE_MAYOR_1000, LocExit.PORRE_MAYOR_1000),
        ExitConnector(OWExit.PORRE_TICKET_OFFICE, LocExit.PORRE_TICKET_OFFICE),
        ExitConnector(OWExit.PORRE_RESIDENCE_1000, LocExit.PORRE_RESIDENCE_1000),
        # fiona_shrine_1000_ow
        ExitConnector(OWExit.FIONAS_SHRINE, LocExit.FIONAS_SHRINE,
                      logictypes.LogicRule([memory.Flags.ROBO_HELPS_FIONA])),
        # medina_1000_ow
        ExitConnector(OWExit.MEDINA_ELDER_HOUSE, LocExit.MEDINA_ELDER),
        ExitConnector(OWExit.MEDINA_INN, LocExit.MEDINA_INN),
        ExitConnector(OWExit.MEDINA_PORTAL, LocExit.MEDINA_PORTAL),
        ExitConnector(OWExit.MELCHIORS_HUT, LocExit.MELCHIORS_HUT),
        ExitConnector(OWExit.MEDINA_MARKET, LocExit.MEDINA_MARKET),
        ExitConnector(OWExit.MEDINA_SQUARE, LocExit.MEDINA_SQUARE),
        ExitConnector(OWExit.FOREST_RUINS, LocExit.FOREST_RUINS),
        ExitConnector(OWExit.HECKRAN_CAVE, LocExit.HECKRAN_CAVE),
        # choras_1000_ow
        ExitConnector(OWExit.CHORAS_MAYOR_1000, LocExit.CHORAS_MAYOR_1000),
        ExitConnector(OWExit.CHORAS_INN_1000, LocExit.CHORAS_INN_1000),
        ExitConnector(OWExit.CHORAS_CARPENTER_1000, LocExit.CHORAS_CARPTENTER_1000),
        ExitConnector(OWExit.NORTHERN_RUINS_1000, LocExit.NORTHERN_RUINS_1000),
        ExitConnector(OWExit.WEST_CAPE, LocExit.WEST_CAPE),
        # truce_600_ow
        ExitConnector(
            OWExit.ZENAN_BRIDGE_600_NORTH, LocExit.ZENAN_BRIDGE_600_NORTH,
            rule=logictypes.LogicRule([ItemID.JERKY, ItemID.JERKY])
        ),
        ExitConnector(OWExit.TRUCE_CANYON, LocExit.TRUCE_CANYON),
        ExitConnector(OWExit.TRUCE_COUPLE_RESIDENCE_600, LocExit.TRUCE_COUPLE_RESIDENCE_600),
        ExitConnector(OWExit.TRUCE_SMITH_RESIDENCE, LocExit.TRUCE_SMITH_RESIDENCE),
        ExitConnector(OWExit.TRUCE_INN_600, LocExit.TRUCE_INN_600),
        ExitConnector(OWExit.TRUCE_MARKET_600, LocExit.TRUCE_MARKET_600),
        ExitConnector(OWExit.GUARDIA_FOREST_SOUTH_600, LocExit.GUARDIA_FOREST_SOUTH_600),
        ExitConnector(OWExit.MANORIA_CATHEDRAL, LocExit.MANORIA_CATHEDRAL),
        # guardia_castle_600_ow
        ExitConnector(OWExit.GUARDIA_CASTLE_600, LocExit.GUARDIA_CASTLE_600),
        ExitConnector(OWExit.GUARDIA_FOREST_NORTH_600, LocExit.GUARDIA_FOREST_NORTH_600),
        # porre_600_ow
        # Zenan 600 south is going just go to the same place as the north exit.
        # ExitConnector(OWExit.ZENAN_BRIDGE_600_SOUTH, LocExit.ZENAN_BRIDGE_600_SOUTH)
        # ExitConnector(OWExit.ZENAN_BRIDGE_600_SOUTH, LocExit.ZENAN_BRIDGE_600_SOUTH_BOSS)
        ExitConnector(OWExit.MAGIC_CAVE_OPEN, LocExit.MAGIC_CAVE_OPEN),
        ExitConnector(OWExit.MAGIC_CAVE_CLOSED, LocExit.MAGIC_CAVE_CLOSED),
        ExitConnector(OWExit.DORINO_BROMIDE_RESIDENCE, LocExit.DORINO_BROMIDE_RESIDENCE),
        ExitConnector(OWExit.DORINO_INN, LocExit.DORINO_INN),
        ExitConnector(OWExit.DORINO_MARKET, LocExit.DORINO_MARKET),
        ExitConnector(OWExit.TATAS_HOUSE, LocExit.TATAS_HOUSE),
        ExitConnector(OWExit.PORRE_ELDER_600, LocExit.PORRE_ELDER_600),
        ExitConnector(OWExit.PORRE_CAFE_600, LocExit.PORRE_CAFE_600),
        ExitConnector(OWExit.PORRE_INN_600, LocExit.PORRE_INN_600),
        ExitConnector(OWExit.PORRE_MARKET_600, LocExit.PORRE_MARKET_600),
        ExitConnector(OWExit.CURSED_WOODS, LocExit.CURSED_WOODS),
        ExitConnector(OWExit.DENADORO_MTS, LocExit.DENADORO_MTS),
        ExitConnector(OWExit.FIONAS_VILLA, LocExit.FIONAS_VILLA),
        # sunken_desert_600_overworld
        ExitConnector(
            OWExit.SUNKEN_DESERT, LocExit.SUNKEN_DESERT_ENTRANCE,
            logictypes.LogicRule([memory.Flags.PLANT_LADY_SAVES_SEED])
        ),
        # ExitConnector(OWExit.SUNKEN_DESERT, LocExit.SUNKEN_DESERT_INTERIOR),
        # choras_600_overworld
        ExitConnector(OWExit.CHORAS_OLD_RESIDENCE_600, LocExit.CHORAS_OLD_RESIDENCE_600),
        ExitConnector(OWExit.CHORAS_INN_600, LocExit.CHORAS_INN_600),
        ExitConnector(OWExit.CHORAS_CAFE_600, LocExit.CHORAS_CAFE_600),
        ExitConnector(OWExit.CHORAS_CARPENTER_600, LocExit.CHORAS_CARPTENTER_600),
        ExitConnector(OWExit.CHORAS_MARKET_600, LocExit.CHORAS_MARKET_600),
        ExitConnector(OWExit.NORTHERN_RUINS_600, LocExit.NORTHERN_RUINS_600),
        # magus_lair_overworld
        ExitConnector(OWExit.MAGUS_LAIR, LocExit.MAGUS_LAIR),
        ExitConnector(OWExit.MAGIC_CAVE_MAGUS, LocExit.MAGIC_CAVE_MAGUS),
        # Various
        ExitConnector(OWExit.SUN_KEEP_1000, LocExit.SUN_KEEP_1000),
        ExitConnector(OWExit.OZZIES_FORT, LocExit.OZZIES_FORT),
        ExitConnector(OWExit.SUN_KEEP_600, LocExit.SUN_KEEP_600),
        ExitConnector(OWExit.GIANTS_CLAW, LocExit.GIANTS_CLAW,
                      logictypes.LogicRule([memory.Flags.OW_GIANTS_CLAW_OPEN])),
        # trann_bangor_overworld
        ExitConnector(OWExit.TRANN_DOME, LocExit.TRANN_DOME),
        ExitConnector(OWExit.BANGOR_DOME, LocExit.BANGOR_DOME),
        ExitConnector(OWExit.LAB_16_WEST, LocExit.LAB_16_WEST),
        # arris_overworld
        ExitConnector(OWExit.ARRIS_DOME, LocExit.ARRIS_DOME),
        ExitConnector(OWExit.LAB_16_EAST, LocExit.LAB_16_EAST),
        ExitConnector(OWExit.SEWER_ACCESS_ARRIS, LocExit.SEWER_ACCESS_ARRIS),
        ExitConnector(OWExit.LAB_32_WEST, LocExit.LAB_32_WEST),
        # proto_overworld
        ExitConnector(OWExit.PROTO_DOME, LocExit.PROTO_DOME),
        ExitConnector(OWExit.FACTORY_RUINS, LocExit.FACTORY_RUINS),
        ExitConnector(OWExit.LAB_32_EAST, LocExit.LAB_32_EAST),
        # keepers_overworld
        ExitConnector(OWExit.KEEPERS_DOME, LocExit.KEEPERS_DOME),
        ExitConnector(OWExit.SEWER_ACCESS_KEEPERS, LocExit.SEWER_ACCESS_KEEPERS),
        ExitConnector(OWExit.DEATH_PEAK, LocExit.DEATH_PEAK),  # Also Fall
        # Various
        ExitConnector(OWExit.SUN_KEEP_2300, LocExit.SUN_KEEP_2300),
        ExitConnector(OWExit.GENO_DOME, LocExit.GENO_DOME),
        ExitConnector(OWExit.SUN_PALACE, LocExit.SUN_PALACE),
        # ioka_overworld
        ExitConnector(OWExit.MYSTIC_MTS, LocExit.MYSTIC_MTS),
        ExitConnector(OWExit.FOREST_MAZE_NORTH, LocExit.FOREST_MAZE_NORTH),
        ExitConnector(OWExit.DACTYL_NEST, LocExit.DACTYL_NEST),
        ExitConnector(OWExit.IOKA_MEETING_SOUTH, LocExit.IOKA_MEETING_SOUTH),
        ExitConnector(OWExit.IOKA_MEETING_NORTH, LocExit.IOKA_MEETING_NORTH),
        ExitConnector(OWExit.CHIEFS_HUT, LocExit.CHIEFS_HUT),
        ExitConnector(OWExit.TRADING_POST, LocExit.TRADING_POST),
        ExitConnector(OWExit.LARUBA_RUINS, LocExit.LARUBA_RUINS),
        ExitConnector(OWExit.IOKA_SW_HUT, LocExit.IOKA_SW_HUT),
        ExitConnector(OWExit.IOKA_SWEET_WATER_HUT, LocExit.IOKA_SWEET_WATER_HUT),
        ExitConnector(OWExit.HUNTING_RANGE, LocExit.HUNTING_RANGE),
        # reptite_lair_overworld
        ExitConnector(OWExit.REPTITE_LAIR, LocExit.REPTITE_LAIR),
        ExitConnector(OWExit.FOREST_MAZE_SOUTH, LocExit.FOREST_MAZE_SOUTH),
        # Various
        ExitConnector(OWExit.SUN_KEEP_PREHISTORY, LocExit.SUN_KEEP_PREHISTORY),
        ExitConnector(OWExit.TYRANO_LAIR, LocExit.TYRANO_LAIR),
        ExitConnector(OWExit.LAIR_RUINS, LocExit.LAIR_RUINS,
                      rule=logictypes.LogicRule([memory.Flags.OW_LAVOS_HAS_FALLEN])
                      ),
        # dark_ages_portal_overworld
        ExitConnector(OWExit.DARK_AGES_PORTAL, LocExit.DARK_AGES_PORTAL_DEFAULT),
        ExitConnector(OWExit.TERRA_CAVE, LocExit.TERRA_CAVE),
        ExitConnector(OWExit.SKYWAY_ENHASA_SOUTH, LocExit.SKYWAY_ENHASA_SOUTH),
        # dark_ages_skyway_island_overworld
        ExitConnector(OWExit.SKYWAY_ENHASA_NORTH, LocExit.SKYWAY_ENHASA_NORTH),
        ExitConnector(OWExit.SKYWAY_KAJAR, LocExit.SKYWAY_KAJAR),
        # enhasa_overworld
        ExitConnector(OWExit.ENHASA, LocExit.ENHASA),
        ExitConnector(OWExit.LAND_BRIDGE_ENHASA_NORTH, LocExit.LAND_BRIDGE_ENHASA_NORTH),
        ExitConnector(OWExit.LAND_BRIDGE_ENHASA_SOUTH, LocExit.LAND_BRIDGE_ENHASA_SOUTH),
        # kajar_overworld
        ExitConnector(OWExit.KAJAR, LocExit.KAJAR),
        ExitConnector(OWExit.LAND_BRIDGE_KAJAR, LocExit.LAND_BRIDGE_KAJAR),
        ExitConnector(OWExit.BLACKBIRD, LocExit.BLACKBIRD),
        ExitConnector(OWExit.ZEAL_TELEPORTER_BOTTOM, LocExit.ZEAL_TELEPORTER_BOTTOM),
        # zeal_palace_overworld
        ExitConnector(OWExit.ZEAL_PALACE, LocExit.ZEAL_PALACE),
        ExitConnector(OWExit.ZEAL_TELEPORTER_TOP, LocExit.ZEAL_TELEPORTER_TOP),
        # last_village_overworld
        ExitConnector(OWExit.LAST_VILLAGE_SHOP, LocExit.LAST_VILLAGE_SHOP),
        ExitConnector(OWExit.LAST_VILLAGE_COMMONS, LocExit.LAST_VILLAGE_COMMNONS),
        ExitConnector(OWExit.NORTH_CAPE, LocExit.NORTH_CAPE),
        ExitConnector(OWExit.LAST_VILLAGE_RESIDENCE, LocExit.LAST_VILLAGE_RESIDENCE),
        ExitConnector(OWExit.LAST_VILLAGE_EMPTY_HUT, LocExit.LAST_VILLAGE_EMPTY_HUT),
        # last_village_portal_overworld
        ExitConnector(OWExit.LAST_VILLAGE_PORTAL, LocExit.DARK_AGES_PORTAL_LAST_VILLAGE),
        # last_village_sun_keep_overworl
        ExitConnector(OWExit.SUN_KEEP_LAST_VILLAGE, LocExit.SUN_KEEP_LAST_VILLAGE)
    ]


def get_default_region_connectors(
        recruit_assign_dict: typing.Optional[dict[ctenums.RecruitID, list[ctenums.CharID]]],
        logic_options: logicoptions.LogicOptions
) -> list[RegionConnector]:

    if recruit_assign_dict is None:
        recruit_assign_dict = {rid: [] for rid in ctenums.RecruitID}
        recruit_assign_dict[RecruitID.STARTER] = [ctenums.CharID.CRONO]

    charge_rule = _charge_rule
    masa_rule = _masa_rule

    fair_recruit_rule = logictypes.LogicRule()
    if recruit_assign_dict[ctenums.RecruitID.MILLENNIAL_FAIR]:
        char_id = recruit_assign_dict[ctenums.RecruitID.MILLENNIAL_FAIR][0]
        recruit_item = logicfactory.get_fair_recruit_item(char_id)
        if recruit_item == ctenums.ItemID.PENDANT_CHARGE:
            fair_recruit_rule = charge_rule(2)
        elif recruit_item == ctenums.ItemID.PENDANT:
            fair_recruit_rule = charge_rule(1)
        else:
            fair_recruit_rule = logictypes.LogicRule([recruit_item])

    crono_trial_rule = logictypes.LogicRule(
        [
            [ctenums.CharID.LUCCA, char_id]
            for char_id in ctenums.CharID if char_id != ctenums.CharID.LUCCA
        ]
    )
    if recruit_assign_dict[RecruitID.CRONO_TRIAL]:
        crono_trial_rule = logictypes.LogicRule()

    progressive_clone_rule = logicfactory.ProgressiveRule(
        [ctenums.ItemID.C_TRIGGER, ctenums.ItemID.CLONE]
    )
    progressive_shell_rule = logicfactory.ProgressiveRule(
        [ctenums.ItemID.RAINBOW_SHELL, ctenums.ItemID.PRISMSHARD]
    )
    eot_portal_rule = logictypes.LogicRule(
        list(list(x) for x in combinations(CharID, 4))
    ) & logictypes.LogicRule([ItemID.GATE_KEY])

    bb_rule = logictypes.LogicRule([memory.Flags.HAS_ALGETTY_PORTAL])
    if logic_options.force_early_flight:
        bb_rule = bb_rule & logictypes.LogicRule([ctenums.ItemID.JETSOFTIME])

    extra_connectors = []
    if logic_options.boats_of_time:
        extra_connectors += [
            RegionConnector(
                "truce_ticket_office", "choras_1000_overworld",
                "ferry_to_choras",
                reversible=False
            ),
            RegionConnector(
                "truce_ticket_office", "choras_600_overworld",
                "ferry_to_choras_600",
                rule=logictypes.LogicRule([ItemID.GATE_KEY]),
                reversible=False
            ),
            RegionConnector(
                "truce_ticket_office", "ozzies_fort_overworld",
                "ferry_to_ozzie",
                rule=logictypes.LogicRule([ItemID.GATE_KEY]),
                reversible=False
            ),
            RegionConnector(
                "truce_ticket_office", "giants_claw_overworld",
                "ferry_to_claw",
                rule=logictypes.LogicRule([ItemID.GATE_KEY]),
                reversible=False
            ),
        ]

    if logic_options.jets_of_time:
            extra_connectors.append(
                RegionConnector(
                    "blackbird_scaffolding", "epoch_reborn",
                    "jets_turn_in",
                    rule=logictypes.LogicRule([ItemID.JETSOFTIME]),
                    reversible=False
                ),
            )

    return extra_connectors + [
        RegionConnector(
            "starting_rewards", "cronos_house",
            "game_start",
        ),
        RegionConnector(
            "cronos_house", "cronos_house_clone",
            "collect_crono_clone",
            logictypes.LogicRule([memory.Flags.WON_CRONO_CLONE])
        ),
        RegionConnector(
            "cronos_house", "cronos_house_mom",
            "get_allowance",
            logictypes.LogicRule([ctenums.CharID.CRONO])
        ),
        RegionConnector(
            "truce_inn_1000", "truce_inn_1000_sealed",
            "truce_inn_pendant_charge",
            charge_rule(2)
        ),
        RegionConnector(
            "truce_ticket_office", "porre_ticket_office",
            "ferry"
        ),
        RegionConnector(
            "guardia_castle_1000", "guardia_castle_1000_sealed",
            "guardia_castle_1000_pendant_charge",
            charge_rule(2)
        ),
        RegionConnector(
            "guardia_castle_1000", "guardia_castle_1000_yakra",
            "use_yakra_key",
            logictypes.LogicRule([ctenums.ItemID.YAKRA_KEY])
        ),
        RegionConnector(
            "guardia_castle_1000", "crono_trial",
            "crono_trial",
            rule=crono_trial_rule
        ),
        RegionConnector(
            "crono_trial", "crono_trial_boss",
            "gain_trial_recruit"
        ),
        RegionConnector(
            "guardia_castle_1000", "guardia_castle_treasury",
            "initiate_shell_quest",
            rule=logictypes.LogicRule([memory.Flags.GUARDIA_TREASURY_EXISTS])
        ),
        RegionConnector(
            "guardia_castle_treasury", "guardia_castle_rbow_shell",
            "marle_rbow_shell",
            rule=logictypes.LogicRule([CharID.MARLE])
        ),
        RegionConnector(
            "guardia_castle_1000", "kings_trial_resolution",
            "fight_yakra_xiii",
            rule=logictypes.LogicRule([CharID.MARLE, memory.Flags.GUARDIA_TREASURY_EXISTS]) & progressive_shell_rule(2)
        ),
        RegionConnector(
            "kings_trial_resolution", "melchior_forge_castle",
            "sunstone_to_melchior",
            rule=logictypes.LogicRule([ctenums.ItemID.SUN_STONE])
        ),
        RegionConnector(
            "porre_mayor_1000", "porre_mayor_1000_sealed",
            "porre_mayor_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "porre_mayor_1000", "porre_mayor_moonstone",
            "porre_mayor_jerky_reward",
            rule=logictypes.LogicRule([memory.Flags.GAVE_AWAY_JERKY_PORRE])
        ),
        RegionConnector(
            "millennial_fair", "millennial_fair_recruit",
            "fair_recruit",
            rule=fair_recruit_rule
        ),
        RegionConnector(
            "millennial_fair", "millennial_fair_bekkler",
            link_name="obtain_clone",
            rule=progressive_clone_rule(1)  # Or Crono?
        ),
        RegionConnector(
            "guardia_forest_1000", "guardia_forest_1000_sealed",
            "guardia_forest_1000_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "heckran_cave", "heckran_sealed",
            "heckran_cave_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "forest_ruins", "forest_ruins_pyramid",
            "forest_ruins_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "luccas_house", "luccas_house_heckran",
            "heckran_taban_vest",
            rule=logictypes.LogicRule([memory.Flags.HECKRAN_DEFEATED])
        ),
        RegionConnector(
            "luccas_house", "luccas_house_forge",
            "forge_taban_helm",
            rule=logictypes.LogicRule([memory.Flags.HAS_FORGED_MASAMUNE])
        ),
        RegionConnector(
            "luccas_house", "luccas_house_charged_pendant",
            "charge_taban_suit",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "millennial_fair", "truce_canyon",
            "telepod_portal"
        ),
        RegionConnector(
            "millennial_fair", "end_of_time",
            "telepod_portal_eot",
            rule=eot_portal_rule,
            reversible=False
        ),
        RegionConnector(
            "end_of_time", "millennial_fair",
            "eot_fair_pillar",
            rule=logictypes.LogicRule([memory.Flags.HAS_TRUCE_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "end_of_time", "truce_canyon",
            "eot_truce_canyon_pillar",
            rule=logictypes.LogicRule([memory.Flags.HAS_TRUCE_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "guardia_castle_600", "guardia_castle_600_shell",
            "shell_turn_in",
            rule=progressive_shell_rule(1)
        ),
        RegionConnector(
            "manoria_sanctuary", "manoria_cathedral",
            "pipe_organ_door",
            rule=logictypes.LogicRule()
        ),
        RegionConnector(
            "guardia_castle_600", "guardia_castle_600_recruit",
            "castle_recruit",
            rule=logictypes.LogicRule([memory.Flags.MANORIA_BOSS_DEFEATED])
        ),
        RegionConnector(
            "guardia_castle_600", "guardia_castle_600_sealed",
            "guardia_castle_600_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "guardia_forest_600", "guardia_forest_600_sealed",
            link_name="guardia_forest_600_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "fionas_villa", "fionas_villa_desert",
            link_name="robo_helps_fiona",
            rule=logictypes.LogicRule([memory.Flags.SUNKEN_DESERT_BOSS_DEFEATED,
                                       ctenums.CharID.ROBO])
        ),
        RegionConnector(
            "cursed_woods", "burrow_medal",
            "show_frog_medal",
            rule=logictypes.LogicRule([ctenums.ItemID.HERO_MEDAL]) | masa_rule(1)
        ),
        RegionConnector(
            "cursed_woods", "burrow_recruit",
            "show_burrow_recruit_masamune",
            rule=masa_rule(1)
        ),
        RegionConnector(
            "tatas_house", "tata_reward",
            "denadoro_and_sword_part",
            rule=(
                logictypes.LogicRule([[ctenums.ItemID.BENT_HILT], [ctenums.ItemID.BENT_SWORD]]) &
                logictypes.LogicRule([memory.Flags.TATA_SCENE_COMPLETE])
            )
        ),
        RegionConnector(
            "lab_32_west", "lab_32_middle",
            "bike_key_west",
            rule=logictypes.LogicRule([ctenums.ItemID.BIKE_KEY])
        ),
        RegionConnector(
            "lab_32_west", "johnny_race",
            "johnny_race_west",
            rule=logictypes.LogicRule([ctenums.ItemID.BIKE_KEY, ctenums.CharID.CRONO]),
            reversible=False
        ),
        RegionConnector(
            "johnny_race", "johnny_race_log",
            "race_good_score",
            rule=logictypes.LogicRule([ctenums.ItemID.RACE_LOG]),
            reversible=False
        ),
        RegionConnector(
            "lab_32_east", "lab_32_middle",
            "bike_key_east",
            rule=logictypes.LogicRule([ctenums.ItemID.BIKE_KEY])
        ),
        RegionConnector(
            "lab_32_east", "johnny_race",
            "johnny_race_east",
            rule=logictypes.LogicRule([ctenums.ItemID.BIKE_KEY, ctenums.CharID.CRONO]),
            reversible=False
        ),
        RegionConnector(
            "death_peak_entrance", "death_peak",
            "climb_death_peak",
            rule=progressive_clone_rule(2)
        ),
        RegionConnector(
            "arris_dome", "arris_dome_sealed",
            "arris_dome_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "arris_dome", "arris_dome_doan",
            "arris_dome_seed_turnin",
            rule=logictypes.LogicRule([ctenums.ItemID.SEED])
        ),
        RegionConnector(
            "proto_dome", "proto_dome_portal",
            "proto_dome_power",
            rule=logictypes.LogicRule([memory.Flags.PROTO_DOME_DOOR_UNLOCKED]),
            reversible=True
        ),
        RegionConnector(
            "keepers_dome", "keepers_dome_sealed",
            "keepers_dome_sealed_door",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "dactyl_nest", "dactyl_nest_recruit",
            "dactyl_nest_summit",
            rule=logictypes.LogicRule([ctenums.ItemID.DREAMSTONE])
        ),
        RegionConnector(
            "mystic_mts", "medina_portal",
            "mystic_mts_portal",
        ),
        RegionConnector(
            "choras_1000_carpenter_base", "choras_1000_carpenter_wife",
            "get_tools_from_carpenter_wife",
            rule=logictypes.LogicRule([memory.Flags.TALKED_TO_CHORAS_1000_CARPENTER])
        ),
        RegionConnector(
            "choras_west_cape", "choras_west_cape_grave",
            "pour_tomas_pop",
            rule=logictypes.LogicRule([ctenums.ItemID.TOMAS_POP])
        ),
        RegionConnector(
            "northern_ruins_1000", "northern_ruins_1000_repaired",
            "northern_ruins_1000_pendant_charge",
            rule=logictypes.LogicRule([memory.Flags.NORTHERN_RUINS_REPAIRS_COMPLETE])
        ),
        RegionConnector(
            "northern_ruins_1000", "northern_ruins_1000_sealed",
            "northern_ruins_1000_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "northern_ruins_1000", "northern_ruins_1000_frog",
            "northern_ruins_1000_frog_locked",
            rule=logictypes.LogicRule([memory.Flags.MASAMUNE_UPGRADED])
        ),
        RegionConnector(
            "porre_elder_600", "porre_elder_600_jerky",
            "give_away_jerky",
            rule=logictypes.LogicRule([ItemID.JERKY, ItemID.JERKY])
        ),
        RegionConnector(
            "porre_elder_600", "porre_elder_600_sealed",
            "porre_elder_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "melchiors_hut", "melchiors_hut_forge",
            "forge_masa",
            rule=(
                    logictypes.LogicRule([ItemID.BENT_HILT, ItemID.BENT_SWORD, ItemID.DREAMSTONE]) &
                    (logictypes.LogicRule([CharID.ROBO]) | logictypes.LogicRule([CharID.LUCCA]))
            )
        ),
        RegionConnector(
            "bangor_dome", "bangor_dome_sealed",
            "bangor_dome_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "trann_dome", "trann_dome_sealed",
            "trann_dome_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "denadoro_mts", "denadoro_gold_rock",
            "frog_gold_rock",
            rule=logictypes.LogicRule([CharID.FROG])
        ),
        RegionConnector(
            "choras_carpenter_600_base", "choras_carpenter_600",
            "carpenter_repair",
            rule=logictypes.LogicRule([memory.Flags.CHORAS_600_GAVE_CARPENTER_TOOLS])
        ),
        RegionConnector(
            "choras_cafe_600", "choras_cafe_600_tools",
            "give_tools",
            rule=logictypes.LogicRule([ItemID.TOOLS])
        ),
        RegionConnector(
            "northern_ruins_600", "northern_ruins_600_repaired",
            "northern_ruins_600_repaired",
            rule=logictypes.LogicRule([memory.Flags.NORTHERN_RUINS_REPAIRS_COMPLETE])
        ),
        RegionConnector(
            "northern_ruins_600_repaired", "northern_ruins_600_sealed",
            "northern_ruins_600_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "northern_ruins_600_repaired", "cyrus_grave_600",
            "cyrus_ghost",
            rule=logictypes.LogicRule([CharID.FROG, ItemID.MASAMUNE_1])
        ),
        RegionConnector(
            "giants_claw", "shared_tyrano_claw",
            "shared_tyrano_claw",
            reversible=False
        ),
        RegionConnector(
            "tyrano_lair", "shared_tyrano_claw",
            "shared_tyrano_claw",
            reversible=False
        ),
        RegionConnector(
            "magic_cave_entrance", "magic_cave",
            "open_magic_cave",
            rule=(
                logictypes.LogicRule([CharID.FROG, ItemID.MASAMUNE_1])
            ), reversible=False
        ),
        RegionConnector(
            "magic_cave", "magic_cave_sealed",
            "magic_cave_pendant_charge",
            rule=charge_rule(2)
        ),
        RegionConnector(
            "fiona_shrine", "fiona_campfire",
            "fiona_shrine_fix_robo",
            rule=logictypes.LogicRule([CharID.LUCCA, memory.Flags.ROBO_HELPS_FIONA])
        ),
        RegionConnector(
            "sun_keep_2300", "moonstone_quest",
            "charged_moonstone",
            rule=logictypes.LogicRule(
                [memory.Flags.MOONSTONE_PLACED_PREHISTORY, CharID.LUCCA]
            )
        ),
        RegionConnector(
            "sun_keep_prehistory", "sun_keep_prehistory_charge",
            "place_moonstone_prehistory",
            rule=logictypes.LogicRule([ItemID.MOON_STONE])
        ),
        RegionConnector(
            "end_of_time", "end_of_time_gaspar",
            "vanilla_ctrigger",
            rule=logictypes.LogicRule([memory.Flags.HAS_ALGETTY_PORTAL])
        ),
        RegionConnector(
            "proto_dome_portal", "end_of_time",
            "end_of_time_portal"
        ),
        RegionConnector(
            "end_of_time", "mystic_mts",
            "eot_mystic_mt_pillar",
            reversible=False
        ),
        RegionConnector(
            "mystic_mts", "end_of_time",
            "mystic_mt_eot_portal",
            rule=eot_portal_rule,
            reversible=False
        ),
        RegionConnector(
            "end_of_time", "lair_ruins_portal",
            "eot_lair_ruins_pillar",
            logictypes.LogicRule([memory.Flags.HAS_LAIR_RUINS_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "end_of_time", "dark_ages_portal",
            "eot_dark_ages_pillar",
            rule=logictypes.LogicRule([memory.Flags.HAS_DARK_AGES_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "dark_ages_portal", "lair_ruins_portal",
            "dark_ages_to_Lair_ruins_portal",
            rule=logictypes.LogicRule([memory.Flags.OW_LAVOS_HAS_FALLEN])
        ),
        RegionConnector(
            "dark_ages_portal", "end_of_time",
            "dark_ages_eot_portal",
            rule=eot_portal_rule,
            reversible=False
        ),
        RegionConnector(
            "end_of_time", "medina_portal",
            "eot_medina_pillar",
            reversible=False
        ),
        RegionConnector(
            "medina_portal", "end_of_time",
            "medina_eot_portal",
            rule=eot_portal_rule,
            reversible=False
        ),
        RegionConnector(
            "last_village_commons", "blackbird",
            "get_captured_by_dalton",
            rule=bb_rule
        ),
        RegionConnector(
            "blackbird", "epoch_reborn",
            "defeat_blackbird_wing_boss",
            reversible=False,
        ),
        RegionConnector(
            "skyway_enhasa_south", "land_bridge_enhasa_south",
            "take_skyway_enhasa_south"
        ),
        RegionConnector(
            "skyway_enhasa_north", "land_bridge_enhasa_north",
            "take_skyway_enhasa_north"
        ),
        RegionConnector(
            "skyway_kajar", "land_bridge_kajar",
            "take_skyway_kajar"
        ),
        RegionConnector(
            "zeal_teleporter_bottom", "zeal_teleporter_top",
            "zeal_teleporter_caves"
        ),
        RegionConnector(
            "truce_inn_600", "truce_inn_600_sealed",
            "truce_inn_600_pendant_charge",
            rule=charge_rule(2)
        ),
        # Flight OW rules -- Not complete graph, just spokes from one region
        RegionConnector(
            "porre_1000_overworld", "guardia_castle_1000_overworld",
            "flight_1000",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "medina_1000_overworld",
            "flight_1000",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "choras_1000_overworld",
            "flight_1000",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "sun_keep_1000_overworld",
            "flight_1000",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "guardia_castle_600_overworld",
            "flight_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        # Remove this if we break zenan.
        RegionConnector(
            "truce_600_overworld", "porre_600_overworld",
            "zenan_bridge_600",
        ),
        RegionConnector(
            "porre_1000_overworld", "porre_600_overworld",
            "flight_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "porre_600_overworld",
            "flight_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "magus_lair_overworld",
            "flight_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "ozzies_fort_overworld",
            "flight_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "sun_keep_600_overworld",
            "flight_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "giants_claw_overworld",
            "flight_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "trann_bangor_overworld",
            "flight_2300",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_FUTURE_TIMEGAUGE_ACCESS]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "arris_overworld",
            "flight_2300",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_FUTURE_TIMEGAUGE_ACCESS]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "proto_overworld",
            "flight_2300",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_FUTURE_TIMEGAUGE_ACCESS]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "sun_keep_2300_overworld",
            "flight_2300",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_FUTURE_TIMEGAUGE_ACCESS]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "geno_overworld",
            "flight_2300",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_FUTURE_TIMEGAUGE_ACCESS]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "sun_palace_overworld",
            "flight_2300",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_FUTURE_TIMEGAUGE_ACCESS]),
            reversible=False,
        ),
        RegionConnector(
            "porre_1000_overworld", "reptite_lair_overworld",
            "flight_prehistory",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False
        ),
        RegionConnector(
            "ioka_sweet_water_hut", "ioka_sweet_water_hut_ayla",
            "ayla_recruited_item",
            rule=logictypes.LogicRule([ctenums.CharID.AYLA]),
            reversible=False
        ),
        RegionConnector(
            "ioka_trading_post", "ioka_trading_post_base",
            "upgraded_trading_post",
            rule=logictypes.LogicRule([logictypes.StrangeReward.TRADING_MATERIALS])
        ),
        RegionConnector(
            "ioka_trading_post", "ioka_trading_post_upgrade",
            "upgraded_trading_post",
            rule=logictypes.LogicRule([memory.Flags.HAS_DARK_AGES_TIMEGAUGE_ACCESS,
                                       logictypes.StrangeReward.TRADING_MATERIALS
                                       ])
        ),
        RegionConnector(
            "ioka_trading_post", "ioka_trading_post_special",
            "special_trading_post",
            rule=logictypes.LogicRule([memory.Flags.HAS_ALGETTY_PORTAL,
                                       # logictypes.StrangeReward.TRADING_MATERIALS
                                       ])
        ),
        RegionConnector(
            "ioka_overworld", "reptite_lair_overworld",
            "flight_prehistory_dactyl",
            rule=logictypes.LogicRule([memory.Flags.OBTAINED_DACTYLS]),
            reversible=False
        ),
        RegionConnector(
            "ioka_overworld", "sun_keep_prehistory_overworld",
            "flight_prehistory",
            rule=logictypes.LogicRule([memory.Flags.OBTAINED_DACTYLS]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "sun_keep_prehistory_overworld",
            "flight_prehistory",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "tyrano_lair_overworld",
            "flight_prehistory",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False
        ),
        RegionConnector(
            "ioka_overworld", "tyrano_lair_overworld",
            "flight_prehistory_dactyl",
            rule=logictypes.LogicRule([memory.Flags.OBTAINED_DACTYLS]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "lair_ruins_overworld",
            "flight_prehistory",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT]),
            reversible=False
        ),
        RegionConnector(
            "ioka_overworld", "lair_ruins_overworld",
            "flight_prehistory_dactyl",
            rule=logictypes.LogicRule([memory.Flags.OBTAINED_DACTYLS]),
            reversible=False
        ),
        RegionConnector(
            "laruba_ruins", "laruba_ruins_chief",
            "dreamstone_to_laruba_chief",
            rule=logictypes.LogicRule([ItemID.DREAMSTONE]),
            reversible=False
        ),
        RegionConnector(
            "forest_maze_north", "forest_maze",
            "ayla_moves_kino",
            rule=logictypes.LogicRule([CharID.AYLA]),
            reversible=False
        ),
        RegionConnector(
            "forest_maze", "forest_maze_north",
            "kino_from_back",
            reversible=False
        ),
        RegionConnector(
            "tyrano_lair_entrance", "tyrano_lair",
            "ayla_opens_skull",
            rule=logictypes.LogicRule([CharID.AYLA]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "dark_ages_skyway_island_overworld",
            "flight_dark_ages",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_DARK_AGES_TIMEGAUGE_ACCESS]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "dark_ages_portal_overworld",
            "flight_dark_ages",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_DARK_AGES_TIMEGAUGE_ACCESS]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "last_village_portal_overworld",
            "flight_last_village",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_DARK_AGES_TIMEGAUGE_ACCESS,
                                       memory.Flags.HAS_ALGETTY_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "last_village_sun_keep_overworld",
            "flight_last_village",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_DARK_AGES_TIMEGAUGE_ACCESS,
                                       memory.Flags.HAS_ALGETTY_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "guardia_forest_1000", "bangor_dome",
            "guardia_forest_portal"
        ),
        RegionConnector(
            "guardia_forest_1000", "end_of_time",
            "guardia_forest_portal_eot",
            rule=eot_portal_rule,
            reversible=False,
        ),
        RegionConnector(
            "end_of_time", "guardia_forest_1000",
            "eot_forest_pillar",
            rule=logictypes.LogicRule([memory.Flags.HAS_BANGOR_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "end_of_time", "bangor_dome",
            "eot_bangor_pillar",
            rule=logictypes.LogicRule([memory.Flags.HAS_BANGOR_PORTAL]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "porre_600_overworld",
            "epoch_warp_1000_to_600",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "ioka_overworld",
            "epoch_warp_1000_to_prehistory",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH]),
            reversible=False
        ),
        RegionConnector(
            "porre_1000_overworld", "dark_ages_portal_overworld",
            "epoch_warp_1000_to_dark_ages",
            rule=logictypes.LogicRule([logictypes.ScriptReward.EPOCH,
                                       memory.Flags.HAS_DARK_AGES_TIMEGAUGE_ACCESS]),
            reversible=False
        ),
        RegionConnector(
            "keepers_dome_sealed", "dark_ages_portal_overworld",
            "epoch_keepers_dark_ages",
            reversible=False,
        ),
        RegionConnector(
            "algetty", "mt_woe",
            "through_beast_cave"
        ),
        RegionConnector(
            "algetty", "last_village_empty_hut",
            link_name="algetty_portal",
            rule=logictypes.LogicRule([memory.Flags.HAS_ALGETTY_PORTAL])
        ),
        RegionConnector(
            "kajar", "kajar_nu_scratch",
            "scratch_the_nu",
            rule=logictypes.LogicRule([memory.Flags.DISCOVERED_NU_SCRATCH_POINT])
        ),
        RegionConnector(
            "zeal_palace", "zeal_mammon_m",
            "mammon_m_give_pendant",
            rule=charge_rule(1)
        ),
        RegionConnector(
            "zeal_palace", "ocean_palace",
            "zeal_palace_pendant_charge",
            rule=charge_rule(2) | logictypes.LogicRule([CharID.MAGUS])
        ),
        RegionConnector(
            "ocean_palace", "ocean_palace_mammon_m",
            "ruby_knife_mammon_m",
            rule=logictypes.LogicRule([ItemID.RUBY_KNIFE])
        ),
        RegionConnector(
            "porre_600_overworld", "sunken_desert_overworld",
            "plant_lady_saves_seed",
            rule=logictypes.LogicRule([memory.Flags.PLANT_LADY_SAVES_SEED])
        ),
        RegionConnector(
            "porre_1000_overworld", "fionas_shrine_overworld",
            "save_the_desert",
            rule=logictypes.LogicRule([memory.Flags.SUNKEN_DESERT_BOSS_DEFEATED])
        ),
        RegionConnector(
            "sun_keep_prehistory", "sun_keep_prehistory_charge",
            "place_moon_stone_prehistory",
            rule=logictypes.LogicRule([ItemID.MOON_STONE])
        ),
        # RegionConnector(
        #     "sun_keep_2300", "luccas_house_sunstone",
        #     "lucca_refines_sunstone",
        #     rule=logictypes.LogicRule([memory.Flags.MOONSTONE_PLACED_PREHISTORY, CharID.LUCCA])
        # ),
        RegionConnector(
            "porre_1000_overworld", "black_omen",
            "fly_to_black_omen",
            rule=logictypes.LogicRule([logictypes.ScriptReward.FLIGHT,
                                       memory.Flags.HAS_DARK_AGES_TIMEGAUGE_ACCESS,
                                       memory.Flags.HAS_ALGETTY_PORTAL])
        ),
        RegionConnector(
            "dorino_bromide_base", "dorino_bromide_reward",
            "bromide_turn_in",
            rule=logictypes.LogicRule([memory.Flags.OBTAINED_NAGAETTE_BROMIDE])
        ),
        RegionConnector(
            "dorino_inn", "dorino_inn_marle",
            "rest_with_marle_recruited",
            rule=logictypes.LogicRule([ctenums.CharID.MARLE]),
            reversible=False
        ),
        RegionConnector(
            "geno_dome", "geno_dome_inside",
            "robo_geno_access",
            rule=logictypes.LogicRule([CharID.ROBO])
        ),
        RegionConnector(
            "factory_ruins", "factory_ruins_inside",
            "robo_factory_access",
            rule=logictypes.LogicRule([CharID.ROBO])
        )
    ]


def get_default_map():
    ow_regions = owregions.get_ow_regions()
    loc_regions = locregions.get_all_loc_regions()
    exit_connectors = get_default_exit_connectors()
    region_connectors = get_default_region_connectors(
        recruit_assign_dict=recruitassign.get_default_recruit_assignment_dict(),
        logic_options=logicoptions.LogicOptions()
    )

    return RegionMap(
        ow_regions, loc_regions, exit_connectors, region_connectors
    )


def assignment_dict_to_exit_connectors(
        assignment_dict: dict[OWExit, OWExit],
) -> list[ExitConnector]:
    """Assumes randomized connectors."""
    new_connectors = [
        x for x in get_default_exit_connectors()
        if x.from_exit != OWExit.TYRANO_LAIR
    ]
    connector_map = {
        connector.from_exit: connector.to_exit
        for connector in new_connectors
    }

    connector_map[OWExit.LAIR_RUINS] = LocExit.TYRANO_LAIR
    connector_map[OWExit.LAST_VILLAGE_PORTAL] = LocExit.LAIR_RUINS

    for connector in new_connectors:
        connector.to_exit = connector_map[assignment_dict[connector.from_exit]]

    return new_connectors


def get_map_from_assignment(
        recruit_assignment: dict[ctenums.RecruitID, ctenums.CharID | None],
        entrance_assignment: dict[OWExit, OWExit],
) -> RegionMap:
    """Create the map from recruit and entrance assignment"""
    region_connectors = get_default_region_connectors(recruit_assignment)

    # A little janky.  If tyrano lair is in the entrance assignment, it's not random.
    if OWExit.TYRANO_LAIR in entrance_assignment:
        exit_connectors = get_default_exit_connectors()
    else:
        exit_connectors = assignment_dict_to_exit_connectors(entrance_assignment)

    region_map = RegionMap(
        owregions.get_ow_regions(),
        locregions.get_all_loc_regions(),
        exit_connectors,
        region_connectors
    )

    return region_map
