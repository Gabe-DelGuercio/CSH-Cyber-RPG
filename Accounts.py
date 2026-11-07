"""
Def users
    start game by asking the player to create a username and password or login with one.
    if the player creates an acount
        allow them to chose a new save out of 4 open ones to start playing
    if the player logs in
        allow them to continue using the save file they chose for before or choose a new one.
"""
import csv
import hashlib
import hmac
import json
import secrets
import shutil
from pathlib import Path


SCOREBOARD_PATH = Path(__file__).resolve().parent / "Files" / "Scoreboard.csv"
SAVE_DIRECTORY = Path(__file__).resolve().parent / "Files" / "Saves"
SAVE_SLOT_COUNT = 4
_PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
_PASSWORD_HASH_ITERATIONS = 600_000
_active_users = set()


def _get_save_paths(username):
    account_key = hashlib.sha256(username.encode("utf-8")).hexdigest()
    account_directory = SAVE_DIRECTORY / account_key
    return [
        account_directory / f"slot_{slot_number}.json"
        for slot_number in range(1, SAVE_SLOT_COUNT + 1)
    ]

def _get_account_usernames():
    account_path = Path("accounts.csv")
    if not account_path.is_file():
        return None

    with open(account_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            return set()
        if "username" not in reader.fieldnames:
            raise ValueError("accounts.csv must contain a username column.")
        return {
            row["username"]
            for row in reader
            if row.get("username")
        }


def _write_scoreboard(scores, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")
    with open(temporary_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=("username", "xp"))
        writer.writeheader()
        writer.writerows(
            {"username": username, "xp": xp}
            for username, xp in sorted(
                scores.items(), key=lambda score: (-score[1], score[0].casefold())
            )
        )
    temporary_path.replace(path)


def _remove_deleted_account_data(account_usernames):
    scoreboard_entries = get_scoreboard()
    scores = {
        entry["username"]: entry["xp"]
        for entry in scoreboard_entries
        if entry["username"] in account_usernames
    }
    if len(scores) != len(scoreboard_entries):
        _write_scoreboard(scores, SCOREBOARD_PATH)

    if SAVE_DIRECTORY.is_dir():
        active_save_directories = {
            hashlib.sha256(username.encode("utf-8")).hexdigest()
            for username in account_usernames
        }
        for account_directory in SAVE_DIRECTORY.iterdir():
            directory_name = account_directory.name
            if (
                account_directory.is_dir()
                and len(directory_name) == 64
                and all(character in "0123456789abcdef" for character in directory_name)
                and directory_name not in active_save_directories
            ):
                shutil.rmtree(account_directory)

    _active_users.intersection_update(account_usernames)


def cleanup_deleted_account_data():
    """Remove save and scoreboard data for usernames no longer in accounts.csv."""
    account_usernames = _get_account_usernames()
    if account_usernames is None:
        return
    _remove_deleted_account_data(account_usernames)


def get_scoreboard(limit=None, scoreboard_path=None):
    """Return scoreboard entries ranked by XP, highest first."""
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or limit < 0
    ):
        raise ValueError("Limit must be a non-negative integer or None.")

    path = Path(scoreboard_path) if scoreboard_path is not None else SCOREBOARD_PATH
    scores = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as csv_file:
            for row in csv.DictReader(csv_file):
                username = row.get("username")
                if not username:
                    continue
                try:
                    xp = int(row["xp"])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"Invalid XP score for {username!r}.") from error
                if xp < 0:
                    raise ValueError(f"XP score for {username!r} cannot be negative.")
                scores[username] = xp

    ordered_scores = sorted(
        scores.items(), key=lambda score: (-score[1], score[0].casefold())
    )
    if limit is not None:
        ordered_scores = ordered_scores[:limit]
    return [
        {"rank": rank, "username": username, "xp": xp}
        for rank, (username, xp) in enumerate(ordered_scores, start=1)
    ]


def update_scoreboard(username, xp, scoreboard_path=None):
    """Insert or update one account's XP and persist the ranked scoreboard."""
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Username must be a non-empty string.")
    if not isinstance(xp, int) or isinstance(xp, bool) or xp < 0:
        raise ValueError("XP must be a non-negative integer.")

    path = Path(scoreboard_path) if scoreboard_path is not None else SCOREBOARD_PATH
    scores = {
        entry["username"]: entry["xp"]
        for entry in get_scoreboard(scoreboard_path=path)
    }
    scores[username] = xp
    _write_scoreboard(scores, path)
    return get_scoreboard(scoreboard_path=path)


def _ensure_scoreboard_user(username):
    if not any(entry["username"] == username for entry in get_scoreboard()):
        update_scoreboard(username, 0)


def _hash_password(password):
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_HASH_ITERATIONS
    )
    return (
        f"{_PASSWORD_HASH_SCHEME}${_PASSWORD_HASH_ITERATIONS}"
        f"${salt.hex()}${password_hash.hex()}"
    )


def _verify_password(password, stored_password):
    try:
        scheme, iterations, salt_hex, password_hash_hex = stored_password.split("$")
        if (
            scheme != _PASSWORD_HASH_SCHEME
            or int(iterations) != _PASSWORD_HASH_ITERATIONS
        ):
            return False
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(password_hash_hex)
    except (AttributeError, ValueError):
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_HASH_ITERATIONS
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def create_account(username, password):
    """
    Create a new user account.

    Args:
        username (str): The desired username for the account.
        password (str): The desired password for the account.

    Returns:
        bool: True if the account was created successfully, False if the username already exists.
    """
    cleanup_deleted_account_data()
    account_path = Path("accounts.csv")
    if account_path.exists():
        with open(account_path, newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if row["username"] == username:
                    return False

    needs_header = not account_path.exists() or account_path.stat().st_size == 0
    with open(account_path, "a", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["username", "password"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if needs_header:
            writer.writeheader()
        writer.writerow({"username": username, "password": _hash_password(password)})
    _active_users.add(username)
    _ensure_scoreboard_user(username)
    return True

def login(username, password):
    """
    Log in to an existing user account.

    Args:
        username (str): The username of the account.
        password (str): The password of the account.

    Returns:
        bool: True if the login was successful, False otherwise.
    """
    cleanup_deleted_account_data()
    account_path = Path("accounts.csv")
    if not account_path.exists():
        return False
    with open(account_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row["username"] == username and _verify_password(
                password, row["password"]
            ):
                _active_users.add(username)
                _ensure_scoreboard_user(username)
                return True
    return False


def is_logged_in(username):
    """Return whether the account has an active session in this process."""
    return username in _active_users


def logout(username):
    """End the account's active session without changing its saved score."""
    if username not in _active_users:
        return False
    _active_users.remove(username)
    return True

def choose_save_file(username):
    """
    Allow the user to choose a save file.

    Args:
        username (str): The username of the account.

    Returns:
        str or None: The selected save path, or None if selection is cancelled.
    """
    if not isinstance(username, str) or not username.strip():
        return None

    account_usernames = _get_account_usernames()
    if account_usernames is None:
        return None
    if username not in account_usernames:
        _remove_deleted_account_data(account_usernames)
        return None

    save_paths = _get_save_paths(username)
    save_paths[0].parent.mkdir(parents=True, exist_ok=True)
    print(f"Save slots for {username}:")
    for slot_number, save_path in enumerate(save_paths, start=1):
        status = "Saved" if save_path.is_file() else "Empty"
        print(f"{slot_number}. Slot {slot_number} ({status})")

    while True:
        try:
            selection = input("Choose a slot (1-4), or press Enter to cancel: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not selection:
            return None
        if selection.isdigit() and 1 <= int(selection) <= SAVE_SLOT_COUNT:
            return str(save_paths[int(selection) - 1])
        print(f"Enter a number from 1 to {SAVE_SLOT_COUNT}, or press Enter to cancel.")

def continue_game(username, save_file):
    """
    Continue the game using the specified save file.

    Args:
        username (str): The username of the account.
        save_file (str): The path to the save file to continue from.

    Returns:
        dict or None: The loaded game state, or None if the save is missing or invalid.
    """
    if not isinstance(username, str) or not username.strip() or not save_file:
        return None
    account_usernames = _get_account_usernames()
    if account_usernames is None:
        return None
    if username not in account_usernames:
        _remove_deleted_account_data(account_usernames)
        return None

    try:
        with open(save_file, encoding="utf-8") as json_file:
            game_state = json.load(json_file)
    except (OSError, TypeError, ValueError):
        return None

    return game_state if isinstance(game_state, dict) else None

def save_game(username, save_file, game_state):
    """
    Save the current game state to the specified save file.

    Args:
        username (str): The username of the account.
        save_file (str): The path to the save file to save to.
        game_state (dict): The current state of the game to be saved.

    Returns:
        bool: True if the game was saved successfully, False otherwise.
    """
    if (
        not isinstance(game_state, dict)
        or not save_file
        or not isinstance(username, str)
        or not username.strip()
    ):
        return False
    account_usernames = _get_account_usernames()
    if account_usernames is None:
        return False
    if username not in account_usernames:
        _remove_deleted_account_data(account_usernames)
        return False

    xp = game_state.get("xp")
    if xp is not None and (
        not isinstance(xp, int) or isinstance(xp, bool) or xp < 0
    ):
        return False

    save_path = Path(save_file)
    temporary_path = save_path.with_name(save_path.name + ".tmp")
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temporary_path, "w", encoding="utf-8") as json_file:
            json.dump(game_state, json_file, indent=2, allow_nan=False)
            json_file.write("\n")
        temporary_path.replace(save_path)
    except (OSError, TypeError, ValueError):
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        return False

    if xp is None:
        _ensure_scoreboard_user(username)
    else:
        update_scoreboard(username, xp)
    return True
