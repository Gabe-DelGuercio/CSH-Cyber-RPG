import random
import unittest
from pathlib import Path

from RPG_Classes import get_available_classes, load_classes_from_csv
from Experience_calc import (
	MAX_PLAYER_LEVEL,
	award_experience,
	abilities,
	ability_evolution_options,
	calculate_xp_for_level,
	create_combatant,
	level_up_skill,
	monster_attack,
	process_status_effects,
	skills,
	upgrade_stat,
	use_ability,
)


class ExperienceProgressionTest(unittest.TestCase):
	def test_random_xp_amount_preserves_level_progression(self):
		max_level_xp = sum(
			calculate_xp_for_level(level)
			for level in range(1, MAX_PLAYER_LEVEL)
		)
		xp_amount = random.randint(0, max_level_xp)
		combatant = {
			"level": 1,
			"xp": 0,
			"level_xp": 0,
			"stat_points": 0,
		}

		expected_level = 1
		expected_level_xp = xp_amount
		while (
			expected_level < MAX_PLAYER_LEVEL
			and expected_level_xp >= calculate_xp_for_level(expected_level)
		):
			expected_level_xp -= calculate_xp_for_level(expected_level)
			expected_level += 1

		levels_gained = award_experience(combatant, xp_amount)

		assert 0 <= xp_amount <= max_level_xp
		assert combatant["xp"] == xp_amount
		assert combatant["level"] == expected_level
		assert combatant["level_xp"] == expected_level_xp
		assert levels_gained == expected_level - 1
		assert combatant["stat_points"] == levels_gained

	def test_exact_max_level_xp_stops_at_level_cap(self):
		max_level_xp = sum(
			calculate_xp_for_level(level)
			for level in range(1, MAX_PLAYER_LEVEL)
		)
		combatant = {"level": 1, "xp": 0, "level_xp": 0, "stat_points": 0}

		levels_gained = award_experience(combatant, max_level_xp)

		assert combatant["level"] == MAX_PLAYER_LEVEL
		assert combatant["level_xp"] == 0
		assert levels_gained == MAX_PLAYER_LEVEL - 1
		assert combatant["stat_points"] == MAX_PLAYER_LEVEL - 1

	def test_legacy_skill_points_migrate_to_stat_points(self):
		combatant = {"level": 1, "xp": 0, "level_xp": 0, "skill_points": 2}

		award_experience(combatant, 0)

		assert combatant["stat_points"] == 2
		assert "skill_points" not in combatant


class CombatStatAndSkillTest(unittest.TestCase):
	def setUp(self):
		self.class_data = {
			"name": "Test Class",
			"tier": 1,
			"stats": {
				"defense": 2,
				"analysis": 1,
				"response": 1,
				"support": 1,
			},
			"skills": ["Opening Skill", "Victory Skill"],
			"abilities": ["Test Ability"],
		}

	def test_each_stat_can_be_upgraded_with_a_stat_point(self):
		combatant = create_combatant(self.class_data)
		combatant["stat_points"] = 4

		for stat in ("defense", "analysis", "response", "support"):
			upgrade_stat(combatant, stat)

		self.assertEqual(
			combatant["stats"],
			{"defense": 3, "analysis": 2, "response": 2, "support": 2},
		)
		self.assertEqual(combatant["stat_upgrades"], {
			"defense": 1,
			"analysis": 1,
			"response": 1,
			"support": 1,
		})
		self.assertEqual(combatant["stat_points"], 0)

	def test_skills_have_distinct_effects_and_do_not_raise_stats(self):
		combatant = create_combatant(self.class_data)
		skill_effects = skills(self.class_data)

		self.assertEqual(combatant["stats"], self.class_data["stats"])
		self.assertEqual(
			[effect["effect"] for effect in skill_effects.values()],
			["opening_shield", "victory_heal"],
		)

		combatant["stat_points"] = 1
		level_up_skill(self.class_data, combatant, "Victory Skill")

		self.assertEqual(combatant["stats"], self.class_data["stats"])
		self.assertEqual(combatant["skill_levels"]["Victory Skill"], 2)
		self.assertEqual(combatant["stat_points"], 0)

	def test_analysis_increases_active_ability_power(self):
		combatant = create_combatant(self.class_data)
		result = use_ability(
			self.class_data, "Test Ability", combatant
		)

		self.assertEqual(result["power"], 16)
		self.assertEqual(combatant["shield"], 16)

		combatant["stats"]["analysis"] += 3
		result = use_ability(
			self.class_data, "Test Ability", combatant
		)

		self.assertEqual(result["power"], 19)
		self.assertEqual(combatant["shield"], 35)

	def test_class_upgrade_offers_a_stronger_ability_and_a_distinct_one(self):
		firewall = {
			"name": "Firewall",
			"tier": 1,
			"stats": {
				"defense": 2,
				"analysis": 2,
				"response": 1,
				"support": 1,
			},
			"abilities": ["Cinder Screen"],
		}
		stateful_firewall = {
			"name": "Stateful Firewall",
			"tier": 2,
			"stats": {
				"defense": 3,
				"analysis": 2,
				"response": 2,
				"support": 1,
			},
			"abilities": ["Flamebound Passage"],
		}
		web_application_firewall = {
			"name": "Web Application Firewall",
			"tier": 2,
			"stats": {
				"defense": 3,
				"analysis": 3,
				"response": 2,
				"support": 1,
			},
			"abilities": ["Inferno Gate"],
		}
		character = {
			"stats": firewall["stats"].copy(),
			"ability_effect": None,
			"ability_power_bonus": 0,
		}

		options = ability_evolution_options(
			firewall, [stateful_firewall, web_application_firewall], character
		)

		self.assertEqual(options[0]["path"], "upgrade")
		self.assertEqual(options[0]["effect"], "shield")
		self.assertEqual(options[0]["power_bonus"], 5)
		self.assertGreater(
			abilities(stateful_firewall)["Flamebound Passage"]["power"]
			+ options[0]["power_bonus"],
			abilities(firewall)["Cinder Screen"]["power"],
		)
		self.assertEqual(options[1]["path"], "new")
		self.assertEqual(options[1]["effect"], "damage")
		self.assertEqual(options[1]["power_bonus"], 0)

	def test_defense_always_reduces_damage_and_support_improves_defending(self):
		attacker = {"special_ability": None}
		target = {
			"health": 100,
			"shield": 0,
			"stats": {"defense": 3, "support": 4},
		}

		normal_hit = monster_attack(attacker, target, 20)
		self.assertEqual(normal_hit["damage"], 17)

		target["health"] = 100
		defended_hit = monster_attack(attacker, target, 20, defending=True)
		self.assertEqual(defended_hit["damage"], 3)

	def test_defense_also_reduces_damage_over_time(self):
		combatant = {
			"health": 100,
			"shield": 0,
			"stats": {"defense": 2},
			"status_effects": {
				"poison": {"damage": 5, "turns_remaining": 1},
			},
		}

		result = process_status_effects(combatant)

		self.assertEqual(result[0]["damage"], 3)
		self.assertEqual(combatant["health"], 97)

	def test_analysis_improves_active_debuff_power(self):
		debuff_class = {
			**self.class_data,
			"stats": {
				"defense": 1,
				"analysis": 3,
				"response": 1,
				"support": 1,
			},
		}
		actor = create_combatant(debuff_class)
		target = {"health": 100, "shield": 0}

		result = use_ability(debuff_class, "Test Ability", actor, target)

		self.assertEqual(result["damage_multiplier"], 0.35)
		self.assertEqual(target["status_effects"]["weakened"]["damage_multiplier"], 0.35)


class AllTierAbilityEvolutionTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		classes_file = Path(__file__).resolve().parents[1] / "Files" / "Classes.csv"
		cls.classes = load_classes_from_csv(classes_file)

	def test_every_class_transition_offers_both_ability_evolution_paths(self):
		transitions = 0
		for current_class in self.classes:
			available_classes = [
				candidate
				for candidate in get_available_classes(
					[current_class["name"]], self.classes
				)
				if candidate["tier"] == current_class["tier"] + 1
			]
			if not available_classes:
				continue

			with self.subTest(current_class=current_class["name"]):
				current_effect = next(
					iter(abilities(current_class).values())
				)["effect"]
				character = {
					"ability_effect": current_effect,
					"ability_power_bonus": 0,
				}
				options = ability_evolution_options(
					current_class, available_classes, character
				)

				self.assertEqual(len(options), len(available_classes))
				self.assertEqual(
					[option["path"] for option in options].count("upgrade"), 1
				)
				self.assertEqual(
					[option["path"] for option in options].count("new"),
					len(available_classes) - 1,
				)
				for option in options:
					ability_name = option["class"]["abilities"][0]
					with self.subTest(
						class_name=option["class"]["name"],
						path=option["path"],
					):
						if option["path"] == "upgrade":
							self.assertEqual(option["effect"], current_effect)
							self.assertEqual(option["power_bonus"], 5)
						else:
							self.assertNotEqual(option["effect"], current_effect)
							self.assertEqual(option["power_bonus"], 0)

						evolved_state = {
							"ability_effect": option["effect"],
							"ability_power_bonus": option["power_bonus"],
						}
						evolved_ability = abilities(
							option["class"], evolved_state
						)[ability_name]
						self.assertEqual(
							evolved_ability["effect"], option["effect"]
						)
						self.assertGreater(evolved_ability["power"], 0)
				transitions += 1

		self.assertEqual(transitions, 28)


if __name__ == "__main__":
	unittest.main()
