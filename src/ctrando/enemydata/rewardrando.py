"""Module for randomizing enemy drop/charm rewards"""
from ctrando.arguments import battlerewards
from ctrando.bosses import bosstypes as bty
from ctrando.characters import ctpcstats
from ctrando.common import ctenums
from ctrando.common.random import RNGType
from ctrando.enemydata import enemystats
from ctrando.enemyscaling.patchscaling import get_true_levels_bytes


def get_enemy_pool(
        enemy_stat_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        options: battlerewards.DropOptions | battlerewards.CharmOptions,
        rng: RNGType
) -> list[ctenums.EnemyID]:
    """Determine the enemies which will have a dropped item."""

    if isinstance(options, battlerewards.DropOptions):
        keep_rate = options.drop_rate
        pool_type = options.drop_enemy_pool
        attr_name = "drop_item"
    elif isinstance(options, battlerewards.CharmOptions):
        keep_rate = options.charm_rate
        pool_type = options.charm_enemy_pool
        attr_name = "charm_item"
    else:
        raise TypeError

    enemy_pool: list[ctenums.EnemyID] = []
    # The only important one (I think) is to not put anything on 0xFF
    restricted_enemies = [
        ctenums.EnemyID.UNKNOWN_3C, ctenums.EnemyID.UNKNOWN_44,
        ctenums.EnemyID.UNKNOWN_5A, ctenums.EnemyID.MAGUS_NO_NAME,
        ctenums.EnemyID.UNUSED_FD, ctenums.EnemyID.UNUSED_FE,
        ctenums.EnemyID.SCHALA, ctenums.EnemyID.UNUSED_FD,
        ctenums.EnemyID.UNUSED_FE, ctenums.EnemyID.UNUSED_FF
    ]

    if pool_type == battlerewards.EnemyPoolType.VANILLA:
        enemy_pool = [
            enemy_id for enemy_id, stats in enemy_stat_dict.items()
            if getattr(stats, attr_name) != ctenums.ItemID.NONE
        ]
    elif pool_type == battlerewards.EnemyPoolType.ALL:
        enemy_pool = [enemy_id for enemy_id in ctenums.EnemyID
                      if enemy_id not in restricted_enemies]
    else:
        print(pool_type)
        raise ValueError

    enemy_pool = [enemy_id for enemy_id in enemy_pool if rng.random() < keep_rate]

    return enemy_pool


def assign_rewards(
        enemy_pool: list[ctenums.EnemyID],
        options: battlerewards.DropOptions | battlerewards.CharmOptions,
        enemy_stat_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        rng: RNGType
):

    if isinstance(options, battlerewards.DropOptions):
        keep_rate = options.drop_rate
        pool_type = options.drop_reward_pool
        attr_name = "drop_item"
    elif isinstance(options, battlerewards.CharmOptions):
        keep_rate = options.charm_rate
        pool_type = options.charm_reward_pool
        attr_name = "charm_item"
    else:
        raise TypeError

    if pool_type == battlerewards.RewardPoolType.VANILLA:
        return

    restricted_items = [
        ctenums.ItemID.NONE, ctenums.ItemID.SCALING_LEVEL, ctenums.ItemID.OBJECTIVE_1,
        ctenums.ItemID.OBJECTIVE_2, ctenums.ItemID.OBJECTIVE_3, ctenums.ItemID.OBJECTIVE_4,
        ctenums.ItemID.OBJECTIVE_5, ctenums.ItemID.OBJECTIVE_6, ctenums.ItemID.OBJECTIVE_7,
        ctenums.ItemID.OBJECTIVE_7, ctenums.ItemID.OBJECTIVE_8, ctenums.ItemID.MASAMUNE_1,
        ctenums.ItemID.MASAMUNE_2, ctenums.ItemID.FIST, ctenums.ItemID.FIST_2,
        ctenums.ItemID.FIST_3, ctenums.ItemID.IRON_FIST, ctenums.ItemID.BRONZEFIST,
        ctenums.ItemID.APITEM, ctenums.ItemID.UNUSED_4A,
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
        ctenums.ItemID.UNUSED_F1,
    ]

    if pool_type == battlerewards.RewardPoolType.SHUFFLE:
        item_assignment = {
            enemy_id: getattr(stats, attr_name) for enemy_id, stats in enemy_stat_dict.items()
            if enemy_id in enemy_pool
        }
    elif pool_type == battlerewards.RewardPoolType.RANDOM:
        allowed_items = [
            item_id for item_id in ctenums.ItemID
            if item_id not in restricted_items
        ]

        item_assignment = {
            enemy_id: rng.choice(allowed_items)
            for enemy_id in enemy_pool
        }
    else:
        raise TypeError

    for enemy_id, item_id in item_assignment.items():
        setattr(enemy_stat_dict[enemy_id], attr_name, item_id)

    for enemy_id in ctenums.EnemyID:
        if enemy_id in item_assignment:
            setattr(enemy_stat_dict[enemy_id], attr_name, item_assignment[enemy_id])
        else:
            setattr(enemy_stat_dict[enemy_id], attr_name, ctenums.ItemID.NONE)


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


def apply_reward_rando(
        reward_options: battlerewards.BattleRewards,
        enemy_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        rng: RNGType
):

    drop_enemy_pool = get_enemy_pool(enemy_dict, reward_options.drop_options, rng)
    assign_rewards(drop_enemy_pool, reward_options.drop_options, enemy_dict, rng)

    charm_enemy_pool = get_enemy_pool(enemy_dict, reward_options.charm_options, rng)
    assign_rewards(charm_enemy_pool, reward_options.charm_options, enemy_dict, rng)

    mark_charm_and_drop(enemy_dict, reward_options.charm_options.mark_charmable_enemies,
                        reward_options.drop_options.mark_dropping_enemies)

    # for enemy_id, stats in enemy_dict.items():
    #     has_charm = stats.charm_item != ctenums.ItemID.NONE
    #     has_drop = stats.drop_item != ctenums.ItemID.NONE
    #
    #     if has_charm or has_drop:
    #         print(f"{stats.name}\t{stats.charm_item}\t{stats.drop_item}")



