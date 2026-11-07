import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import Main


class StartupCsvCleanupTest(unittest.TestCase):
	def test_main_cleans_csv_files_before_authentication(self):
		with tempfile.TemporaryDirectory() as temporary_directory:
			classes_file = Path(temporary_directory) / "Classes.csv"
			scoreboard_file = Path(temporary_directory) / "Scoreboard.csv"
			classes_file.write_text(
				' name , description \n\n " Class Name " , " Description text " \n',
				encoding="utf-8",
			)
			scoreboard_file.write_text(
				" username , xp \n\n player , 10 \n",
				encoding="utf-8",
			)

			def authenticate_after_cleanup():
				self.assertEqual(
					classes_file.read_text(encoding="utf-8"),
					"name,description\nClass Name,Description text\n",
				)
				self.assertEqual(
					scoreboard_file.read_text(encoding="utf-8"),
					"username,xp\nplayer,10\n",
				)
				return None

			with (
				patch.object(Main, "CLASSES_FILE", classes_file),
				patch.object(Main, "SCOREBOARD_PATH", scoreboard_file),
				patch.object(Main, "cleanup_deleted_account_data") as cleanup_accounts,
				patch.object(Main, "_authenticate", side_effect=authenticate_after_cleanup),
			):
				Main.main()
				cleanup_accounts.assert_called_once_with()


class AreaMusicIntegrationTest(unittest.TestCase):
	def setUp(self):
		self.classes = Main.load_classes_from_csv(Main.CLASSES_FILE)
		self.music_player = Mock()

	def test_run_game_starts_area_music_and_stops_when_quitting(self):
		class_data = self.classes[0]
		game_state = {
			"class_name": class_data["name"],
			"current_area": 1,
			"character": {"level": 1, "xp": 0},
		}

		with (
			patch.object(Main, "AreaMusicPlayer", return_value=self.music_player),
			patch.object(Main, "_choose", return_value="5"),
			patch.object(Main, "save_game", return_value=True),
		):
			Main.run_game("Player", "save.json", game_state, self.classes)

		self.music_player.play_area.assert_called_once_with(1)
		self.music_player.stop.assert_called_once()

	def test_adventure_switches_music_when_entering_another_area(self):
		game_state = {
			"current_area": 1,
			"boss_defeated": True,
			"character": {"level": 1},
		}

		with (
			patch.object(Main, "_choose", return_value="2"),
			patch.object(Main, "spawn_area_monster", return_value={"type": "easy"}),
			patch.object(Main, "_resolve_encounter", return_value=True),
		):
			result = Main._adventure(
				"Player", "save.json", game_state, self.classes[0], self.music_player
			)

		self.assertTrue(result)
		self.assertEqual(game_state["current_area"], 2)
		self.music_player.play_area.assert_called_once_with(2)


class CombatProgressionIntegrationTest(unittest.TestCase):
	def setUp(self):
		self.classes = Main.load_classes_from_csv(Main.CLASSES_FILE)
		self.class_data = self.classes[0]

	def test_restore_migrates_old_skill_points_and_removes_skill_stat_bonuses(self):
		game_state = {
			"class_name": self.class_data["name"],
			"current_area": 1,
			"character": {
				"level": 1,
				"skill_points": 2,
				"stats": {"defense": 4, "analysis": 2, "response": 2, "support": 1},
			},
		}

		Main._restore_game_state(game_state, "Player", self.classes)

		character = game_state["character"]
		self.assertEqual(character["stat_points"], 2)
		self.assertNotIn("skill_points", character)
		self.assertEqual(character["stats"], self.class_data["stats"])

	def test_restore_reapplies_tracked_stat_upgrades(self):
		game_state = {
			"class_name": self.class_data["name"],
			"current_area": 1,
			"character": {
				"level": 1,
				"stat_upgrades": {"defense": 2, "support": 1},
			},
		}

		Main._restore_game_state(game_state, "Player", self.classes)

		expected_stats = self.class_data["stats"].copy()
		expected_stats["defense"] += 2
		expected_stats["support"] += 1
		self.assertEqual(game_state["character"]["stats"], expected_stats)

	def test_response_adds_its_amount_to_attack_damage(self):
		character = {
			"health": 100,
			"max_health": 100,
			"shield": 0,
			"stats": {"response": 3},
		}
		monster = {
			"name": "Test Monster",
			"health": 100,
			"shield": 0,
			"attack_damage": 0,
		}
		attack_result = {"damage": 0, "critical": False, "poison_applied": False}

		with (
			patch.object(Main, "_choose", return_value="1"),
			patch.object(Main, "monster_attack", return_value=attack_result),
		):
			Main._take_turn(character, self.class_data, monster, False, False)

		self.assertEqual(monster["health"], 92)

	def test_stat_point_menu_can_upgrade_more_than_one_stat(self):
		character = {
			"stats": {"defense": 2, "analysis": 1, "response": 2, "support": 1},
			"stat_upgrades": {},
			"stat_points": 2,
		}

		with patch.object(Main, "_choose", side_effect=["1", "2", "0"]):
			Main._spend_stat_points(character, self.class_data)

		self.assertEqual(character["stats"]["defense"], 3)
		self.assertEqual(character["stats"]["analysis"], 2)
		self.assertEqual(character["stat_points"], 0)

	def test_level_three_promotion_applies_selected_class_stat_differences(self):
		antivirus = Main.get_class_by_name("Antivirus", self.classes)
		character = {
			"level": 2,
			"xp": 0,
			"level_xp": 0,
			"stat_points": 0,
			"health": 70,
			"max_health": 100,
			"stats": antivirus["stats"].copy(),
			"stat_upgrades": {"response": 2},
			"skill_levels": {
				"Signature scanning": 2,
				"Quarantine": 1,
			},
		}
		game_state = {
			"class_name": antivirus["name"],
			"current_area": 1,
			"character": character,
		}

		with (
			patch.object(Main, "_fight", return_value=True),
			patch.object(Main, "calculate_monster_xp", return_value=300),
			patch.object(Main, "_spend_stat_points"),
			patch.object(Main, "_choose", return_value="1"),
			patch.object(Main, "save_game", return_value=True),
			patch.object(Main, "_pause_and_clear"),
		):
			Main._resolve_encounter(
				"Player",
				"save.json",
				game_state,
				antivirus,
				{"type": "easy"},
				is_boss=False,
				classes=self.classes,
			)

		email_gateway = Main.get_class_by_name("Email Security Gateway", self.classes)
		self.assertEqual(character["level"], 3)
		self.assertEqual(game_state["class_name"], email_gateway["name"])
		self.assertEqual(
			character["stats"],
			{"defense": 3, "analysis": 2, "response": 4, "support": 2},
		)
		self.assertEqual(
			character["skill_levels"],
			{"Attachment scanning": 2, "Spam filtering": 1},
		)

		Main._restore_game_state(game_state, "Player", self.classes)
		self.assertEqual(
			character["stats"],
			{"defense": 3, "analysis": 2, "response": 4, "support": 2},
		)

	def test_level_six_and_ten_promotions_follow_class_requirements(self):
		class_data = Main.get_class_by_name("Email Security Gateway", self.classes)
		game_state = {
			"class_name": class_data["name"],
			"character": {
				"level": 6,
				"stats": class_data["stats"].copy(),
				"stat_upgrades": {},
				"skill_levels": {skill: 1 for skill in class_data["skills"]},
			},
		}

		with patch.object(Main, "_choose", return_value="1"):
			class_data = Main._offer_tier_promotions(
				game_state, class_data, self.classes
			)

		self.assertEqual(class_data["name"], "Data Loss Prevention")
		self.assertEqual(class_data["tier"], 3)

		game_state["character"]["level"] = 10
		with patch.object(Main, "_choose", return_value="1"):
			class_data = Main._offer_tier_promotions(
				game_state, class_data, self.classes
			)

		self.assertEqual(class_data["tier"], 4)
		self.assertEqual(game_state["class_name"], class_data["name"])

	def test_firewall_branches_upgrade_shield_or_switch_to_fire_damage(self):
		firewall = Main.get_class_by_name("Firewall", self.classes)
		stateful = Main.get_class_by_name("Stateful Firewall", self.classes)
		web_firewall = Main.get_class_by_name("Web Application Firewall", self.classes)

		for selected_class, expected_effect, expected_bonus in (
			(stateful, "shield", 5),
			(web_firewall, "damage", 0),
		):
			game_state = {
				"class_name": firewall["name"],
				"character": {
					"level": 3,
					"stats": firewall["stats"].copy(),
					"stat_upgrades": {},
					"skill_levels": {skill: 1 for skill in firewall["skills"]},
					"ability_effect": None,
					"ability_power_bonus": 0,
				},
			}
			available = [
				candidate
				for candidate in Main.get_available_classes(
					[firewall["name"]], self.classes
				)
				if candidate["tier"] == 2
			]
			option_index = next(
				index
				for index, candidate in enumerate(available, start=1)
				if candidate["name"] == selected_class["name"]
			)

			with patch.object(Main, "_choose", return_value=str(option_index)):
				upgraded_class = Main._offer_tier_promotions(
					game_state, firewall, self.classes
				)

			character = game_state["character"]
			self.assertEqual(upgraded_class["name"], selected_class["name"])
			self.assertEqual(character["ability_effect"], expected_effect)
			self.assertEqual(character["ability_power_bonus"], expected_bonus)
			ability_name = upgraded_class["abilities"][0]
			target = {"health": 100, "shield": 0}
			result = Main.use_ability(
				upgraded_class, ability_name, character, target
			)
			if expected_effect == "shield":
				self.assertEqual(result["effect"], "shield")
				self.assertEqual(result["amount"], 32)
				self.assertGreater(character["shield"], 0)
			else:
				self.assertEqual(result["effect"], "damage")
				self.assertEqual(result["amount"], 23)
				self.assertLess(target["health"], 100)

			restored_state = {
				"class_name": upgraded_class["name"],
				"current_area": 1,
				"character": character.copy(),
			}
			Main._restore_game_state(restored_state, "Player", self.classes)
			self.assertEqual(
				restored_state["character"]["ability_effect"], expected_effect
			)

	def test_first_skill_grants_its_opening_shield_in_combat(self):
		character = {
			"health": 100,
			"max_health": 100,
			"stats": self.class_data["stats"].copy(),
			"skill_levels": {skill: 1 for skill in self.class_data["skills"]},
		}
		monster = {
			"type": "easy",
			"health": 20,
			"attack_damage": 5,
		}

		def win_after_starting(character_arg, class_arg, monster_arg, used, defending):
			self.assertEqual(character_arg["shield"], 3)
			return "win", used, defending

		with patch.object(Main, "_take_turn", side_effect=win_after_starting):
			result = Main._fight(character, self.class_data, monster)

		self.assertTrue(result)

	def test_second_skill_restores_health_after_victory(self):
		character = {
			"level": 1,
			"xp": 0,
			"level_xp": 0,
			"stat_points": 0,
			"health": 50,
			"max_health": 100,
		}
		game_state = {"character": character}

		with (
			patch.object(Main, "_fight", return_value=True),
			patch.object(Main, "calculate_monster_xp", return_value=0),
			patch.object(Main, "save_game", return_value=True),
			patch.object(Main, "_pause_and_clear"),
		):
			result = Main._resolve_encounter(
				"Player",
				"save.json",
				game_state,
				self.class_data,
				{"type": "easy"},
				is_boss=False,
			)

		self.assertTrue(result)
		self.assertEqual(character["health"], 53)


if __name__ == "__main__":
	unittest.main()
