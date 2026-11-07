import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from AreaMusic import AreaMusicPlayer


class AreaMusicPlayerTest(unittest.TestCase):
	def setUp(self):
		self.temporary_directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.temporary_directory.cleanup)
		self.music_directory = Path(self.temporary_directory.name)
		self.track_path = self.music_directory / "area_1.ogg"
		self.track_path.touch()

	def test_plays_area_track_on_loop(self):
		pygame = Mock()
		pygame.error = RuntimeError
		pygame.mixer.get_init.return_value = True

		with patch.dict("sys.modules", {"pygame": pygame}):
			player = AreaMusicPlayer(self.music_directory)
			player.play_area(1)

		pygame.mixer.music.load.assert_called_once_with(str(self.track_path))
		pygame.mixer.music.play.assert_called_once_with(-1)
		pygame.mixer.music.stop.assert_not_called()

	def test_does_not_restart_track_for_same_area(self):
		pygame = Mock()
		pygame.error = RuntimeError
		pygame.mixer.get_init.return_value = True

		with patch.dict("sys.modules", {"pygame": pygame}):
			player = AreaMusicPlayer(self.music_directory)
			player.play_area(1)
			player.play_area(1)

		pygame.mixer.music.play.assert_called_once_with(-1)

	def test_switches_track_when_area_changes(self):
		area_two_track = self.music_directory / "area_2.ogg"
		area_two_track.touch()
		pygame = Mock()
		pygame.error = RuntimeError
		pygame.mixer.get_init.return_value = True

		with patch.dict("sys.modules", {"pygame": pygame}):
			player = AreaMusicPlayer(self.music_directory)
			player.play_area(1)
			player.play_area(2)

		self.assertEqual(
			[call.args[0] for call in pygame.mixer.music.load.call_args_list],
			[str(self.track_path), str(area_two_track)],
		)
		self.assertEqual(pygame.mixer.music.play.call_count, 2)
		pygame.mixer.music.stop.assert_called_once()

	def test_missing_track_is_reported(self):
		player = AreaMusicPlayer(self.music_directory)
		output = io.StringIO()

		with contextlib.redirect_stdout(output):
			player.play_area(2)

		self.assertIn("Background music file not found", output.getvalue())

	def test_stop_stops_playback(self):
		pygame = Mock()
		pygame.error = RuntimeError
		pygame.mixer.get_init.return_value = True

		with patch.dict("sys.modules", {"pygame": pygame}):
			player = AreaMusicPlayer(self.music_directory)
			player.play_area(1)
			player.stop()

		pygame.mixer.music.stop.assert_called_once()
		self.assertIsNone(player._current_area)


if __name__ == "__main__":
	unittest.main()
