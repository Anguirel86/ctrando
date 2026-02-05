"""Module to store the state of the randomizer during generation."""
from dataclasses import dataclass, field

from ctrando.characters import characterwriter
from ctrando.shops import shoptypes
from ctrando.attacks import pctech
from ctrando.bosses import bosstypes, bossrando
from ctrando.enemyai import enemyaimanager, vanillafixes
from ctrando.enemydata import enemystats
from ctrando.logic import logictypes
from ctrando.base import basepatch
from ctrando.items import itemdata
from ctrando.characters import ctpcstats
from ctrando.common import ctenums, ctrom, memory
from ctrando.locations import locationevent, locationtypes
from ctrando.locations.eventcommand import EventCommand as EC
from ctrando.locations.eventfunction import EventFunction as EF
from ctrando.locations.scriptmanager import ScriptManager
from ctrando.objectives import objectivetypes
from ctrando.overworlds import overworld, owexitdata
from ctrando.overworlds.owmanager import OWManager
from ctrando.recruits import recruitassign
from ctrando.treasures import treasuretypes as ttypes
from ctrando.entranceshuffler import regionmap


_LocEvent = locationevent.LocationEvent
_Overworld = overworld.Overworld


def add_dream_devourer(
        enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
):
    dd_id = ctenums.EnemyID.DREAM_DEVOURER
    # dd_id = ctenums.EnemyID.KRAWLIE
    stats = enemy_dict[dd_id]

    stats.hp = 32000
    stats.defense = 220
    stats.mdef = 80
    stats.name = "DrmDevourer"

    # Experimental
    stats.level = 80
    stats.magic = 220
    stats.offense = 230
    stats.evade = 40
    stats.hit = 100
    stats.speed = 16

    # No rewards
    stats.xp = 0
    stats.tp = 0
    stats.gp = 0

    schala_id = ctenums.EnemyID.SCHALA
    stats = enemy_dict[schala_id]
    stats.hp = 0


@dataclass
class ConfigState:
    """
    Minimal config data for writing a randomized CT Rom.
    Maybe this is more like plando settings?
    """
    item_db: itemdata.ItemDB
    treasure_assignment: dict[ctenums.TreasureID, ttypes.RewardType]
    pcstat_manager: ctpcstats.PCStatsManager
    pctech_manager: pctech.PCTechManager
    enemy_data_dict: dict[ctenums.EnemyID, enemystats.EnemyStats]
    # enemy_sprite_dict: dict[ctenums.EnemyID, enemystats.EnemySpriteData]
    boss_assignment_dict: dict[bosstypes.BossSpotID, bosstypes.BossID]
    shop_manager: shoptypes.ShopManager
    recruit_dict: dict[ctenums.RecruitID, list[ctenums.CharID | None]]
    ow_exit_assignment_dict: dict[owexitdata.OWExitClass, owexitdata.OWExitClass]
    region_map: regionmap.RegionMap
    starting_rewards: list[logictypes.RewardType]
    objectives: list[objectivetypes.ObjectiveType]
    enemy_assign_dict: dict[ctenums.EnemyID, ctenums.EnemyID]

    @classmethod
    def get_default_config_from_ctrom(cls, ct_rom: ctrom.CTRom):
        item_db = itemdata.ItemDB.from_rom(ct_rom.getbuffer())
        basepatch.modifyitems.modify_item_stats(item_db)
        basepatch.modifyitems.add_ds_accessories(item_db)
        basepatch.modifyitems.update_boosts(item_db)

        data_dict: dict[ctenums.ItemID, tuple[str, str]] = {
            ctenums.ItemID.PENDANT_CHARGE: (" PendantChg",
                                            "The Pendant begins to glow..."),
            ctenums.ItemID.RAINBOW_SHELL: (" Rbow Shell",
                                           "Give to King in 600AD"),
            ctenums.ItemID.JETSOFTIME: (" JetsOfTime",
                                        " Use at Blackbird 12000BC"),
            ctenums.ItemID.SCALING_LEVEL: (" ScalingLvl", "Current level of enemies"),
            ctenums.ItemID.APITEM: (" APItem", "Archipelago item")
        }

        for item_id, (name_str, desc_str) in data_dict.items():
            item_db[item_id].set_name_from_str(name_str)
            item_db[item_id].set_desc_from_str(desc_str)

        item_db[ctenums.ItemID.SCALING_LEVEL].secondary_stats.is_key_item = True
        item_db[ctenums.ItemID.SCALING_LEVEL].secondary_stats.is_unsellable = True

        pcstat_manager = ctpcstats.PCStatsManager.read_from_ct_rom(ct_rom)
        characterwriter.fill_vanilla_tp_gaps(pcstat_manager)

        pctech_manager = pctech.PCTechManager.read_from_ctrom(ct_rom)
        pctech.fix_vanilla_techs(pctech_manager)

        enemy_data_dict = enemystats.get_stat_dict_from_ctrom(ct_rom)
        enemy_data_dict[ctenums.EnemyID.ELDER_SPAWN_SHELL].name = "Elder Spawn"

        ### Trying some Balance Here
        new_xp = enemy_data_dict[ctenums.EnemyID.R_SERIES].xp / 10
        enemy_data_dict[ctenums.EnemyID.R_SERIES].xp = round(new_xp)

        enemy_data_dict[ctenums.EnemyID.DALTON_PLUS].tp = 25

        add_dream_devourer(enemy_data_dict)

        boss_assignment_dict = bosstypes.get_default_boss_assignment()
        shop_manager = shoptypes.ShopManager.read_from_ctrom(ct_rom)
        treasure_assignment = ttypes.get_vanilla_assignment()
        recruit_dict = recruitassign.get_default_recruit_assignment_dict()

        ow_exit_assignment_dict = {
            exit_class: exit_class for exit_class in owexitdata.OWExitClass
        }
        region_map = regionmap.get_default_map()
        starting_rewards = []
        objectives = [None for _ in range(8)]
        enemy_assign_dict: dict[ctenums.EnemyID, ctenums.EnemyID] = dict()

        return cls(
            item_db, treasure_assignment, pcstat_manager,
            pctech_manager, enemy_data_dict, boss_assignment_dict,
            shop_manager, recruit_dict, ow_exit_assignment_dict, region_map,
            starting_rewards, objectives, enemy_assign_dict
        )


@dataclass()
class PostConfigState:
    """
    State that is not directly configured by the settings
    """
    script_manager: ScriptManager
    overworld_manager: OWManager
    loc_exit_dict: dict[ctenums.LocID, list[locationtypes.LocationExit]]
    loc_data_dict: dict[ctenums.LocID, locationtypes.LocationData]
    treasure_data_dict: dict[ctenums.TreasureID, ttypes.RewardSpot]
    enemy_sprite_dict: dict[ctenums.EnemyID, enemystats.EnemySpriteData]
    enemy_ai_manager: enemyaimanager.EnemyAIManager

    @classmethod
    def get_default_state_from_ctrom(cls, ct_rom: ctrom.CTRom):
        script_manager = ScriptManager(ct_rom)
        overworld_manager = OWManager(ct_rom)
        loc_exit_dict = locationtypes.get_exit_dict_from_ctrom(ct_rom)
        loc_data_dict = {
            loc_id: locationtypes.LocationData.read_from_ctrom(ct_rom, loc_id)
            for loc_id in ctenums.LocID
        }
        treasure_data_dict = ttypes.get_base_treasure_dict()
        enemy_sprite_dict = enemystats.get_sprite_dict_from_ctrom(ct_rom)

        enemy_ai_manager = enemyaimanager.EnemyAIManager.read_from_ct_rom(ct_rom)
        vanillafixes.fix_son_of_sun_ai(enemy_ai_manager)
        vanillafixes.fix_magus_masa2_ai(enemy_ai_manager)

        return cls(script_manager, overworld_manager, loc_exit_dict, loc_data_dict,
                   treasure_data_dict, enemy_sprite_dict, enemy_ai_manager)

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        locationtypes.write_exit_dict_to_ctrom(ct_rom, self.loc_exit_dict)
        for tid, treasure in self.treasure_data_dict.items():
            if tid == ctenums.TreasureID.CRONOS_MOM:
                pass
            treasure.write_to_ct_rom(ct_rom, self.script_manager)

        for loc_id, loc_data in self.loc_data_dict.items():
            loc_data.write_to_ctrom(ct_rom, loc_id)

        self.script_manager.write_all_scripts_to_ctrom()
        for enemy_id, enemy_sprite in self.enemy_sprite_dict.items():
            enemy_sprite.write_to_ctrom(ct_rom, enemy_id)

        self.enemy_ai_manager.write_to_ct_rom(ct_rom)
        self.overworld_manager.write_all_overworlds_to_ctrom()


@dataclass
class RandoState:
    """
    Deprecated.  We split between Config and PostConfig now.

    Class which holds the state of the randomizer.

    The data in this class should never be touched by a user.  Users interact
    with the randomizer through randosettings and randoconfig
    """
    ct_rom: ctrom.CTRom
    script_manager: ScriptManager = field(init=False)
    overworld_manager: OWManager = field(init=False)
    item_db: itemdata.ItemDB = field(init=False)
    loc_exit_dict: dict[ctenums.LocID, list[locationtypes.LocationExit]] = \
        field(init=False)
    loc_data_dict: dict[ctenums.LocID, locationtypes.LocationData] = \
        field(init=False)
    treasure_data_dict: dict[ctenums.TreasureID, ttypes.RewardSpot] = \
        field(init=False)
    pcstat_manager: ctpcstats.PCStatsManager = field(init=False)
    pctech_manager: pctech.PCTechManager = field(init=False)
    enemy_data_dict: dict[ctenums.EnemyID, enemystats.EnemyStats] = field(init=False)
    enemy_sprite_dict: dict[ctenums.EnemyID, enemystats.EnemySpriteData] =  field(init=False)
    enemy_ai_manager: enemyaimanager.EnemyAIManager = field(init=False)
    boss_assignment_dict: dict[bosstypes.BossSpotID, bosstypes.BossID] = field(init=False)
    shop_manager: shoptypes.ShopManager = field(init=False)
    recruit_dict: dict[ctenums.RecruitID, ctenums.CharID | None] = field(init=False)
    ow_exit_assignment_dict: dict[owexitdata.OWExitClass, owexitdata.OWExitClass] = field(init=False)
    starting_rewards: list[logictypes.RewardType] = field(init=False)
    objectives: list[objectivetypes.ObjectiveType] = field(init=False)

    def __post_init__(self):
        self.script_manager = ScriptManager(self.ct_rom)
        self.overworld_manager = OWManager(self.ct_rom)
        self.item_db = itemdata.ItemDB.from_rom(self.ct_rom.getbuffer())
        self.loc_exit_dict = locationtypes.get_exit_dict_from_ctrom(self.ct_rom)
        self.loc_data_dict = {
            loc_id: locationtypes.LocationData.read_from_ctrom(self.ct_rom, loc_id)
            for loc_id in ctenums.LocID
        }
        self.treasure_data_dict = ttypes.get_base_treasure_dict()
        self.pcstat_manager = ctpcstats.PCStatsManager.read_from_ct_rom(self.ct_rom)
        self.pctech_manager = pctech.PCTechManager.read_from_ctrom(self.ct_rom)
        self.enemy_data_dict = enemystats.get_stat_dict_from_ctrom(self.ct_rom)
        self.enemy_sprite_dict = enemystats.get_sprite_dict_from_ctrom(self.ct_rom)
        self.enemy_ai_manager = enemyaimanager.EnemyAIManager.read_from_ct_rom(self.ct_rom)
        self.boss_assignment_dict = bosstypes.get_default_boss_assignment()
        self.shop_manager = shoptypes.ShopManager.read_from_ctrom(self.ct_rom)

        # TODO: Move this elsewhere.
        self.recruit_dict = {
            ctenums.RecruitID.STARTER: ctenums.CharID.CRONO,
            ctenums.RecruitID.MILLENNIAL_FAIR: ctenums.CharID.MARLE,
            ctenums.RecruitID.CRONO_TRIAL: None,
            ctenums.RecruitID.PROTO_DOME: ctenums.CharID.ROBO,
            ctenums.RecruitID.FROGS_BURROW: ctenums.CharID.FROG,
            ctenums.RecruitID.DACTYL_NEST: ctenums.CharID.AYLA,
            ctenums.RecruitID.NORTH_CAPE: ctenums.CharID.MAGUS,
            ctenums.RecruitID.CATHEDRAL: ctenums.CharID.LUCCA,
            ctenums.RecruitID.DEATH_PEAK: None,
            ctenums.RecruitID.CASTLE: None
        }

        self.ow_exit_assignment_dict = {
            exit_class: exit_class for exit_class in owexitdata.OWExitClass
        }
        self.starting_rewards = []
        self.objectives = [None for _ in range(8)]

    # def update_ct_rom(self, settings: Settings = Settings() ):
    #     """Apply all changes made to scripts, etc to the ct_rom"""
    #     start = chesttext.write_desc_strings(self.ct_rom, self.item_db)
    #     chesttext.update_desc_str_start(self.ct_rom, start)
    #     chesttext.ugly_hack_chest_str(self.ct_rom)
    #     self.item_db.write_to_ctrom(self.ct_rom)
    #
    #     locationtypes.write_exit_dict_to_ctrom(self.ct_rom, self.loc_exit_dict)
    #
    #     for loc_id, loc_data in self.loc_data_dict.items():
    #         loc_data.write_to_ctrom(self.ct_rom, loc_id)
    #
    #     for tid, treasure in self.treasure_data_dict.items():
    #         assigned_treasure = treasure.reward
    #         if assigned_treasure == ctenums.ItemID.NONE:
    #             assigned_treasure = ctenums.ItemID.MOP
    #
    #         # TODO: Do progressive items more gracefully...
    #         if assigned_treasure == ctenums.ItemID.PENDANT_CHARGE:
    #             assigned_treasure = ctenums.ItemID.PENDANT
    #         if assigned_treasure == ctenums.ItemID.MASAMUNE_2:
    #             assigned_treasure = ctenums.ItemID.MASAMUNE_1
    #         if assigned_treasure == ctenums.ItemID.PRISMSHARD:
    #             assigned_treasure = ctenums.ItemID.RAINBOW_SHELL
    #         if assigned_treasure == ctenums.ItemID.CLONE:
    #             assigned_treasure = ctenums.ItemID.C_TRIGGER
    #
    #         treasure.reward = assigned_treasure
    #
    #         if isinstance(treasure.reward, ttypes.Gold) and isinstance(treasure, ttypes.ScriptTreasure):
    #             # print(tid, treasure.reward)
    #             treasure.write_to_ct_rom(self.ct_rom, self.script_manager)
    #         else:
    #             treasure.write_to_ct_rom(self.ct_rom, self.script_manager)
    #
    #     write_initial_rewards(self.starting_rewards, self.script_manager)
    #
    #     recruitwriter.write_recruits_to_ct_rom(
    #         self.recruit_dict, self.script_manager, settings
    #     )
    #     bossrando.write_bosses_to_ct_rom(self.boss_assignment_dict, self.script_manager)
    #
    #     self.script_manager.write_all_scripts_to_ctrom()
    #     self.overworld_manager.write_all_overworlds_to_ctrom()
    #     self.pcstat_manager.write_to_ct_rom(self.ct_rom)
    #     self.pctech_manager.write_to_ctrom(self.ct_rom, 5.0)
    #
    #     for enemy_id, enemy_stats in self.enemy_data_dict.items():
    #         enemy_stats.write_to_ctrom(self.ct_rom, enemy_id)
    #
    #     for enemy_id, enemy_sprite in self.enemy_sprite_dict.items():
    #         enemy_sprite.write_to_ctrom(self.ct_rom, enemy_id)
    #
    #     self.enemy_ai_manager.write_to_ct_rom(self.ct_rom)
    #     self.shop_manager.write_to_ctrom(self.ct_rom)
    #

def get_reward_event_code(
        reward: logictypes.RewardType,
        temp_addr: int = 0x7F0300
) -> EF:
    if isinstance(reward, memory.Flags):
        return EF().add(EC.set_flag(reward))
    elif isinstance(reward, ctenums.ItemID):
        return EF().add(EC.add_item(reward))
    elif isinstance(reward, logictypes.ScriptReward):
        if reward == logictypes.ScriptReward.FLIGHT:
            # epoch_status_byte = memory.Flags.EPOCH_OBTAINED.value.bit
            epoch_status_addr = memory.Flags.EPOCH_CAN_FLY.value.address
            set_epoch_block = (
                EF()
                .add(EC.assign_mem_to_mem(epoch_status_addr, temp_addr, 1))
                .add(EC.set_reset_bits(temp_addr, memory.Flags.EPOCH_CAN_FLY.value.bit))
                .add(EC.assign_mem_to_mem(temp_addr, epoch_status_addr, 1))
                .add(EC.set_flag(memory.Flags.OBTAINED_EPOCH_FLIGHT))
            )
            return set_epoch_block
        elif reward == logictypes.ScriptReward.EPOCH:
            ret_fn = (
                EF().add(EC.set_flag(memory.Flags.EPOCH_OBTAINED_LOC))
                .add(EC.assign_val_to_mem(ctenums.LocID.OW_PRESENT, memory.Memory.EPOCH_MAP_LO, 2))
            )
            return ret_fn

    raise ValueError


def get_initial_rewards_ef(intial_rewards: list[logictypes.RewardType]) -> EF:
    ret_ef = EF()

    normal_item_reward_count: dict[ctenums.ItemID, int] = dict()
    other_rewards: list[logictypes.RewardType] = []
    scaling_items = basepatch.get_scaling_key_items()

    for reward in intial_rewards:
        if isinstance(reward, ctenums.ItemID) and reward not in scaling_items:
            count = normal_item_reward_count.get(reward, 0)
            normal_item_reward_count[reward] = count + 1
        else:
            other_rewards.append(reward)


    item_bytes = bytes(list(normal_item_reward_count.keys()))
    count_bytes = bytes(list(normal_item_reward_count.values()))

    if item_bytes:
        item_st = 0x7E2400
        count_st = item_st + 0x000100
        ret_ef.add(EC.copy_memory(item_st, item_bytes))
        ret_ef.add(EC.copy_memory(count_st, count_bytes))

    for reward in other_rewards:
        ret_ef.append(get_reward_event_code(reward))

    return ret_ef


def write_initial_rewards(
        initial_rewards: list[logictypes.RewardType],
        script_manager: ScriptManager):

    func = get_initial_rewards_ef(initial_rewards)

    script = script_manager[ctenums.LocID.LOAD_SCREEN]

    # Note: We look *after* the default Epoch status is set.
    pos = script.find_exact_command(EC.set_flag(memory.Flags.OW_VORTEX_ACTIVE))
    script.insert_commands(func.get_bytearray(), pos)
