"""Module for randomizing enemy drop/charm rewards"""
from collections.abc import Sequence

from ctrando.arguments import battlerewards, gearrandooptions
from ctrando.bosses import bosstypes as bty
from ctrando.characters import ctpcstats
from ctrando.common import ctenums, distribution
from ctrando.common.random import RNGType
from ctrando.enemydata import enemystats
from ctrando.enemyscaling.patchscaling import get_true_levels_bytes


_restricted_enemies = frozenset((
    ctenums.EnemyID.UNKNOWN_3C, ctenums.EnemyID.UNKNOWN_44,
    ctenums.EnemyID.UNKNOWN_5A, ctenums.EnemyID.MAGUS_NO_NAME,
    ctenums.EnemyID.UNUSED_FD, ctenums.EnemyID.UNUSED_FE,
    ctenums.EnemyID.SCHALA, ctenums.EnemyID.UNUSED_FD,
    ctenums.EnemyID.UNUSED_FE, ctenums.EnemyID.UNUSED_FF)
)

_restricted_items = frozenset([
    ctenums.ItemID.NONE, ctenums.ItemID.SCALING_LEVEL, ctenums.ItemID.OBJECTIVE_1,
    ctenums.ItemID.OBJECTIVE_2, ctenums.ItemID.OBJECTIVE_3, ctenums.ItemID.OBJECTIVE_4,
    ctenums.ItemID.OBJECTIVE_5, ctenums.ItemID.OBJECTIVE_6, ctenums.ItemID.OBJECTIVE_7,
    ctenums.ItemID.OBJECTIVE_7, ctenums.ItemID.OBJECTIVE_8, ctenums.ItemID.MASAMUNE_1,
    ctenums.ItemID.MASAMUNE_2, ctenums.ItemID.FIST, ctenums.ItemID.FIST_2,
    ctenums.ItemID.FIST_3, ctenums.ItemID.IRON_FIST, ctenums.ItemID.BRONZEFIST,
    ctenums.ItemID.PACIFIST, ctenums.ItemID.APITEM,
    ctenums.ItemID.BENT_HILT, ctenums.ItemID.BENT_SWORD,
    ctenums.ItemID.MASAMUNE_0_ATK,
    ctenums.ItemID.UNUSED_56, ctenums.ItemID.UNUSED_57, ctenums.ItemID.UNUSED_58,
    ctenums.ItemID.UNUSED_59, ctenums.ItemID.WEAPON_END_5A, ctenums.ItemID.ARMOR_END_7B,
    ctenums.ItemID.HELM_END_94, # Rocks?
    ctenums.ItemID.HERO_MEDAL,
    ctenums.ItemID.ACCESSORY_END_BC,
    ctenums.ItemID.SEED,
    ctenums.ItemID.BIKE_KEY, ctenums.ItemID.PENDANT, ctenums.ItemID.GATE_KEY,
    ctenums.ItemID.PRISMSHARD, ctenums.ItemID.C_TRIGGER, ctenums.ItemID.TOOLS,
    ctenums.ItemID.JERKY, ctenums.ItemID.DREAMSTONE, ctenums.ItemID.RACE_LOG,
    ctenums.ItemID.MOON_STONE, ctenums.ItemID.SUN_STONE, ctenums.ItemID.RUBY_KNIFE,
    ctenums.ItemID.YAKRA_KEY, ctenums.ItemID.CLONE, ctenums.ItemID.TOMAS_POP,
    ctenums.ItemID.BUCKETFRAG, ctenums.ItemID.JETSOFTIME, ctenums.ItemID.PENDANT_CHARGE,
    ctenums.ItemID.RAINBOW_SHELL, ctenums.ItemID.UNUSED_EC, ctenums.ItemID.UNUSED_ED,
    ctenums.ItemID.UNUSED_EE, ctenums.ItemID.UNUSED_EF, ctenums.ItemID.UNUSED_F0,
    ctenums.ItemID.UNUSED_F1,]
)

_non_lavos_boss_ids = tuple(
    x for x in bty.BossID if x not in set(bty.get_lavos_bosses())
)


_pool_dict: dict[battlerewards.EnemyPoolType, Sequence[ctenums.EnemyID]] = {
    battlerewards.EnemyPoolType.ALL: tuple(x for x in ctenums.EnemyID if x not in _restricted_enemies),
    battlerewards.EnemyPoolType.MIDBOSSES: (
        ctenums.EnemyID.ATROPOS_XR, ctenums.EnemyID.GATO, ctenums.EnemyID.SUPER_SLASH,
        ctenums.EnemyID.FLEA_PLUS, ctenums.EnemyID.KRAWLIE, ctenums.EnemyID.DALTON
    ),
    battlerewards.EnemyPoolType.BOSSES: (
        tuple(bty.get_enemy_ids(bty.get_boss_ids()))
        + (ctenums.EnemyID.SPEKKIO_FROG, ctenums.EnemyID.SPEKKIO_FROG,
           ctenums.EnemyID.SPEKKIO_OGRE, ctenums.EnemyID.SPEKKIO_OMNICRONE,
           ctenums.EnemyID.SPEKKIO_MASA_MUNE, ctenums.EnemyID.SPEKKIO_NU)
    ),
    battlerewards.EnemyPoolType.BOSSES_NO_LAVOS: tuple(bty.get_enemy_ids(_non_lavos_boss_ids)),
    battlerewards.EnemyPoolType.NORMAL_ENEMIES: (
        ctenums.EnemyID.REPTITE_GREEN, ctenums.EnemyID.KILWALA, ctenums.EnemyID.HENCH_PURPLE,
        ctenums.EnemyID.OMICRONE, ctenums.EnemyID.BLUE_IMP, ctenums.EnemyID.GREEN_IMP,
        ctenums.EnemyID.STONE_IMP, ctenums.EnemyID.ROLY, ctenums.EnemyID.POLY,
        ctenums.EnemyID.ROLYPOLY, ctenums.EnemyID.ROLY_RIDER, ctenums.EnemyID.BLUE_EAGLET,
        ctenums.EnemyID.GOLD_EAGLET, ctenums.EnemyID.RED_EAGLET, ctenums.EnemyID.AVIAN_CHAOS,
        ctenums.EnemyID.IMP_ACE, ctenums.EnemyID.BANTAM_IMP, ctenums.EnemyID.GNASHER,
        ctenums.EnemyID.GNAWER, ctenums.EnemyID.NAGA_ETTE, ctenums.EnemyID.OCTOPOD,
        ctenums.EnemyID.OCTOBLUSH, ctenums.EnemyID.OCTOBINO, ctenums.EnemyID.DECEASED,
        ctenums.EnemyID.DECEDENT, ctenums.EnemyID.MACABRE, ctenums.EnemyID.GUARD,
        ctenums.EnemyID.FREE_LANCER, ctenums.EnemyID.OUTLAW, ctenums.EnemyID.JUGGLER,
        ctenums.EnemyID.MAGE, ctenums.EnemyID.FLY_TRAP, ctenums.EnemyID.MEAT_EATER,
        ctenums.EnemyID.MAN_EATER, ctenums.EnemyID.KRAKKER, ctenums.EnemyID.EGDER,
        ctenums.EnemyID.REPTITE_PURPLE, ctenums.EnemyID.BLUE_SHIELD, ctenums.EnemyID.YODU_DE,
        ctenums.EnemyID.INCOGNITO, ctenums.EnemyID.PEEPINGDOOM, ctenums.EnemyID.JINN_BOTTLE,
        ctenums.EnemyID.EVILWEEVIL, ctenums.EnemyID.TEMPURITE, ctenums.EnemyID.DIABLOS,
        ctenums.EnemyID.GARGOYLE, ctenums.EnemyID.GRIMALKIN, ctenums.EnemyID.HENCH_BLUE,
        ctenums.EnemyID.T_POLE, ctenums.EnemyID.CROAKER, ctenums.EnemyID.AMPHIBITE,
        ctenums.EnemyID.MAD_BAT, ctenums.EnemyID.VAMP, ctenums.EnemyID.SCOUTER,
        ctenums.EnemyID.FLYCLOPS, ctenums.EnemyID.BUGGER, ctenums.EnemyID.DEBUGGER,
        ctenums.EnemyID.SORCERER, ctenums.EnemyID.JINN, ctenums.EnemyID.BARGHEST,
        ctenums.EnemyID.CRATER, ctenums.EnemyID.VOLCANO, ctenums.EnemyID.SHITAKE,
        ctenums.EnemyID.HETAKE, ctenums.EnemyID.SHIST, ctenums.EnemyID.PAHOEHOE,
        ctenums.EnemyID.NEREID, ctenums.EnemyID.SAVE_POINT_ENEMY, ctenums.EnemyID.SHADOW,
        ctenums.EnemyID.ACID, ctenums.EnemyID.ALKALINE, ctenums.EnemyID.ION,
        ctenums.EnemyID.ANION, ctenums.EnemyID.THRASHER, ctenums.EnemyID.LASHER,
        ctenums.EnemyID.GOBLIN, ctenums.EnemyID.OGRE, ctenums.EnemyID.CAVE_BAT,
        ctenums.EnemyID.OGAN, ctenums.EnemyID.FLUNKY, ctenums.EnemyID.GROUPIE,
        ctenums.EnemyID.WINGED_APE, ctenums.EnemyID.CAVE_APE, ctenums.EnemyID.MEGASAUR,
        ctenums.EnemyID.BLUE_BEAST, ctenums.EnemyID.RED_BEAST, ctenums.EnemyID.AVIAN_REX,
        ctenums.EnemyID.RAT, ctenums.EnemyID.GREMLIN, ctenums.EnemyID.RUNNER,
        ctenums.EnemyID.PROTO_2, ctenums.EnemyID.PROTO_3, ctenums.EnemyID.BUG,
        ctenums.EnemyID.BEETLE, ctenums.EnemyID.RAIN_FROG, ctenums.EnemyID.BELLBIRD,
        ctenums.EnemyID.TERRASAUR, ctenums.EnemyID.MUTANT, ctenums.EnemyID.FAKE_FLEA,
        ctenums.EnemyID.OZZIE_MAGUS_CHAINS, ctenums.EnemyID.ROLY_BOMBER, ctenums.EnemyID.OCTORIDER,
        ctenums.EnemyID.BYTE, ctenums.EnemyID.RED_SCOUT, ctenums.EnemyID.BLUE_SCOUT,
        ctenums.EnemyID.BASHER
    ),
    battlerewards.EnemyPoolType.HARD_ENEMIES: (
        ctenums.EnemyID.OMNICRONE, ctenums.EnemyID.SENTRY, ctenums.EnemyID.REAPER,
        ctenums.EnemyID.DEFUNCT, ctenums.EnemyID.DEPARTED, ctenums.EnemyID.MOHAVOR,
        ctenums.EnemyID.HEXAPOD, ctenums.EnemyID.BLOB, ctenums.EnemyID.ALIEN,
        ctenums.EnemyID.BEAST, ctenums.EnemyID.LIZARDACTYL, ctenums.EnemyID.NU,
        ctenums.EnemyID.NU_2, ctenums.EnemyID.PROTO_4, ctenums.EnemyID.DEBUGGEST,
        ctenums.EnemyID.GOON, ctenums.EnemyID.PANEL, ctenums.EnemyID.RUMINATOR,
        ctenums.EnemyID.BASE, ctenums.EnemyID.MARTELLO, ctenums.EnemyID.METAL_MUTE,
        ctenums.EnemyID.CYBOT, ctenums.EnemyID.TUBSTER, ctenums.EnemyID.GIGASAUR,
        ctenums.EnemyID.LEAPER, ctenums.EnemyID.FOSSIL_APE,
        ctenums.EnemyID.OZZIE_FORT, ctenums.EnemyID.SYNCHRITE,
        ctenums.EnemyID.MASA, ctenums.EnemyID.MUNE, ctenums.EnemyID.OZZIE_ZENAN,
        ctenums.EnemyID.LASER_GUARD, ctenums.EnemyID.RUBBLE, ctenums.EnemyID.TURRET,
        ctenums.EnemyID.BOSS_ORB, ctenums.EnemyID.SIDE_KICK
    )
}


def get_pool_enemy_ids(pool_type: battlerewards.EnemyPoolType) -> Sequence[ctenums.EnemyID]:
    return list(_pool_dict[pool_type])


def mark_charm_and_drop(
        enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        mark_charm: bool,
        mark_drop: bool
):
    """Add a suffix to names of enemies with charm and/or drop."""
    for enemy_id, enemy_stats in enemy_dict.items():
        suffix = ""
        if mark_charm and enemy_stats.charm_item != ctenums.ItemID.NONE:
            suffix += "C"
        if mark_drop and enemy_stats.drop_item != ctenums.ItemID.NONE:
            suffix += "D"

        if suffix and "{null}" not in enemy_stats.name:
            cur_name = enemy_stats.name.ljust(0xB, " ")
            cur_name = cur_name[:-len(suffix)] + suffix
            enemy_stats.name = cur_name


def pre_reduce_xp_thresholds(
        enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        xp_thresholds: ctpcstats.XPThreshholds,
        base_scale_factor: int = 2.0
):
    """
    Reduce all xp thresholds and xp rewards by a factor to shrink
    the range of possible xp values.
    """

    for enemy_stats in enemy_dict.values():
        xp = enemy_stats.xp
        if xp == 0:
            continue
        # print(xp, end=", ")
        xp = sorted([1, round(xp/base_scale_factor), 0xFFFF])[1]
        enemy_stats.xp = xp
        # print(xp)

    input

    for level in range(99):
        xp_req = xp_thresholds.get_xp_for_level(level)
        xp_req = sorted([1, round(xp_req/base_scale_factor), 0xFFFF])[1]
        xp_thresholds.set_xp_for_level(level, xp_req)

def normalize_boss_xp(
        enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        true_levels_dict: dict[bty.BossID, int | None],
        xp_threholds: ctpcstats.XPThreshholds  # For xp thresholds
):
    true_levels_b = get_true_levels_bytes(enemy_dict, true_levels_dict)

    # Before starting, set Zeal's XP to any non-zero value so it isn't ignored.
    enemy_dict[ctenums.EnemyID.ZEAL].xp = 1

    boss_ids = bty.get_boss_ids()
    for boss_id in boss_ids:
        scheme = bty.get_default_scheme(boss_id)
        part_ids = [part.enemy_id for part in scheme.parts]
        total_xp = sum(enemy_dict[part_id].xp for part_id in part_ids)

        xp_share: dict[ctenums.EnemyID, int] = {}
        for part_id in part_ids:
            cur_share = xp_share.get(part_id, 0)
            cur_share += enemy_dict[part_id].xp
            xp_share[part_id] = cur_share

        # for part_id in set(part_ids):
        #     print(f"{part_id}: {enemy_dict[part_id].xp}")

        total_xp = sum(xp_share.values())
        if not total_xp:
            continue

        level = true_levels_dict.get(boss_id, None)
        if level is not None:
            target_xp = xp_threholds.get_xp_for_level(level)
        else:
            real_parts = [part_id for part_id, xp in xp_share.items()
                          if xp > 0]

            total_level = sum(true_levels_b[part] for part in real_parts)
            avg_level = round(total_level/len(real_parts))
            target_xp = xp_threholds.get_xp_for_level(avg_level)

        for part_id in set(part_ids):
            new_xp = round(enemy_dict[part_id].xp * target_xp/total_xp)
            new_xp = sorted([0, new_xp, 0xFFFF])[1]
            enemy_dict[part_id].xp = new_xp

        # for part_id in set(part_ids):
        #     print(f"{part_id}: {enemy_dict[part_id].xp}")
        # input()

def modify_boss_midboss_xp_tp(
        enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        midboss_factor: float,
        boss_xp_factor: float,
        boss_tp_factor: float,
):
    midbosses = bty.get_midboss_ids()

    for boss_id in bty.BossID:
        if boss_id in midbosses:
            xp_factor = midboss_factor
            tp_factor = midboss_factor
        else:
            xp_factor = boss_xp_factor
            tp_factor = boss_tp_factor

        scheme = bty.get_default_scheme(boss_id)
        parts = set(part.enemy_id for part in scheme.parts)

        for part in parts:
            new_xp = enemy_dict[part].xp*xp_factor
            new_xp = sorted([0, round(new_xp), 0xFFFF])[1]
            enemy_dict[part].xp = new_xp

            new_tp = enemy_dict[part].tp*tp_factor
            new_tp = sorted([0, round(new_tp), 0xFF])[1]
            enemy_dict[part].tp = new_tp


def apply_drop_charm_group(
        vanilla_enemy_dict: dict[ctenums.EnemyID, enemystats.StatList],
        current_enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        group: battlerewards.RewardGroup,
        allowed_ds_items: Sequence[gearrandooptions.DSItem],
        rng: RNGType
):
    enemy_pool_type = group.get_enemy_pool_type()
    reward_pool_type = group.get_reward_pool_type()
    attr_name = group.get_stat_attr_name()

    restricted_enemies = [
        ctenums.EnemyID.UNKNOWN_3C, ctenums.EnemyID.UNKNOWN_44,
        ctenums.EnemyID.UNKNOWN_5A, ctenums.EnemyID.MAGUS_NO_NAME,
        ctenums.EnemyID.UNUSED_FD, ctenums.EnemyID.UNUSED_FE,
        ctenums.EnemyID.SCHALA, ctenums.EnemyID.UNUSED_FD,
        ctenums.EnemyID.UNUSED_FE, ctenums.EnemyID.UNUSED_FF
    ]

    # For non-custom modes, the custom field is used to represent exclusions
    if enemy_pool_type == battlerewards.EnemyPoolType.CUSTOM:
       enemy_pool =  list(group.get_custom_enemy_pool())
    else:
       restrictions = set(group.get_custom_enemy_pool())
       if enemy_pool_type == battlerewards.EnemyPoolType.VANILLA:
           enemy_pool = [
               enemy_id for enemy_id, stats in vanilla_enemy_dict.items()
               if getattr(stats, attr_name) != ctenums.ItemID.NONE
           ]
       else:
           enemy_pool = get_pool_enemy_ids(enemy_pool_type)
       enemy_pool = [x for x in enemy_pool if x not in restrictions]


    if (
            reward_pool_type == battlerewards.RewardPoolType.VANILLA
            and not group.get_custom_reward_pool()
    ):
        return


    restricted_items: list[ctenums.ItemID] = []
    if gearrandooptions.DSItem.VALOR_CREST not in allowed_ds_items:
        restricted_items.append(ctenums.ItemID.VALOR_CREST)
    if gearrandooptions.DSItem.DRAGONS_TEAR not in allowed_ds_items:
        restricted_items.append(ctenums.ItemID.DRAGON_TEAR)

    if reward_pool_type in (battlerewards.RewardPoolType.VANILLA,
                            battlerewards.RewardPoolType.SHUFFLE):
        reward_dist = group.get_custom_reward_pool()
        if reward_dist is None:
            reward_pool = [
                getattr(vanilla_enemy_dict[enemy_id], attr_name)
                for enemy_id in enemy_pool
            ]
        else:
            reward_pool = reward_dist.get_all_items_multiplicity()

        num_nones = max(len(enemy_pool) - len(reward_pool), 0)
        none_pad = [ctenums.ItemID.NONE for _ in range(num_nones)]

        if reward_pool_type == battlerewards.RewardPoolType.VANILLA:
            reward_pool += none_pad
        if reward_pool_type == battlerewards.RewardPoolType.SHUFFLE:
            reward_pool += none_pad
            rng.shuffle(reward_pool)
    elif reward_pool_type == battlerewards.RewardPoolType.RANDOM:
        reward_dist = group.get_custom_reward_pool()
        if reward_dist is None:
            reward_dist = distribution.Distribution(
                (1,
                 [x for x in ctenums.ItemID
                  if x not in _restricted_items.union(restricted_items)]
                 )
            )

        reward_pool = [
            reward_dist.get_random_item(rng) for _ in enemy_pool
            if rng.random() < group.get_rate()
        ]
    else:
        raise ValueError(reward_pool_type)

    for enemy, reward in zip(enemy_pool, reward_pool):
        stats = current_enemy_dict[enemy]
        setattr(stats, attr_name, reward)


def apply_reward_rando(
        reward_options: battlerewards.BattleRewards,
        enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        allowed_ds_items: Sequence[gearrandooptions.DSItem],
        rng: RNGType
):

    vanilla_enemy_dict = dict(enemy_dict)
    for group in reward_options.drop_options.drop_groups:
        apply_drop_charm_group(vanilla_enemy_dict, enemy_dict, group, allowed_ds_items, rng)

    for group in reward_options.charm_options.charm_groups:
        apply_drop_charm_group(vanilla_enemy_dict, enemy_dict, group, allowed_ds_items, rng)

    mark_charm_and_drop(enemy_dict, reward_options.charm_options.mark_charmable_enemies,
                        reward_options.drop_options.mark_dropping_enemies)

    # for enemy_id, stats in enemy_dict.items():
    #     has_charm = stats.charm_item != ctenums.ItemID.NONE
    #     has_drop = stats.drop_item != ctenums.ItemID.NONE
    #
    #     if has_charm or has_drop:
    #         print(f"{stats.name}\t{stats.charm_item}\t{stats.drop_item}")
