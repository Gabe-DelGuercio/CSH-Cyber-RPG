"""
Define the level system
    there are 10 levels
    level 1 takes 100 xp to get to
    each consecutive level is 3 times harder to get to than the last
Monster XP calc
    Easy monster xp = random amount(3-6) x 5 x 2^player level
    Medium monster xp = random amount(7-10) x 5 x 2^player level
    Hard monster xp = random amount(7-10) x 5 x 2^player level
    Boss monster xp = 100 x 2^player level
Enemy spawn rate
    easy monsters spawn 75% of the time
    medium monsters spawn 20% of the time
    hard monsters spawn 5% of the time
    Bosses must be selected and grant acess to the next area.
"""
import math
import random


def calculate_xp_for_level(level):
    if level < 1:
        raise ValueError("Level must be 1 or higher.")
    return 100 * (3 ** (level - 1))


MAX_PLAYER_LEVEL = 10


def award_experience(combatant, amount):
    """Add XP and grant one stat point for every level gained."""
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise ValueError("Experience must be a non-negative integer.")

    combatant.setdefault("level", 1)
    combatant.setdefault("xp", 0)
    combatant.setdefault("level_xp", 0)
    if "stat_points" not in combatant:
        combatant["stat_points"] = combatant.pop("skill_points", 0)
    else:
        combatant.pop("skill_points", None)
    level = combatant["level"]
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= MAX_PLAYER_LEVEL:
        raise ValueError(f"Level must be between 1 and {MAX_PLAYER_LEVEL}.")

    combatant["xp"] += amount
    combatant["level_xp"] += amount
    levels_gained = 0
    while (
        combatant["level"] < MAX_PLAYER_LEVEL
        and combatant["level_xp"] >= calculate_xp_for_level(combatant["level"])
    ):
        combatant["level_xp"] -= calculate_xp_for_level(combatant["level"])
        combatant["level"] += 1
        combatant["stat_points"] += 1
        levels_gained += 1
    return levels_gained

def calculate_monster_xp(monster_type, player_level):
    import random

    if monster_type == 'easy':
        base_xp = random.randint(3, 6) * 5
    elif monster_type == 'medium':
        base_xp = random.randint(7, 10) * 5
    elif monster_type == 'hard':
        base_xp = random.randint(7, 10) * 5
    elif monster_type == 'boss':
        base_xp = 100
    else:
        raise ValueError("Invalid monster type. Must be 'easy', 'medium', 'hard', or 'boss'.")
    return base_xp * (2 ** player_level)

def get_enemy_spawn_rate(monster_type):
    if monster_type == 'easy':
        return 0.75
    elif monster_type == 'medium':
        return 0.20
    elif monster_type == 'hard':
        return 0.05
    elif monster_type == 'boss':
        return 0.00  # Bosses must be selected and do not spawn randomly
    else:
        raise ValueError("Invalid monster type. Must be 'easy', 'medium', 'hard', or 'boss'.")

def get_next_area_access(monster_type):
    if monster_type == 'boss':
        return True
    else:
        return False

def calculate_total_xp(player_level, defeated_monsters):
    total_xp = 0
    for monster_type in defeated_monsters:
        total_xp += calculate_monster_xp(monster_type, player_level)
    return total_xp


SPECIAL_ABILITY_SPAWN_CHANCE = 0.05
CRITICAL_HIT_CHANCE = 0.20
POISON_DAMAGE = 3
POISON_DURATION = 3
WEAKENED_DAMAGE_MULTIPLIER = 0.5
WEAKENED_DURATION = 2
SPECIAL_MONSTER_ABILITIES = ("poison", "critical")


def spawn_monster(monster_type, random_source=None):
    """Create a monster and optionally assign it a rare special ability."""
    get_enemy_spawn_rate(monster_type)
    random_source = random_source or random
    special_ability = None
    if random_source.random() < SPECIAL_ABILITY_SPAWN_CHANCE:
        special_ability = random_source.choice(SPECIAL_MONSTER_ABILITIES)
    return {"type": monster_type, "special_ability": special_ability}


def spawn_random_monster(random_source=None):
    """Spawn an easy, medium, or hard monster using the configured rates."""
    random_source = random_source or random
    monster_types = ("easy", "medium", "hard")
    monster_type = random_source.choices(
        monster_types,
        weights=tuple(get_enemy_spawn_rate(kind) for kind in monster_types),
        k=1,
    )[0]
    return spawn_monster(monster_type, random_source)


def _apply_combat_damage(combatant, damage, defending=False):
    stats = combatant.get("stats", {})
    blocked_damage = max(0, stats.get("defense", 0))
    if defending:
        blocked_damage += math.ceil(damage * 0.5) + max(
            0, stats.get("support", 0)
        )
    damage = max(0, damage - blocked_damage)
    combatant.setdefault("health", 100)
    combatant.setdefault("shield", 0)
    shield_damage = min(combatant["shield"], damage)
    combatant["shield"] -= shield_damage
    health_damage = min(combatant["health"], damage - shield_damage)
    combatant["health"] -= health_damage
    return shield_damage + health_damage


def monster_attack(monster, target, damage, random_source=None, defending=False):
    """Apply a monster hit, including its critical or poison trait if present."""
    if damage < 0:
        raise ValueError("Damage must be zero or greater.")
    special_ability = monster.get("special_ability")
    if special_ability not in (None, *SPECIAL_MONSTER_ABILITIES):
        raise ValueError("Monster has an unknown special ability.")

    random_source = random_source or random
    weakened = monster.get("status_effects", {}).get("weakened")
    hit_damage = damage
    if weakened and weakened["turns_remaining"] > 0 and hit_damage > 0:
        hit_damage = max(1, math.ceil(hit_damage * weakened["damage_multiplier"]))

    critical = (
        special_ability == "critical"
        and random_source.random() < CRITICAL_HIT_CHANCE
    )
    if critical:
        hit_damage *= 2
    damage_dealt = _apply_combat_damage(target, hit_damage, defending)

    poison_applied = False
    if special_ability == "poison" and damage_dealt > 0:
        status_effects = target.setdefault("status_effects", {})
        poison = status_effects.get("poison", {})
        status_effects["poison"] = {
            "damage": max(poison.get("damage", 0), POISON_DAMAGE),
            "turns_remaining": max(poison.get("turns_remaining", 0), POISON_DURATION),
        }
        poison_applied = True

    return {
        "damage": damage_dealt,
        "critical": critical,
        "poison_applied": poison_applied,
    }


def process_status_effects(combatant):
    """Apply one turn of damage-over-time effects and expire completed effects."""
    status_effects = combatant.setdefault("status_effects", {})
    results = []
    for effect_name, effect in list(status_effects.items()):
        damage = 0
        if "damage" in effect:
            damage = _apply_combat_damage(combatant, effect["damage"])
        effect["turns_remaining"] -= 1
        results.append({"effect": effect_name, "damage": damage})
        if effect["turns_remaining"] <= 0:
            del status_effects[effect_name]
    return results

_COMBAT_STATS = ("defense", "analysis", "response", "support")
_ABILITY_EFFECTS_BY_STAT = {
    "defense": "shield",
    "analysis": "debuff",
    "response": "damage",
    "support": "heal",
}
_ABILITY_STAT_BY_EFFECT = {
    "shield": "defense",
    "debuff": "analysis",
    "damage": "response",
    "heal": "support",
}
_CLASS_ABILITY_EFFECT_OVERRIDES = {
    "Web Application Firewall": "damage",
}


def _rank_class_stats(class_data):
    stats = class_data.get("stats", {})
    return sorted(
        (stat for stat in _COMBAT_STATS if stat in stats),
        key=lambda stat: (-stats[stat], _COMBAT_STATS.index(stat)),
    )


def skills(class_data):
    """Return distinct passive perks for a class's listed skills."""
    skill_perks = (
        (
            "opening_shield",
            3,
            "Start each fight with bonus shield.",
        ),
        (
            "victory_heal",
            3,
            "Recover bonus health after each victory.",
        ),
    )
    return {
        skill: {
            "type": "passive",
            "effect": skill_perks[index % len(skill_perks)][0],
            "bonus": skill_perks[index % len(skill_perks)][1],
            "description": skill_perks[index % len(skill_perks)][2],
        }
        for index, skill in enumerate(class_data.get("skills", []))
    }


def abilities(class_data, combatant=None):
    """Return active ability effects for a class.

    A class's strongest stat determines whether its ability grants a shield,
    heals its user, weakens a target, or damages a target. Ability power scales
    with stat and tier.
    """
    ranked_stats = _rank_class_stats(class_data)
    if class_data.get("abilities") and not ranked_stats:
        raise ValueError("Class must define at least one combat stat.")
    if not ranked_stats:
        return {}

    primary_stat = ranked_stats[0]
    effect = _CLASS_ABILITY_EFFECT_OVERRIDES.get(
        class_data["name"], _ABILITY_EFFECTS_BY_STAT[primary_stat]
    )
    if combatant is not None:
        effect = combatant.get("ability_effect") or effect
    power_stat = _ABILITY_STAT_BY_EFFECT[effect]
    if power_stat not in class_data["stats"]:
        power_stat = primary_stat
    power = 5 * (class_data["stats"][power_stat] + class_data["tier"])
    if combatant is not None:
        power += combatant.get("ability_power_bonus", 0)
    return {
        ability: {
            "type": "active",
            "effect": effect,
            "stat": power_stat,
            "power": power,
        }
        for ability in class_data.get("abilities", [])
    }


def new_ability_effect(class_data, current_effect):
    """Choose a distinct ability effect supported by the class's stats."""
    for stat in _rank_class_stats(class_data):
        effect = _ABILITY_EFFECTS_BY_STAT[stat]
        if effect != current_effect:
            return effect
    return next(
        effect
        for effect in _ABILITY_EFFECTS_BY_STAT.values()
        if effect != current_effect
    )


def ability_evolution_options(current_class, available_classes, character):
    """Return deterministic class branches with an upgraded or new ability."""
    current_effect = character.get("ability_effect")
    if current_effect is None:
        current_effect = next(iter(abilities(current_class).values()))["effect"]
    current_bonus = character.get("ability_power_bonus", 0)
    options = []
    ordered_classes = sorted(
        available_classes, key=lambda class_data: class_data["name"].casefold()
    )
    for index, candidate in enumerate(ordered_classes):
        if index == 0:
            options.append({
                "class": candidate,
                "path": "upgrade",
                "effect": current_effect,
                "power_bonus": current_bonus + 5,
            })
            continue

        candidate_effect = next(iter(abilities(candidate).values()))["effect"]
        effect = (
            candidate_effect
            if candidate_effect != current_effect
            else new_ability_effect(candidate, current_effect)
        )
        options.append({
            "class": candidate,
            "path": "new",
            "effect": effect,
            "power_bonus": 0,
        })
    return options


def apply_passive_skills(class_data, combatant):
    """Return a combatant state with class defaults initialized."""
    updated = dict(combatant)
    stats = dict(combatant.get("stats", class_data.get("stats", {})))
    updated["stats"] = stats
    updated.setdefault("stat_upgrades", {})
    updated.setdefault("stat_points", updated.pop("skill_points", 0))
    updated.setdefault("ability_effect", None)
    updated.setdefault("ability_power_bonus", 0)
    updated.setdefault("max_health", 100)
    updated.setdefault("health", updated["max_health"])
    updated.setdefault("shield", 0)
    return updated


def create_combatant(class_data, max_health=100):
    """Create a combat state with the class's passive skills already applied."""
    if max_health < 1:
        raise ValueError("Max health must be at least 1.")
    base_state = {
        "health": max_health,
        "max_health": max_health,
        "shield": 0,
        "stats": dict(class_data.get("stats", {})),
        "level": 1,
        "xp": 0,
        "level_xp": 0,
        "stat_points": 0,
        "stat_upgrades": {},
        "ability_effect": None,
        "ability_power_bonus": 0,
        "skill_levels": {skill: 1 for skill in class_data.get("skills", [])},
    }
    return apply_passive_skills(class_data, base_state)


def upgrade_stat(combatant, stat):
    """Spend one stat point to permanently increase a combat stat."""
    if stat not in _COMBAT_STATS:
        raise ValueError(f"{stat!r} is not a combat stat.")
    if combatant.get("stat_points", combatant.get("skill_points", 0)) < 1:
        raise ValueError("The character has no unspent stat points.")

    stats = dict(combatant.get("stats", {}))
    if stat not in stats:
        raise ValueError(f"The character does not have the {stat!r} stat.")
    stat_upgrades = dict(combatant.get("stat_upgrades", {}))
    stats[stat] += 1
    stat_upgrades[stat] = stat_upgrades.get(stat, 0) + 1
    combatant["stats"] = stats
    combatant["stat_upgrades"] = stat_upgrades
    combatant["stat_points"] = combatant.get(
        "stat_points", combatant.get("skill_points", 0)
    ) - 1
    combatant.pop("skill_points", None)
    return stats[stat]


def level_up_skill(class_data, combatant, skill_name):
    """Spend one stat point to improve a class skill by one level."""
    skill_effects = skills(class_data)
    if skill_name not in skill_effects:
        raise ValueError(f"{skill_name!r} is not a skill for this class.")
    stat_points = combatant.get("stat_points", combatant.get("skill_points", 0))
    if stat_points < 1:
        raise ValueError("The character has no unspent stat points.")

    skill_levels = dict(combatant.get("skill_levels", {}))
    new_skill_level = skill_levels.get(skill_name, 1) + 1

    combatant["skill_levels"] = {**skill_levels, skill_name: new_skill_level}
    combatant["stat_points"] = stat_points - 1
    combatant.pop("skill_points", None)
    return new_skill_level


def use_ability(class_data, ability_name, actor, target=None):
    """Use a class's active ability and update the affected combat state."""
    ability = abilities(class_data, actor).get(ability_name)
    if ability is None:
        raise ValueError(f"{ability_name!r} is not an ability for this class.")
    if ability["effect"] == "damage" and target is None:
        raise ValueError("This ability requires a target.")
    if ability["effect"] == "debuff" and target is None:
        raise ValueError("This ability requires a target.")

    actor.setdefault("max_health", 100)
    actor.setdefault("health", actor["max_health"])
    actor.setdefault("shield", 0)
    effect = ability["effect"]
    power = ability["power"] + max(
        0, actor.get("stats", {}).get("analysis", 0)
    )

    if effect == "shield":
        actor["shield"] += power
        return {"ability": ability_name, "effect": "shield", "amount": power, "power": power}

    if effect == "heal":
        healed = min(power, actor["max_health"] - actor["health"])
        actor["health"] += healed
        return {"ability": ability_name, "effect": "heal", "amount": healed, "power": power}

    if effect == "debuff":
        analysis = max(0, actor.get("stats", {}).get("analysis", 0))
        damage_multiplier = max(
            0.1, WEAKENED_DAMAGE_MULTIPLIER - 0.05 * analysis
        )
        status_effects = target.setdefault("status_effects", {})
        status_effects["weakened"] = {
            "damage_multiplier": damage_multiplier,
            "turns_remaining": WEAKENED_DURATION,
        }
        return {
            "ability": ability_name,
            "effect": "debuff",
            "damage_multiplier": damage_multiplier,
            "turns_remaining": WEAKENED_DURATION,
            "power": power,
        }

    target.setdefault("health", 100)
    target.setdefault("shield", 0)
    shield_damage = min(target["shield"], power)
    target["shield"] -= shield_damage
    health_damage = min(target["health"], power - shield_damage)
    target["health"] -= health_damage
    return {
        "ability": ability_name,
        "effect": "damage",
        "amount": shield_damage + health_damage,
        "power": power,
    }