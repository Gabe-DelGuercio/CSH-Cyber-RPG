import unittest
from unittest.mock import Mock

from Areas import AREAS, spawn_area_boss, spawn_area_monster


class AreaBossScalingTest(unittest.TestCase):
	def test_first_four_areas_keep_a_flat_difficulty_multiplier(self):
		self.assertEqual(
			[area["difficulty_multiplier"] for area in AREAS[:4]],
			[1.0, 1.0, 1.0, 1.0],
		)

	def test_boss_stats_match_the_tier_unlock_levels(self):
		bosses = [
			spawn_area_boss(area_number)
			for area_number in range(1, 5)
		]

		self.assertEqual(
			[boss["level"] for boss in bosses],
			[2, 3, 6, 10],
		)
		self.assertEqual(
			[(boss["health"], boss["attack_damage"]) for boss in bosses],
			[(56, 11), (60, 12), (75, 15), (95, 19)],
		)

	def test_boss_stats_are_fixed_for_an_area_across_player_levels(self):
		bosses = [
			spawn_area_boss(1, player_level=level)
			for level in (1, 3, 10, 50)
		]

		self.assertEqual(
			[(boss["health"], boss["attack_damage"]) for boss in bosses],
			[(bosses[0]["health"], bosses[0]["attack_damage"])] * len(bosses),
		)
		self.assertEqual({boss["level"] for boss in bosses}, {2})

	def test_boss_stats_still_reflect_area_difficulty(self):
		first_area_boss = spawn_area_boss(1, player_level=10)
		second_area_boss = spawn_area_boss(2, player_level=10)

		self.assertGreater(second_area_boss["health"], first_area_boss["health"])
		self.assertGreater(
			second_area_boss["attack_damage"], first_area_boss["attack_damage"]
		)

	def test_regular_monsters_remain_scaled_by_player_level(self):
		random_source = Mock()
		random_source.choices.side_effect = lambda population, **kwargs: [population[0]]
		random_source.random.return_value = 1
		low_level = spawn_area_monster(1, 1, random_source)
		high_level = spawn_area_monster(1, 10, random_source)

		self.assertGreater(high_level["health"], low_level["health"])
		self.assertGreater(high_level["attack_damage"], low_level["attack_damage"])


if __name__ == "__main__":
	unittest.main()
