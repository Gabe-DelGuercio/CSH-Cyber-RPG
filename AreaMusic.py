"""Loop area-specific background music during gameplay."""
from pathlib import Path


MUSIC_DIRECTORY = Path(__file__).resolve().parent / "Music"


class AreaMusicPlayer:
	"""Play one looping OGG track for the player's current area."""

	def __init__(self, music_directory=MUSIC_DIRECTORY):
		self.music_directory = Path(music_directory)
		self._current_area = None
		self._pygame = None
		self._pygame_unavailable = False

	def play_area(self, area_number):
		"""Start the area's track, leaving the current track alone if unchanged."""
		if area_number == self._current_area:
			return

		if self._current_area is not None:
			self._stop_music()
		self._current_area = area_number
		track_path = self.music_directory / f"area_{area_number}.ogg"
		if not track_path.is_file():
			print(f"Background music file not found: {track_path}")
			return

		if self._pygame_unavailable:
			return
		if self._pygame is None:
			try:
				import pygame
			except ImportError as error:
				self._pygame_unavailable = True
				print(f"Background music is unavailable because pygame-ce could not be imported: {error}")
				return
			self._pygame = pygame

		try:
			if not self._pygame.mixer.get_init():
				self._pygame.mixer.init()
			self._pygame.mixer.music.load(str(track_path))
			self._pygame.mixer.music.play(-1)
		except self._pygame.error as error:
			self._stop_music()
			print(f"Could not play background music {track_path}: {error}")

	def stop(self):
		"""Stop the current track and clear the tracked area."""
		self._stop_music()
		self._current_area = None

	def _stop_music(self):
		if self._pygame is not None and self._pygame.mixer.get_init():
			self._pygame.mixer.music.stop()
