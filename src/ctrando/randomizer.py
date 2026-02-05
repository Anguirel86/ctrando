"""The main randomizer."""
import copy
import enum
import pathlib
import pickle
import random
import sys
import time
import tomllib
import typing
from typing import TextIO

from ctrando.arguments import (
    arguments, enemyscaling, techoptions, tomloptions, gearrandooptions
)
from ctrando.enemydata import enemystats, rewardrando, enemyrando
from ctrando.logic import logictweaks, logictypes
from ctrando.shops import shoptypes, shoprando

from ctrando.attacks import (
    pctechrandomizer, techdescriptions, pctech, animationscript, scriptreassign,
    techmenu
)
from ctrando.base import basepatch, xptpmod, modifymaps, chesttext
from ctrando.bosses import staticbossscaling, bossrando, bosstypes
from ctrando.characters import characterwriter, charactermods
from ctrando.common import ctrom, ctenums, randostate
from ctrando.common.random import RNGType

from ctrando import encounters

from ctrando.enemyai import randofixes
from ctrando.enemyscaling import patchscaling
from ctrando.entranceshuffler import (
    entrancefiller, entranceassign, regionmap, maptraversal, locregions
)
from ctrando.entranceshuffler.entrancefiller import update_starting_rewards
from ctrando.items import gearrando, itemdata
from ctrando.locations.scriptmanager import ScriptManager
from ctrando.objectives import objectivewriter, objectivelogic
from ctrando.postrando import postrandowriter, flashreduce
from ctrando.recruits import recruitwriter
from ctrando.strings import ctstrings
from ctrando.treasures import treasureassign, treasuretypes as ttypes

from ctrando.effects import effecttypes


# Should move this into patchscaling
def apply_dynamic_scaling(
        ct_rom: ctrom.CTRom,
        script_manager: ScriptManager,
        enemy_data_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        region_map: regionmap.RegionMap,
        treasure_assignment: dict[ctenums.TreasureID, ttypes.RewardType],
        recruit_assignment: dict[ctenums.RecruitID, ctenums.CharID | None],
        settings: arguments.Settings,
):
    scaling_opts = settings.scaling_options
    if scaling_opts.dynamic_scaling_scheme == enemyscaling.DynamicScalingScheme.NONE:
        return

    scaling_exclusion_list = [
        ctenums.EnemyID.NU, ctenums.EnemyID.NU_2,
        ctenums.EnemyID.UNKNOWN_BF,  # Weird Motherbrain object
        ctenums.EnemyID.UNUSED_FF,  # Placeholder enemy
    ]

    if not scaling_opts.dynamic_scaling_general_options.dynamic_scale_lavos:
        scaling_exclusion_list += [
            ctenums.EnemyID.LAVOS_2_LEFT, ctenums.EnemyID.LAVOS_2_RIGHT,
            ctenums.EnemyID.LAVOS_2_HEAD,
            ctenums.EnemyID.LAVOS_3_CORE, ctenums.EnemyID.LAVOS_3_LEFT,
            ctenums.EnemyID.LAVOS_3_RIGHT,
            ctenums.EnemyID.LAVOS_1,
        ]

    if not isinstance(scaling_opts.dynamic_scaling_scheme_options,
                      arguments.enemyscaling.ProgressionScalingData):
        raise TypeError

    patchscaling.apply_full_scaling_patch(
        ct_rom=ct_rom,
        scaling_general_options=settings.scaling_options.dynamic_scaling_general_options,
        scaling_scheme_type=settings.scaling_options.dynamic_scaling_scheme,
        scaling_scheme_options=settings.scaling_options.dynamic_scaling_scheme_options,
        region_scaling_options=settings.scaling_options.region_scaling_options,
        script_manager=script_manager,
        region_map=region_map,
        treasure_assignment=treasure_assignment,
        recruit_assignment=recruit_assignment,
        starting_rewards=settings.logic_options.starter_rewards,
        enemy_stat_dict=enemy_data_dict,
        boss_scaling_settings=settings.boss_scaling_options.boss_level_dict,
    )


def list_keys(key_type: arguments.KeyListType):
    enum_keys: list[enum.Enum] = []

    if key_type == arguments.KeyListType.ITEMS:
        enum_keys = list(ctenums.ItemID)
    elif key_type == arguments.KeyListType.TREASURE_SPOTS:
        enum_keys = list(ctenums.TreasureID)
    elif key_type == arguments.KeyListType.BOSS_SPOTS:
        enum_keys = [
            key for key in list(bosstypes.BossSpotID)
            if key not in [
                bosstypes.BossSpotID.GENO_DOME_MID,
                bosstypes.BossSpotID.OZZIES_FORT_SUPER_SLASH,
                bosstypes.BossSpotID.OZZIES_FORT_FLEA_PLUS
            ]
        ]
    elif key_type == arguments.KeyListType.BOSSES:
        enum_keys = [
            key for key in list(bosstypes.BossID)
            if key not in [
                bosstypes.BossID.KRAWLIE,
                bosstypes.BossID.LAVOS_CORE,
                bosstypes.BossID.INNER_LAVOS,
                bosstypes.BossID.LAVOS_SHELL,
                bosstypes.BossID.ATROPOS_XR,
                bosstypes.BossID.FLEA_PLUS,
                bosstypes.BossID.SUPER_SLASH,
                bosstypes.BossID.MAGUS_NORTH_CAPE,
                bosstypes.BossID.BLACK_TYRANO,
                bosstypes.BossID.MAMMON_M,
                bosstypes.BossID.MAGUS,
                bosstypes.BossID.ZEAL,
                bosstypes.BossID.ZEAL_2,
            ]
        ]

    for enum_key in enum_keys:
        print(enum_key.name.lower())


def extract_settings(*in_args: str) -> arguments.Settings:
    """
    Read arguments to generate a settings object.
    """

    parser = arguments.get_parser()
    args = parser.parse_args(in_args)
    if hasattr(args, "preset"):
        preset: arguments.Presets = getattr(args, "preset")
        preset_data = arguments.get_preset(preset)
    else:
        preset_data: dict[str, typing.Any] = {}

    if hasattr(args, "options_file"):
        options_path = getattr(args, "options_file")
        with open(options_path, 'rb') as infile:
            options_data = tomllib.load(infile)

    else:
        options_data: dict[str, typing.Any] = {}

    preset_data.update(options_data)

    additional_args = tomloptions.toml_data_to_args(preset_data, args)
    args = parser.parse_args(list(in_args) + additional_args)

    settings = arguments.Settings.extract_from_namespace(args)
    return settings


def get_random_config(
        settings: arguments.Settings,
        input_rom: ctrom.CTRom,
        rng: typing.Optional[RNGType] = None
) -> randostate.ConfigState:
    """
    Test: Try to do everyting EXCEPT rom changes (incl. scripts).  Then combine all rom changes.
    """

    config = randostate.ConfigState.get_default_config_from_ctrom(input_rom)

    if rng is None:
        # noinspection PyTypeChecker
        rng: RNGType = random.Random()
        rng.seed(settings.general_options.seed, version=2)

    if settings.character_options.use_phys_marle:
        charactermods.make_phys_marle(config.pcstat_manager, config.pctech_manager)
    if settings.character_options.use_haste_all:
        charactermods.make_haste_all(config.pctech_manager)
    if settings.character_options.use_phys_lucca:
        charactermods.make_phys_lucca(config.pcstat_manager, config.pctech_manager)
    if settings.character_options.use_protect_all:
        charactermods.make_prot_all(config.pctech_manager)
    if settings.character_options.use_reraise:
        charactermods.make_reraise(config.pctech_manager)
    if settings.character_options.use_magus_dual_techs:
        charactermods.add_magus_duals(config.pctech_manager)
    if settings.character_options.use_daltonized_magus:
        charactermods.add_daltonized_magus_techs(config.pctech_manager)
        staticbossscaling.modify_poison_immunity(config.enemy_data_dict)

    ### Techs
    pctechrandomizer.modify_all_single_tech_powers(
        config.pctech_manager, settings.tech_options, rng
    )

    techdescriptions.update_all_tech_descs(config.pctech_manager,
                                           settings.tech_options.black_hole_factor,
                                           settings.tech_options.black_hole_min)
    permutation_dict = pctechrandomizer.randomize_tech_order(
        config.pctech_manager,
        settings.tech_options.tech_order,
        settings.tech_options.preserve_magic,
        rng
    )

    ### Shops
    shoprando.apply_shop_settings(config.item_db, config.shop_manager,
                                  settings.shop_options,
                                  settings.gear_rando_options.ds_item_pool,
                                  rng)

    ### Recruits
    config.recruit_dict = recruitwriter.get_random_recruit_assignment_dict(
        settings.plando_options.recruit_assignment, rng)

    ### Boss/Midboss
    config.boss_assignment_dict = bossrando.get_random_boss_assignment(settings.boss_rando_options, rng)
    midboss_assignment = bossrando.get_random_midboss_assignment(settings.boss_rando_options, rng)
    config.boss_assignment_dict.update(midboss_assignment)
    bossrando.resolve_character_conflicts(config.boss_assignment_dict,
                                          config.recruit_dict,
                                          settings.boss_rando_options,
                                          rng)

    ### Objectives
    # After bosses to avoid double dipping.
    # Before map to allow objectives in logic
    config.objectives = objectivewriter.get_random_objectives_from_settings(
        settings.objective_options,
        config.boss_assignment_dict,
        rng
    )

    ### Enemy Charm/Drop
    rewardrando.apply_reward_rando(settings.battle_rewards, config.enemy_data_dict, rng)

    ### Enemy Reshuffle
    config.enemy_assign_dict = enemyrando.get_enemy_shuffle(settings.enemy_options.shuffle_enemies, rng)

    ### XP modifications depending on enemy type
    # Reduce the xp values so that we don't get so close to 0xFFFF
    rewardrando.pre_reduce_xp_thresholds(config.enemy_data_dict,
                                         config.pcstat_manager.xp_thresholds)

    # This needs to be BEFORE adaptive scale, which changes xp requirements
    if settings.battle_rewards.xp_tp_rewards.normalize_boss_xp:
        rewardrando.normalize_boss_xp(
            config.enemy_data_dict,
            settings.boss_scaling_options.boss_level_dict,
            config.pcstat_manager.xp_thresholds
        )

    rewardrando.modify_boss_midboss_xp_tp(
        config.enemy_data_dict,
        settings.battle_rewards.xp_tp_rewards.midboss_reward_factor,
        settings.battle_rewards.xp_tp_rewards.boss_xp_factor,
        settings.battle_rewards.xp_tp_rewards.boss_tp_factor
    )

    ### XP/TP Mod
    characterwriter.adaptive_scale_xp(
        config.pcstat_manager,
        settings.battle_rewards.xp_tp_rewards.xp_scale,
        settings.battle_rewards.xp_tp_rewards.xp_penalty_level,
        settings.battle_rewards.xp_tp_rewards.xp_penalty_percent,
        settings.battle_rewards.xp_tp_rewards.level_cap
    )
    characterwriter.scale_tp(
        config.pcstat_manager, settings.battle_rewards.xp_tp_rewards.tp_scale)

    ### Logic (KI Fill, Entrances)
    entrancefiller.update_starting_rewards(settings.logic_options.starter_rewards,
                                           settings.entrance_options)
    config.starting_rewards = list(settings.logic_options.starter_rewards)
    for reward in settings.logic_options.out_of_logic_starter_rewards:
        if isinstance(reward, ctenums.ItemID):
            config.starting_rewards.append(reward)
        elif reward not in config.starting_rewards:
            config.starting_rewards.append(reward)

    treasure_assignment, entrance_assignment, region_map = entrancefiller.get_key_item_fill(
        dict(),
        config.boss_assignment_dict,
        config.recruit_dict,
        settings.logic_options,
        settings.entrance_options,
        rng
    )

    objectivelogic.add_objectives_to_map(config.objectives, config.boss_assignment_dict,
                                         settings.objective_options, region_map)


    config.ow_exit_assignment_dict = entrance_assignment
    config.region_map = region_map
    # for key, val in entrance_assignment.items():
    #     print(key, val)
    # input()

    ### Treasure Fill
    exclude_pool = [
        x for x in settings.logic_options.starter_rewards
        if isinstance(x, ctenums.ItemID)
    ]
    if settings.gear_rando_options.bronze_fist_policy == gearrandooptions.BronzeFistPolicy.REMOVE:
        exclude_pool += ctenums.ItemID.BRONZEFIST

    config.treasure_assignment = treasureassign.default_assignment(
        treasure_assignment,
        settings.treasure_options,
        settings.gear_rando_options.ds_item_pool,
        exclude_pool,
        config.region_map,
        config.recruit_dict,
        settings.logic_options.starter_rewards,
        rng)

    ### Gear Rando
    gearrando.randomize_good_accessory_effects(
        config.item_db, settings.gear_rando_options, rng)
    gearrando.randomize_gear(config.item_db, settings.gear_rando_options, rng)
    config.item_db.update_all_descriptions()

    return config


def clean_scripts_for_tf(
        script_man: randostate.ScriptManager
):
    bad_locs = (
        ctenums.LocID.LOAD_SCREEN,
        ctenums.LocID.SPEKKIO,
        ctenums.LocID.FROGS_BURROW,
        ctenums.LocID.PRISON_SUPERVISORS_OFFICE, ctenums.LocID.PRISON_TORTURE_STORAGE_ROOM,
        ctenums.LocID.LEENE_SQUARE,
        ctenums.LocID.NORTH_CAPE,
        ctenums.LocID.DEATH_PEAK_SUMMIT_AFTER,
        ctenums.LocID.DACTYL_NEST_SUMMIT,
        ctenums.LocID.MANORIA_SANCTUARY,
        ctenums.LocID.PROTO_DOME,
        ctenums.LocID.QUEENS_ROOM_600
    )

    for loc in bad_locs:
        script = script_man[loc]
        while True:
            pos, _ = script.find_command_opt(
                [0xFC, 0xFD]
            )
            if pos is None:
                break

            script.delete_commands(pos, 1)


def get_ctrom_from_config(
        input_rom: ctrom.CTRom,
        settings: arguments.Settings,
        config: randostate.ConfigState,
        post_config_load_path: pathlib.Path | None = None,
        prepatched_rom_load_path: pathlib.Path | None = None,
        make_tf_friendly: bool = False
) -> ctrom.CTRom:
    """Generate the rom specified by the settings and config"""

    # There is some division between generating the post-config state and actually
    # writing the rom, but it's hard to separate.  Will do if there's need.

    ct_rom = ctrom.CTRom(input_rom.getbuffer())
    print("Applying Base Patch...", end="")
    a=time.time()
    if prepatched_rom_load_path is not None:
        try:
            infile = open(prepatched_rom_load_path, "rb")
            ct_rom = pickle.load(infile)
        except (OSError, pickle.PickleError):
            apply_settings_free_patches(ct_rom)
        finally:
            infile.close()
    else:
        apply_settings_free_patches(ct_rom)

    b=time.time()
    print(f"({b-a})")
    basepatch.add_set_level_command(ct_rom, config.pcstat_manager)
    if settings.tech_options.show_full_tech_list:
        techmenu.show_all_techs_in_menu(ct_rom)
        techmenu.write_cumulative_tp_in_menu(ct_rom)
    effecttypes.write_bh_percent(ct_rom, config.pctech_manager,
                                 settings.tech_options.black_hole_min,
                                 settings.tech_options.black_hole_factor
    )
    effecttypes.expand_effect_mods(
        ct_rom, config.pctech_manager
    )
    animationscript.write_scripts_to_ct_rom(ct_rom)
    scriptreassign.write_magus_animation_scripts(config.pctech_manager, ct_rom)


    print("Applying Openworld Scripts...", end="")
    a = time.time()
    post_config = get_openworld_post_config(ct_rom, post_config_load_path)
    encounters.apply_all_encounter_mods(post_config.script_manager)
    b = time.time()
    print(f"({b-a})")

    print("Setting Random Data...", end="")
    a = time.time()

    randofixes.fix_movement_locks(post_config.enemy_ai_manager)
    # Slash AI
    for tech_id in range(1, 9):
        if config.pctech_manager.get_tech(tech_id).name == "Slash":
            randofixes.fix_dino_slash_scripts(post_config.enemy_ai_manager, tech_id)
            break
    else:
        raise IndexError
    randofixes.add_dream_devourer_ai(post_config.enemy_ai_manager)
    ct_rom.seek(0x24F023 +0xCD*5 + 2)  # "Kid" palette for cutscene Schala
    ct_rom.write(b'\x36')

    modifymaps.make_heckran_boss_map(post_config.script_manager,
                                     post_config.loc_exit_dict,
                                     post_config.loc_data_dict)
    modifymaps.make_zenan_boss_map(post_config.script_manager,
                                   post_config.loc_exit_dict,
                                   post_config.loc_data_dict)
    modifymaps.make_dream_devourer_map(post_config.script_manager,
                                       post_config.loc_exit_dict,
                                       post_config.loc_data_dict)

    enemyrando.apply_enemy_shuffle(
        config.enemy_assign_dict, post_config.script_manager, post_config.enemy_sprite_dict
    )
    enemyrando.fix_npc_graphics(ct_rom, config.enemy_assign_dict,
                                post_config.enemy_sprite_dict)
    enemyrando.nerf_phys_immune(config.enemy_data_dict)

    apply_dynamic_scaling(ct_rom,
                          post_config.script_manager,
                          config.enemy_data_dict,
                          config.region_map,
                          config.treasure_assignment,
                          config.recruit_dict,
                          settings)

    bossrando.fix_boss_sprites_given_assignment(config.boss_assignment_dict,
                                                post_config.enemy_sprite_dict)
    bossrando.update_boss_names(config.boss_assignment_dict,
                                post_config.script_manager,
                                config.enemy_data_dict,
                                post_config.overworld_manager)
    bossrando.fix_atropos_ribbon_buff(config.boss_assignment_dict,
                                      post_config.script_manager)
    bossrando.bass.add_r_series_boss_defeat_check(config.boss_assignment_dict,
                                                  post_config.script_manager)

    xptpmod.apply_xptp_mods(
        ct_rom,
        settings.battle_rewards.xp_tp_rewards.split_xp,
        settings.battle_rewards.xp_tp_rewards.split_tp,
        settings.battle_rewards.xp_tp_rewards.fix_tp_doubling
    )

    staticbossscaling.scale_boss_hp(
        config.enemy_data_dict, post_config.enemy_ai_manager,
        settings.scaling_options.static_scaling_options.static_boss_hp_scale,
        settings.scaling_options.static_scaling_options.static_hp_scale_lavos
    )
    staticbossscaling.set_element_safety_level(post_config.enemy_ai_manager,
                                               settings.scaling_options.static_scaling_options.element_safety_level)

    enemystats.set_enemy_sightscope_settings(
        ct_rom, config.enemy_data_dict,
        settings.enemy_options.sightscope_all,
        settings.enemy_options.forced_sightscope
    )

    objectivewriter.write_test_objectives(post_config.script_manager,
                                          config.boss_assignment_dict,
                                          config.item_db,
                                          settings.objective_options, config.objectives)
    objectivewriter.write_quest_counters(post_config.script_manager)
    gearrando.normalize_ayla_fist(ct_rom)
    entranceassign.apply_entrance_rando(
        settings.entrance_options,
        post_config.overworld_manager,
        post_config.script_manager,
        config.ow_exit_assignment_dict,
        post_config.loc_exit_dict
    )

    ### Replace rstate.update_ct_rom()
    start = chesttext.write_desc_strings(ct_rom, config.item_db)
    chesttext.update_desc_str_start(ct_rom, start)
    chesttext.ugly_hack_chest_str(ct_rom)
    config.item_db.write_to_ctrom(ct_rom)

    for tid, treasure in post_config.treasure_data_dict.items():
        assigned_treasure = config.treasure_assignment[tid]
        # if assigned_treasure == ctenums.ItemID.NONE:
        #     assigned_treasure = ctenums.ItemID.MOP

        # TODO: Do progressive items more gracefully...
        if assigned_treasure == ctenums.ItemID.PENDANT_CHARGE:
            assigned_treasure = ctenums.ItemID.PENDANT
        if assigned_treasure == ctenums.ItemID.MASAMUNE_2:
            assigned_treasure = ctenums.ItemID.MASAMUNE_1
        if assigned_treasure == ctenums.ItemID.PRISMSHARD:
            assigned_treasure = ctenums.ItemID.RAINBOW_SHELL
        if assigned_treasure == ctenums.ItemID.CLONE:
            assigned_treasure = ctenums.ItemID.C_TRIGGER

        treasure.reward = assigned_treasure

    treasureassign.update_trading_post_strings(
        config.treasure_assignment, post_config.script_manager,
        config.item_db
    )
    treasureassign.update_trading_post_costs(
        settings.treasure_options.trading_post_base_cost,
        settings.treasure_options.trading_post_upgrade_cost,
        settings.treasure_options.trading_post_special_cost,
        post_config.script_manager
    )
    treasureassign.write_johnny_rewards(
        post_config.script_manager,
        settings.treasure_options
    )
    randostate.write_initial_rewards(config.starting_rewards, post_config.script_manager)

    recruitwriter.write_recruits_to_ct_rom(
        config.recruit_dict, post_config.script_manager, settings
    )
    bossrando.write_bosses_to_ct_rom(config.boss_assignment_dict,
                                     post_config.script_manager)

    config.pcstat_manager.write_to_ct_rom(ct_rom)
    config.pctech_manager.write_to_ctrom(ct_rom,
                                         settings.tech_options.black_hole_factor,
                                         settings.tech_options.black_hole_min)

    for enemy_id, enemy_stats in config.enemy_data_dict.items():
        enemy_stats.write_to_ctrom(ct_rom, enemy_id)

    config.shop_manager.write_to_ctrom(ct_rom)

    ### Logic Tweaks
    logictweaks.apply_logic_tweaks(settings.logic_options, post_config.script_manager)
    b=time.time()
    print(f"({b-a})")

    print("Writing Post-Randomization Personalizations...", end="")
    a = time.time()
    postrandowriter.write_post_rando_options(settings.post_random_options, post_config.script_manager,
                                             post_config.overworld_manager)
    b = time.time()
    print(f"({b-a})")

    if make_tf_friendly:
        clean_scripts_for_tf(post_config.script_manager)

    print("Writing to Rom...", end="")
    a = time.time()
    post_config.write_to_ctrom(ct_rom)
    b = time.time()
    print(f"({b-a})")
    ### End replace rstate.update_ct_rom()
    return ct_rom


def write_rjust_dict(
            in_dict: dict,
            heading: str | None,
            outfile: TextIO,
            padding: int = 0
    ):
        max_spot = max(in_dict.keys(), key=lambda x: len(str(x)))
        max_len = len(str(max_spot))

        if heading is not None:
            outfile.write(heading+"\n")
            outfile.write("-"*len(heading) + "\n")

        for key, val in in_dict.items():
            outfile.write(f"{str(key).rjust(max_len+padding)}: {str(val)}\n")


def write_treasure_spoilers(
        treasure_str_dict: dict[ctenums.TreasureID, str],
        outfile: TextIO
):

    regions = locregions.get_all_loc_regions()
    for region in regions:
        treasure_ids = [x for x in region.reward_spots if isinstance(x, ctenums.TreasureID)]
        if treasure_ids:
            region_name = " ".join(x.capitalize() for x in region.name.split("_"))
            outfile.write(region_name + ":\n")
            region_dict = {x: treasure_str_dict[x] for x in treasure_ids}
            write_rjust_dict(region_dict, None, outfile, padding=4)
            outfile.write("\n")


def write_character_spoilers(
        config: randostate.ConfigState,
        outfile: TextIO
):
    for char_id in ctenums.CharID:
        outfile.write(char_id.name.capitalize() +":\n")
        tech_start = 1+char_id*8
        tech_dict: dict[str, str] = {}
        for ind in range(tech_start, tech_start+8):
            tech = config.pctech_manager.get_tech(ind)
            tech_dict[tech.name] = f"{tech.effect_mps[0]} MP".rjust(6) + f"    {tech.desc[:-6]}"

        write_rjust_dict(tech_dict, None, outfile, 4)
        outfile.write("\n")


def write_spoilers_to_file(
        settings: arguments.Settings,
        config: randostate.ConfigState,
        outfile: TextIO
):
        recruit_spoiler_dict: dict[typing.Any, str] = {}
        for key, val in config.recruit_dict.items():
            if not val:
                out_str = "None"
            else:
                out_str = ", ".join(str(x) for x in val)
            recruit_spoiler_dict[key] = out_str

        write_rjust_dict(recruit_spoiler_dict, "Recruit Spots", outfile)
        outfile.write("\n")

        outfile.write("Tech Lists\n")
        outfile.write("----------\n")
        write_character_spoilers(config, outfile)

        key_items = (
                entrancefiller.get_forced_key_items() +
                settings.logic_options.additional_key_items
        )

        treasure_str_dict: dict[ctenums.TreasureID, str] = {}
        ki_spots: list[ctenums.TreasureID] = []
        for spot, reward in config.treasure_assignment.items():
            if reward in key_items:
                ki_spots.append(spot)

            if isinstance(reward, ctenums.ItemID):
                reward_name = config.item_db[reward].name
                reward_str = str(ctstrings.CTNameString(reward_name[1:]))
            else:
                reward_str = f"{reward} G"
            treasure_str_dict[spot] = reward_str

        obj_dict: dict[str, str] = dict()
        for ind, item_id in enumerate((
            ctenums.ItemID.OBJECTIVE_1, ctenums.ItemID.OBJECTIVE_2,
            ctenums.ItemID.OBJECTIVE_3, ctenums.ItemID.OBJECTIVE_4,
            ctenums.ItemID.OBJECTIVE_5, ctenums.ItemID.OBJECTIVE_6,
            ctenums.ItemID.OBJECTIVE_7, ctenums.ItemID.OBJECTIVE_8,
        )):
            name = f"Objective {ind+1}"
            desc = config.item_db[item_id].get_desc_as_str()
            obj_dict[name] = desc

        write_rjust_dict(obj_dict, "Objectives", outfile)

        ki_dict = {key: treasure_str_dict[key] for key in ki_spots}
        write_rjust_dict(ki_dict, "Key Items", outfile)
        outfile.write("\n")

        outfile.write("Full Treasure Assignment\n")
        outfile.write("------------------------\n\n")
        write_treasure_spoilers(treasure_str_dict, outfile)
        outfile.write("\n")

        # write_rjust_dict(treasure_str_dict, "Full Treasure Assignment", outfile)

        def make_printable(in_str: str) -> str:
            parts = in_str.split("_")
            return " ".join(x.capitalize() for x in parts)


        write_rjust_dict(config.boss_assignment_dict, "Bosses", outfile)
        if settings.entrance_options.shuffle_entrances:

            printable_entrance_dict: dict[str, str] = {
                make_printable(key.name): make_printable(val.name)
                for key, val in  config.ow_exit_assignment_dict.items()
            }
            write_rjust_dict(printable_entrance_dict, "Entrance Assignment", outfile)
        # get_proof(
        #     config.ow_exit_assignment_dict,
        #     config.recruit_dict,
        #     config.treasure_assignment,
        #     key_items,
        #     config.starting_rewards,
        # )


def write_spoilers(
        settings: arguments.Settings,
        config: randostate.ConfigState,
        path: pathlib.Path
):

    with open(path, "w") as outfile:
        write_spoilers_to_file(settings, config, outfile)


def get_proof(
        entrance_assignment: dict[regionmap.OWExit, regionmap.OWExit],
        recruit_assignment: dict[ctenums.RecruitID, ctenums.CharID | None],
        treasure_assignment: dict[ctenums.TreasureID, logictypes.RewardType],
        key_items: list[ctenums.ItemID],
        starting_rewards: list[logictypes.RewardType],
        starting_region: str = "starting_rewards"
) -> str:
    region_map = regionmap.get_map_from_assignment(recruit_assignment, entrance_assignment)
    region_map.loc_region_dict[starting_region].region_rewards = list(starting_rewards)

    traverser = maptraversal.MapTraverser(region_map, starting_region, starting_rewards)

    ret_str = "Proof:"
    ret_str += "------"

    regions = set(traverser.reached_regions)
    sphere = 0

    return ret_str


def main():
    """Do the randomization."""
    # import builtins
    # def f(*args, **kwargs):
    #     raise ValueError
    # builtins.print = f

    print("Getting Settings...", end = "")
    a = time.time()
    try:
        settings = extract_settings(*sys.argv[1:])
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(-2)

    x = settings.get_argument_spec()

    list_type = settings.general_options.list_keys

    if list_type is not None:
        list_keys(list_type)
        sys.exit()
    b = time.time()

    # Do generation
    if settings.general_options.input_file is None:
        raise ValueError("No input rom specified")
    if settings.general_options.output_directory is None:
        # Validation is done in the GeneralOptions object, but maybe it
        # should be here instead.
        settings.general_options.output_directory = \
            settings.general_options.input_file.parent

    ct_rom = ctrom.CTRom.from_file(str(settings.general_options.input_file))
    print(f"({b - a})")

    print("Getting Random Data...", end="")
    a = time.time()
    config = get_random_config(settings, ct_rom)
    b = time.time()
    print(f"({b-a})")

    # import time
    # x = time.time()
    out_rom = get_ctrom_from_config(ct_rom, settings, config, make_tf_friendly=False)
    # y = time.time()
    # print(y-x)


    output_path = settings.general_options.output_directory / "ct-mod.sfc"
    output_path.write_bytes(out_rom.getbuffer())

    spoiler_path = settings.general_options.output_directory / "ct-mod-spoilers.txt"
    write_spoilers(settings, config, spoiler_path)


def get_openworld_post_config(
        cur_ct_rom: ctrom.CTRom,
        load_path: pathlib.Path | None = None,
) -> randostate.PostConfigState:

    if load_path is not None:
        with open(load_path, "rb") as infile:
            post_config: randostate.PostConfigState = pickle.load(infile)

        if not isinstance(post_config, randostate.PostConfigState):
            raise TypeError

        post_config.script_manager.set_ctrom(cur_ct_rom)
        post_config.overworld_manager.set_ct_rom(cur_ct_rom)
        return post_config

    post_config = randostate.PostConfigState.get_default_state_from_ctrom(cur_ct_rom)

    lavos_sprite = post_config.enemy_sprite_dict[ctenums.EnemyID.LAVOS_1].get_copy()
    post_config.enemy_sprite_dict[ctenums.EnemyID.DREAM_DEVOURER] = lavos_sprite
    # 26 1B 9F 3B 00
    schala_sprite = post_config.enemy_sprite_dict[ctenums.EnemyID.SCHALA]
    schala_sprite.packet_id = 0x26
    schala_sprite.sprite_assembly_id = 0x1B
    schala_sprite.palette = 0x80 # 0x36 # 0x80
    schala_sprite.animation_id = 0x3B
    schala_sprite.sprite_size = 0x00

    basepatch.apply_openworld.apply_openworld(post_config.script_manager)
    basepatch.apply_openworld_ow.update_all_overworlds(post_config.overworld_manager)

    # Location Data
    post_config.loc_data_dict[ctenums.LocID.GUARDIA_BASEMENT].music = 0xFF
    post_config.loc_data_dict[ctenums.LocID.GUARDIA_REAR_STORAGE].music = 0xFF

    # Location Exits
    exit_dict = post_config.loc_exit_dict
    del exit_dict[ctenums.LocID.LAB_32_EAST][1]
    exit_dict[ctenums.LocID.BLACK_OMEN_98F_OMEGA_DEFENSE][1].exit_y -= 1

    return post_config


def dump_openworld_post_config(
        vanilla_rom: ctrom.CTRom,
        dump_path: pathlib.Path
):
    post_config = get_openworld_post_config(vanilla_rom)

    with open(dump_path, "wb") as outfile:
        # noinspection PyTypeChecker
        pickle.dump(post_config, outfile)


def apply_settings_free_patches(vanilla_rom: ctrom.CTRom):
    """
    Apply patches which do not depend on settings and dump the CTRom.
    """
    basepatch.base_patch_ct_rom(vanilla_rom)
    basepatch.apply_ow_warp_patch(vanilla_rom)


def dump_prepatched_ctrom(
        vanilla_rom: ctrom.CTRom,
        dump_path: pathlib.Path
):
    """
    Dump a settings-free patched rom
    """
    copy_rom = copy.deepcopy(vanilla_rom)
    apply_settings_free_patches(copy_rom)

    with open(dump_path, "wb") as outfile:
        pickle.dump(copy_rom, outfile)


if __name__ == "__main__":
    main()
