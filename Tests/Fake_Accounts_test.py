import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import Accounts

class FakeAccountIntegrityTest(unittest.TestCase):
	def setUp(self):
		self.original_directory = Path.cwd()
		self.temporary_directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.temporary_directory.cleanup)
		os.chdir(self.temporary_directory.name)
		self.addCleanup(os.chdir, self.original_directory)

		self.scoreboard_patcher = patch.object(
			Accounts,
			"SCOREBOARD_PATH",
			Path(self.temporary_directory.name) / "Scoreboard.csv",
		)
		self.scoreboard_patcher.start()
		self.addCleanup(self.scoreboard_patcher.stop)

		self.save_directory_patcher = patch.object(
			Accounts,
			"SAVE_DIRECTORY",
			Path(self.temporary_directory.name) / "Saves",
		)
		self.save_directory_patcher.start()
		self.addCleanup(self.save_directory_patcher.stop)

	def _write_accounts(self, usernames):
		with open("accounts.csv", "w", newline="", encoding="utf-8") as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=("username", "password"))
			writer.writeheader()
			writer.writerows(
				{"username": username, "password": "stored-hash"}
				for username in usernames
			)

	def test_fake_account_login_scoreboard_and_logout(self):
		username = "Fake_Integrity_User"
		password = "test-password"
		self.addCleanup(Accounts.logout, username)

		self.assertTrue(Accounts.create_account(username, password))
		with open("accounts.csv", newline="", encoding="utf-8") as csv_file:
			account = next(csv.DictReader(csv_file))
		self.assertNotEqual(account["password"], password)
		self.assertTrue(account["password"].startswith("pbkdf2_sha256$"))
		self.assertTrue(Accounts.is_logged_in(username))
		self.assertTrue(Accounts.login(username, password))
		self.assertFalse(Accounts.login(username, "incorrect-password"))

		scoreboard = Accounts.get_scoreboard()
		self.assertEqual(scoreboard, [{"rank": 1, "username": username, "xp": 0}])

		Accounts.update_scoreboard(username, 1234)
		self.assertEqual(Accounts.get_scoreboard()[0]["xp"], 1234)

		self.assertTrue(Accounts.logout(username))
		self.assertFalse(Accounts.is_logged_in(username))
		self.assertFalse(Accounts.logout(username))
		self.assertEqual(Accounts.get_scoreboard()[0]["xp"], 1234)

	def test_create_account_accepts_an_empty_accounts_file(self):
		Path("accounts.csv").touch()

		self.assertTrue(Accounts.create_account("New_User", "test-password"))

	def test_cleanup_removes_deleted_accounts_saves_and_scores(self):
		registered_username = "Keep_Account"
		deleted_username = "Remove_Account"
		self._write_accounts([registered_username])

		for username in (registered_username, deleted_username):
			save_path = Accounts._get_save_paths(username)[0]
			save_path.parent.mkdir(parents=True, exist_ok=True)
			save_path.write_text("{}", encoding="utf-8")
			Accounts.update_scoreboard(username, 100)

		Accounts.cleanup_deleted_account_data()

		self.assertTrue(Accounts._get_save_paths(registered_username)[0].is_file())
		self.assertFalse(Accounts._get_save_paths(deleted_username)[0].parent.exists())
		self.assertEqual(
			Accounts.get_scoreboard(),
			[{"rank": 1, "username": registered_username, "xp": 100}],
		)

	def test_save_after_account_deletion_is_rejected_and_purged(self):
		username = "Deleted_During_Game"
		self._write_accounts([username])
		save_path = Accounts._get_save_paths(username)[0]
		self.assertTrue(
			Accounts.save_game(username, save_path, {"xp": 25, "level": 2})
		)

		self._write_accounts([])

		self.assertFalse(
			Accounts.save_game(username, save_path, {"xp": 50, "level": 3})
		)
		self.assertFalse(save_path.exists())
		self.assertEqual(Accounts.get_scoreboard(), [])


if __name__ == "__main__":
	unittest.main()
