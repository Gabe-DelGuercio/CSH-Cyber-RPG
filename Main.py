"""Command-line entry point for the Cyber Defense RPG."""
import csv
import os
from pathlib import Path

from AreaMusic import AreaMusicPlayer
from Accounts import (
	SCOREBOARD_PATH,
	choose_save_file,
	cleanup_deleted_account_data,
	continue_game,
	create_account,
	get_scoreboard,
	login,
	save_game,
)
from Areas import (
	AREAS,
	can_enter_area,
	get_area,
	get_available_areas,
	spawn_area_boss,
	spawn_area_monster,
)
from Experience_calc import (
	MAX_PLAYER_LEVEL,
	abilities,
	ability_evolution_options,
	award_experience,
	calculate_monster_xp,
	calculate_xp_for_level,
	create_combatant,
	level_up_skill,
	monster_attack,
	process_status_effects,
	skills,
	upgrade_stat,
	use_ability,
)
from RPG_Classes import (
	get_available_classes,
	get_class_by_name,
	get_tier_classes,
	load_classes_from_csv,
)


CLASSES_FILE = Path(__file__).resolve().parent / "Files" / "Classes.csv"
TIER_PROMOTION_LEVELS = {2: 3, 3: 6, 4: 10}


def _clean_csv_whitespace(file_path):
	"""Trim CSV field edges and remove empty rows before the game starts."""
	file_path = Path(file_path)
	with open(file_path, newline="", encoding="utf-8-sig") as csv_file:
		rows = [
			[field.strip() for field in row]
			for row in csv.reader(csv_file, skipinitialspace=True)
			if any(field.strip() for field in row)
		]

	temporary_path = file_path.with_name(file_path.name + ".tmp")
	with open(temporary_path, "w", newline="", encoding="utf-8") as csv_file:
		csv.writer(csv_file).writerows(rows)
	temporary_path.replace(file_path)


def _read_input(prompt):
	try:
		return input(prompt).strip()
	except (EOFError, KeyboardInterrupt):
		return None


def _pause_and_clear(prompt="Press Enter to continue..."):
	_read_input(prompt)
	os.system("cls" if os.name == "nt" else "clear")


def _choose(prompt, choices):
	while True:
		value = _read_input(prompt)
		if value is None:
			return None
		if value in choices:
			return value
		print("Invalid selection.")


def _show_scoreboard():
	print("\nTop 10 Players")
	entries = get_scoreboard(limit=10)
	if not entries:
		print("No scores recorded yet.")
	else:
		for entry in entries:
			print(f"{entry['rank']:>2}. {entry['username']} - {entry['xp']} XP")
	_pause_and_clear("Press Enter to clear the screen and return to the startup menu...")


def _authenticate():
	while True:
		print("\nCyber Defense RPG")
		print("1. Create account")
		print("2. Sign in")
		print("3. Quit")
		print("4. View top 10 scoreboard")
		choice = _choose("Select an option: ", {"1", "2", "3", "4"})
		if choice in (None, "3"):
			return None
		if choice == "4":
			_show_scoreboard()
			continue

		username = _read_input("Username: ")
		password = _read_input("Password: ")
		if not username or password is None:
			print("Username and password are required.")
			continue

		if choice == "1":
			if create_account(username, password):
				print(f"Account created. Welcome, {username}.")
				return username
			print("That username is already taken.")
		elif login(username, password):
			print(f"Welcome back, {username}.")
			return username
		else:
			print("Incorrect username or password.")


def _new_game(username, save_file, classes):
	starting_classes = get_tier_classes(1, classes)
	print("\nChoose your starting program:")
	for index, class_data in enumerate(starting_classes, start=1):
		print(f"{index}. {class_data['name']}: {class_data['description']}")

	choice = _choose(
		f"Select a class (1-{len(starting_classes)}): ",
		{str(index) for index in range(1, len(starting_classes) + 1)},
	)
	if choice is None:
		return None

	class_data = starting_classes[int(choice) - 1]
	character = create_combatant(class_data)
	game_state = {
		"username": username,
		"class_name": class_data["name"],
		"character": character,
		"current_area": 1,
		"boss_defeated": False,
		"xp": 0,
	}
	if not save_game(username, save_file, game_state):
		print("Could not create the save file.")
		return None
	print(f"New game started as {class_data['name']}.")
	return game_state


def _is_valid_game_state(game_state, classes):
	if not isinstance(game_state, dict):
		return False
	class_data = get_class_by_name(game_state.get("class_name"), classes)
	character = game_state.get("character")
	area_number = game_state.get("current_area")
	if class_data is None or not isinstance(character, dict):
		return False
	if get_area(area_number) is None:
		return False
	if not isinstance(character.get("level", 1), int):
		return False
	stat_upgrades = character.get("stat_upgrades", {})
	if not isinstance(stat_upgrades, dict):
		return False
	if any(
		stat not in class_data["stats"]
		or not isinstance(amount, int)
		or isinstance(amount, bool)
		or amount < 0
		for stat, amount in stat_upgrades.items()
	):
		return False
	if character.get("ability_effect") not in (
		None, "shield", "debuff", "damage", "heal"
	):
		return False
	ability_power_bonus = character.get("ability_power_bonus", 0)
	if (
		not isinstance(ability_power_bonus, int)
		or isinstance(ability_power_bonus, bool)
		or ability_power_bonus < 0
	):
		return False
	return True


def _restore_game_state(game_state, username, classes):
	class_data = get_class_by_name(game_state["class_name"], classes)
	character = game_state["character"]
	character.setdefault("level", 1)
	character.setdefault("xp", game_state.get("xp", 0))
	character.setdefault("level_xp", 0)
	character.setdefault(
		"stat_points", character.pop("skill_points", 0)
	)
	character.pop("skill_points", None)
	character.setdefault("max_health", 100)
	character.setdefault("health", character["max_health"])
	character.setdefault("shield", 0)
	character.setdefault("ability_effect", None)
	character.setdefault("ability_power_bonus", 0)
	stat_upgrades = character.setdefault("stat_upgrades", {})
	character["stats"] = class_data["stats"].copy()
	for stat, amount in stat_upgrades.items():
		character["stats"][stat] += amount
	character.setdefault(
		"skill_levels", {skill: 1 for skill in class_data.get("skills", [])}
	)
	game_state.setdefault("username", username)
	game_state.setdefault("current_area", 1)
	game_state.setdefault("boss_defeated", False)
	game_state["xp"] = character["xp"]
	return class_data


def _choose_or_load_game(username, save_file, classes):
	while True:
		if Path(save_file).is_file():
			game_state = continue_game(username, save_file)
			if _is_valid_game_state(game_state, classes):
				class_data = _restore_game_state(game_state, username, classes)
				print(f"Loaded {class_data['name']} in Area {game_state['current_area']}.")
				return game_state
			print("That save is invalid. Choose another slot.")
			save_file = choose_save_file(username)
			if save_file is None:
				return None
			continue
		return _new_game(username, save_file, classes)


def _deal_damage(target, damage):
	target.setdefault("health", 100)
	target.setdefault("shield", 0)
	absorbed = min(target["shield"], damage)
	target["shield"] -= absorbed
	health_damage = min(target["health"], damage - absorbed)
	target["health"] -= health_damage
	return absorbed + health_damage


def _take_turn(character, class_data, monster, compute_used, defending):
	choices = {"1", "2"}
	if not compute_used:
		choices.add("3")
	print("\nYour turn:")
	print("1. Attack")
	print("2. Defend (block half the next hit plus Support)")
	if compute_used:
		print("3. Compute (already used this fight)")
	else:
		print("3. Compute (use your class ability)")
	choice = _choose("Action: ", choices)
	if choice is None:
		return "quit", compute_used, defending

	if choice == "1":
		damage = max(1, 5 + character.get("stats", {}).get("response", 0))
		dealt = _deal_damage(monster, damage)
		print(f"You deal {dealt} damage.")
	elif choice == "2":
		defending = True
		print("You brace for the next attack; Support boosts your block.")
	else:
		available_abilities = list(abilities(class_data, character))
		for index, ability_name in enumerate(available_abilities, start=1):
			print(f"{index}. {ability_name}")
		ability_choice = _choose(
			f"Choose an ability (1-{len(available_abilities)}): ",
			{str(index) for index in range(1, len(available_abilities) + 1)},
		)
		if ability_choice is None:
			return "quit", compute_used, defending
		ability_name = available_abilities[int(ability_choice) - 1]
		result = use_ability(class_data, ability_name, character, monster)
		compute_used = True
		print(f"{ability_name}: {result['effect']} ({result.get('amount', result.get('power', result.get('turns_remaining', 0)))})")

	if monster["health"] <= 0:
		print(f"{monster['name']} is defeated.")
		return "win", compute_used, defending

	attack_result = monster_attack(
		monster, character, monster["attack_damage"], defending=defending
	)
	print(f"{monster['name']} hits you for {attack_result['damage']} damage.")
	if attack_result["critical"]:
		print("Critical hit!")
	if attack_result["poison_applied"]:
		print("You are poisoned for the next three turns.")
	if character["health"] <= 0:
		print("You have been defeated.")
		return "loss", compute_used, False
	return "continue", compute_used, False


def _fight(character, class_data, monster):
	character["shield"] = sum(
		effect["bonus"] * character.get("skill_levels", {}).get(skill_name, 1)
		for skill_name, effect in skills(class_data).items()
		if effect["effect"] == "opening_shield"
	)
	character.pop("status_effects", None)
	monster.setdefault("name", monster["type"].title())
	monster.setdefault("max_health", monster["health"])
	compute_used = False
	defending = False

	print(
		f"\n{monster['name']} appears! "
		f"HP {monster['health']}, attack {monster['attack_damage']}"
	)
	if monster.get("special_ability"):
		print(f"Special trait: {monster['special_ability']}")

	while True:
		process_status_effects(monster)
		for status in process_status_effects(character):
			if status["damage"]:
				print(f"Poison deals {status['damage']} damage.")
		if character["health"] <= 0:
			print("You were defeated by a status effect.")
			return False

		print(
			f"\nYou: {character['health']}/{character['max_health']} HP "
			f"({character.get('shield', 0)} shield) | "
			f"{monster['name']}: {monster['health']}/{monster['max_health']} HP"
		)
		result, compute_used, defending = _take_turn(
			character, class_data, monster, compute_used, defending
		)
		if result == "win":
			return True
		if result == "loss":
			return False
		if result == "quit":
			return None


def _spend_stat_points(character, class_data):
	class_skills = skills(class_data)
	stat_names = ("defense", "analysis", "response", "support")
	while character.get("stat_points", 0) > 0:
		print(f"\nYou have {character['stat_points']} stat point(s).")
		options = [("stat", stat) for stat in stat_names]
		options.extend(("skill", skill_name) for skill_name in class_skills)
		for index, (option_type, option_name) in enumerate(options, start=1):
			if option_type == "stat":
				print(
					f"{index}. Increase {option_name.title()} "
					f"(currently {character['stats'].get(option_name, 0)})"
				)
				continue
			level = character.get("skill_levels", {}).get(option_name, 1)
			effect = class_skills[option_name]
			print(
				f"{index}. Improve {option_name} (level {level}): "
				f"{effect['description']} +{effect['bonus']} per level"
			)
		print("0. Save this point for later")
		choice = _choose(
			f"Spend a stat point (0-{len(options)}): ",
			{"0", *(str(index) for index in range(1, len(options) + 1))},
		)
		if choice in (None, "0"):
			return
		option_type, option_name = options[int(choice) - 1]
		if option_type == "stat":
			new_value = upgrade_stat(character, option_name)
			print(f"{option_name.title()} increased to {new_value}.")
		else:
			new_level = level_up_skill(class_data, character, option_name)
			print(f"{option_name} reached level {new_level}.")


def _offer_tier_promotions(game_state, class_data, classes):
	"""Offer eligible class advancements unlocked by the character's level."""
	character = game_state["character"]
	for tier, required_level in TIER_PROMOTION_LEVELS.items():
		if character["level"] < required_level or class_data["tier"] >= tier:
			continue

		available_classes = [
			candidate
			for candidate in get_available_classes([class_data["name"]], classes)
			if candidate["tier"] == tier
		]
		if not available_classes:
			continue
		upgrade_options = ability_evolution_options(
			class_data, available_classes, character
		)

		print(f"\nLevel {required_level} reached: choose a Tier {tier} program.")
		for index, option in enumerate(upgrade_options, start=1):
			path_description = (
				f"strengthen your {option['effect']} ability"
				if option["path"] == "upgrade"
				else f"gain a {option['effect']} ability"
			)
			candidate = option["class"]
			print(
				f"{index}. {candidate['name']} ({path_description}): "
				f"{candidate['description']}"
			)
		print("0. Decide later")
		choice = _choose(
			f"Choose a class upgrade (0-{len(upgrade_options)}): ",
			{"0", *(str(index) for index in range(1, len(upgrade_options) + 1))},
		)
		if choice in (None, "0"):
			break

		selected_option = upgrade_options[int(choice) - 1]
		new_class = selected_option["class"]
		old_class = class_data
		stat_upgrades = character.get("stat_upgrades", {})
		character["stats"] = {
			stat: value + stat_upgrades.get(stat, 0)
			for stat, value in new_class["stats"].items()
		}
		old_skill_levels = character.get("skill_levels", {})
		character["skill_levels"] = {
			skill: old_skill_levels.get(old_skill, 1)
			for skill, old_skill in zip(
				new_class.get("skills", []), old_class.get("skills", [])
			)
		}
		character["skill_levels"].update(
			{
				skill: 1
				for skill in new_class.get("skills", [])
				if skill not in character["skill_levels"]
			}
		)
		character["ability_effect"] = selected_option["effect"]
		character["ability_power_bonus"] = selected_option["power_bonus"]
		game_state["class_name"] = new_class["name"]
		class_data = new_class

		stat_changes = []
		for stat, value in new_class["stats"].items():
			change = value - old_class["stats"].get(stat, 0)
			if change:
				stat_changes.append(f"{stat.title()} {change:+d}")
		print(f"Class upgraded to {new_class['name']}.")
		if selected_option["path"] == "upgrade":
			print(
				f"Your {selected_option['effect']} ability is strengthened "
				f"(+5 power)."
			)
		else:
			print(
				f"You gain a new {selected_option['effect']} ability, "
				"replacing your previous active effect."
			)
		if stat_changes:
			print("Stat changes: " + ", ".join(stat_changes))

	return class_data


def _resolve_encounter(
	username,
	save_file,
	game_state,
	class_data,
	monster,
	is_boss,
	music_player=None,
	classes=None,
):
	character = game_state["character"]
	won = _fight(character, class_data, monster)
	if won is None:
		return None
	if not won:
		character["health"] = max(1, character["max_health"])
		character["shield"] = 0
		character.pop("status_effects", None)
		print(f"You recover to {character['health']} HP. No XP awarded.")
		_pause_and_clear()
		return True

	character.pop("status_effects", None)
	xp_gained = calculate_monster_xp(monster["type"], character["level"])
	levels_gained = award_experience(character, xp_gained)
	game_state["xp"] = character["xp"]
	print(f"You gained {xp_gained} XP. Total XP: {character['xp']}.")
	if classes is None:
		classes = load_classes_from_csv(CLASSES_FILE)
	class_data = _offer_tier_promotions(game_state, class_data, classes)
	if levels_gained:
		print(f"Level up! You are now level {character['level']}.")
		_spend_stat_points(character, class_data)

	victory_heal = sum(
		effect["bonus"] * character.get("skill_levels", {}).get(skill_name, 1)
		for skill_name, effect in skills(class_data).items()
		if effect["effect"] == "victory_heal"
	)
	healed = min(victory_heal, character["max_health"] - character["health"])
	character["health"] += healed
	if healed:
		print(f"Your skills restore {healed} HP.")

	if is_boss:
		area_number = game_state["current_area"]
		game_state["boss_defeated"] = True
		next_area = area_number + 1
		if get_area(next_area) and can_enter_area(
			next_area, area_number, boss_defeated=True
		):
			game_state["current_area"] = next_area
			game_state["boss_defeated"] = False
			print(f"Boss defeated! You advance to Area {next_area}: {get_area(next_area)['name']}.")
			if music_player is not None:
				music_player.play_area(next_area)
		else:
			print("The Singularity Core is cleared. You completed the campaign!")

	game_state["xp"] = character["xp"]
	if not save_game(username, save_file, game_state):
		print("Warning: the game could not be saved.")
	_pause_and_clear()
	return True


def _adventure(
	username, save_file, game_state, class_data, music_player=None, classes=None
):
	current_area = game_state["current_area"]
	if game_state.get("boss_defeated"):
		available_areas = get_available_areas(current_area, boss_defeated=True)
		print("\nAvailable areas:")
		for index, area in enumerate(available_areas, start=1):
			print(f"{index}. Area {area['number']}: {area['name']}")
		choice = _choose(
			"Choose an area, or press Enter to cancel: ",
			{str(index) for index in range(1, len(available_areas) + 1)},
		)
		if choice is None:
			return False
		current_area = available_areas[int(choice) - 1]["number"]
		game_state["current_area"] = current_area
		game_state["boss_defeated"] = False
		if music_player is not None:
			music_player.play_area(current_area)

	area = get_area(current_area)
	print(f"\nExploring Area {current_area}: {area['name']}")
	monster = spawn_area_monster(current_area, game_state["character"]["level"])
	monster["name"] = f"{monster['type'].title()} Intruder"
	return _resolve_encounter(
		username, save_file, game_state, class_data, monster, is_boss=False,
		music_player=music_player, classes=classes,
	) is not None


def _fight_area_boss(
	username, save_file, game_state, class_data, music_player=None, classes=None
):
	if game_state.get("boss_defeated"):
		print("This area's boss has already been defeated. Choose Adventure to advance.")
		return True
	monster = spawn_area_boss(
		game_state["current_area"], game_state["character"]["level"]
	)
	monster["name"] = f"Area {game_state['current_area']} Boss"
	return _resolve_encounter(
		username, save_file, game_state, class_data, monster, is_boss=True,
		music_player=music_player, classes=classes,
	) is not None


def _show_level(character):
	print(f"\nLevel: {character['level']}/{MAX_PLAYER_LEVEL}")
	print(f"Total XP: {character['xp']}")
	if character["level"] < MAX_PLAYER_LEVEL:
		needed = calculate_xp_for_level(character["level"])
		print(f"XP toward next level: {character['level_xp']}/{needed}")
	else:
		print("Maximum level reached.")
	print(f"Unspent stat points: {character.get('stat_points', 0)}")
	_pause_and_clear()


def _show_abilities(class_data, character):
	print(f"\nClass: {class_data['name']}")
	print("Combat stats:")
	for stat_name in ("defense", "analysis", "response", "support"):
		print(f"- {stat_name.title()}: {character['stats'].get(stat_name, 0)}")
	print("Skills:")
	for skill_name, effect in skills(class_data).items():
		level = character.get("skill_levels", {}).get(skill_name, 1)
		print(
			f"- {skill_name} (level {level}): {effect['description']} "
			f"(+{effect['bonus'] * level})"
		)
	print("Active ability:")
	for ability_name, effect in abilities(class_data, character).items():
		print(
			f"- {ability_name}: {effect['effect']} using {effect['stat']} "
			f"(power {effect['power']} plus Analysis)"
		)
	print(
		"Combat actions: Defense reduces incoming damage; Response adds attack damage; "
		"Analysis boosts active abilities; Support strengthens Defend."
	)
	_pause_and_clear()


def run_game(username, save_file, game_state, classes=None):
	"""Run the main game menu for an authenticated player."""
	if classes is None:
		classes = load_classes_from_csv(CLASSES_FILE)
	if not _is_valid_game_state(game_state, classes):
		raise ValueError("Invalid game state.")
	class_data = _restore_game_state(game_state, username, classes)
	class_data = _offer_tier_promotions(game_state, class_data, classes)
	music_player = AreaMusicPlayer()

	try:
		music_player.play_area(game_state["current_area"])
		while True:
			area = get_area(game_state["current_area"])
			print(f"\n{username} | {class_data['name']} | Area {area['number']}: {area['name']}")
			print("1. Adventure")
			print("2. Check level")
			print("3. Check abilities and actions")
			print("4. Fight area boss")
			print("5. Save and quit")
			choice = _choose("Choose an action: ", {"1", "2", "3", "4", "5"})
			if choice is None or choice == "5":
				game_state["xp"] = game_state["character"]["xp"]
				if not save_game(username, save_file, game_state):
					print("Warning: the game could not be saved.")
				return game_state

			if choice == "1":
				if not _adventure(
					username, save_file, game_state, class_data, music_player, classes
				):
					return game_state
			elif choice == "2":
				_show_level(game_state["character"])
			elif choice == "3":
				_show_abilities(class_data, game_state["character"])
			else:
				if not _fight_area_boss(
					username, save_file, game_state, class_data, music_player, classes
				):
					return game_state

			class_data = get_class_by_name(game_state["class_name"], classes)
			game_state["xp"] = game_state["character"]["xp"]
			if not save_game(username, save_file, game_state):
				print("Warning: the game could not be saved.")
	finally:
		music_player.stop()


def main():
	_clean_csv_whitespace(CLASSES_FILE)
	_clean_csv_whitespace(SCOREBOARD_PATH)
	cleanup_deleted_account_data()
	username = _authenticate()
	if username is None:
		print("Goodbye.")
		return

	classes = load_classes_from_csv(CLASSES_FILE)
	save_file = choose_save_file(username)
	if save_file is None:
		print("No save slot selected.")
		return
	game_state = _choose_or_load_game(username, save_file, classes)
	if game_state is None:
		print("Game not started.")
		return
	run_game(username, save_file, game_state, classes)


if __name__ == "__main__":
	main()
