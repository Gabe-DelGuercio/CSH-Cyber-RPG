"""Area progression and scaled monster encounters."""
import math
import random

from Experience_calc import get_enemy_spawn_rate, spawn_monster


AREAS = (
	{
		"number": 1,
		"name": "Perimeter Outskirts",
		"tier": 1,
		"boss_level": 2,
		"bonus": False,
		"description": "A breached outer network where small threats slip past the first defenses.",
		"monster_types": ("easy", "medium"),
		"difficulty_multiplier": 1.0,
	},
	{
		"number": 2,
		"name": "Malware Wetlands",
		"tier": 2,
		"boss_level": 3,
		"bonus": False,
		"description": "A corrupted data marsh filled with spreading infections and suspicious traffic.",
		"monster_types": ("easy", "medium", "hard"),
		"difficulty_multiplier": 1.0,
	},
	{
		"number": 3,
		"name": "Botnet Citadel",
		"tier": 3,
		"boss_level": 6,
		"bonus": False,
		"description": "A fortified command network where coordinated threats strike together.",
		"monster_types": ("medium", "hard"),
		"difficulty_multiplier": 1.0,
	},
	{
		"number": 4,
		"name": "Ransomware Vault",
		"tier": 4,
		"boss_level": 10,
		"bonus": False,
		"description": "A locked archive guarded by destructive threats and a chosen boss.",
		"monster_types": ("medium", "hard"),
		"difficulty_multiplier": 1.0,
	},
	{
		"number": 5,
		"name": "Zero-Day Labyrinth",
		"tier": None,
		"boss_level": 10,
		"bonus": True,
		"description": "An optional maze of unknown vulnerabilities built for seasoned defenders.",
		"monster_types": ("hard",),
		"difficulty_multiplier": 2.0,
	},
	{
		"number": 6,
		"name": "Singularity Core",
		"tier": None,
		"boss_level": 10,
		"bonus": True,
		"description": "The final optional gauntlet where every system-level threat reaches its peak.",
		"monster_types": ("hard",),
		"difficulty_multiplier": 2.75,
	},
)

MONSTER_BASE_STATS = {
	"easy": {"health": 25, "attack_damage": 5},
	"medium": {"health": 50, "attack_damage": 10},
	"hard": {"health": 50, "attack_damage": 10},
	"boss": {"health": 50, "attack_damage": 10},
}
PLAYER_LEVEL_SCALING = 0.1


def get_area(area_number):
	"""Return the definition for an area, or None if it does not exist."""
	return next((area for area in AREAS if area["number"] == area_number), None)


def can_enter_area(area_number, current_area, boss_defeated=False):
	"""Check whether a player can enter an area without backtracking."""
	if get_area(area_number) is None or get_area(current_area) is None:
		return False
	if area_number < current_area:
		return False
	if area_number == current_area:
		return True
	return area_number == current_area + 1 and boss_defeated


def get_available_areas(current_area, boss_defeated=False):
	"""Return the current area and any immediately unlocked next area."""
	return [
		area
		for area in AREAS
		if can_enter_area(area["number"], current_area, boss_defeated)
	]


def scale_monster(monster, player_level, area_number):
	"""Return a monster scaled by both the player's level and area difficulty."""
	area = get_area(area_number)
	if area is None:
		raise ValueError(f"Unknown area: {area_number}")
	if not isinstance(player_level, int) or isinstance(player_level, bool) or player_level < 1:
		raise ValueError("Player level must be a positive integer.")

	monster_type = monster.get("type")
	if monster_type not in MONSTER_BASE_STATS:
		raise ValueError(f"Unknown monster type: {monster_type}")

	level_multiplier = 1 + PLAYER_LEVEL_SCALING * (player_level - 1)
	multiplier = area["difficulty_multiplier"] * level_multiplier
	base_stats = MONSTER_BASE_STATS[monster_type]
	scaled_monster = dict(monster)
	scaled_monster.update(
		{
			"area": area_number,
			"level": player_level,
			"health": math.ceil(monster.get("health", base_stats["health"]) * multiplier),
			"attack_damage": math.ceil(
				monster.get("attack_damage", base_stats["attack_damage"]) * multiplier
			),
		}
	)
	scaled_monster["max_health"] = scaled_monster["health"]
	return scaled_monster


def spawn_area_monster(area_number, player_level, random_source=None):
	"""Spawn a weighted non-boss encounter and scale it for the area and level."""
	area = get_area(area_number)
	if area is None:
		raise ValueError(f"Unknown area: {area_number}")
	random_source = random_source or random
	monster_type = random_source.choices(
		area["monster_types"],
		weights=tuple(get_enemy_spawn_rate(kind) for kind in area["monster_types"]),
		k=1,
	)[0]
	monster = spawn_monster(monster_type, random_source)
	return scale_monster(monster, player_level, area_number)


def spawn_area_boss(area_number, player_level=None, random_source=None):
	"""Create a boss with fixed stats determined by its area."""
	_ = player_level
	area = get_area(area_number)
	if area is None:
		raise ValueError(f"Unknown area: {area_number}")
	monster = spawn_monster("boss", random_source)
	return scale_monster(monster, area["boss_level"], area_number)
