import unittest
from pathlib import Path
from RPG_Classes import get_class_stats, load_classes_from_csv

class ClassStatsCsvTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		classes_file = Path(__file__).resolve().parents[1] / "Files" / "Classes.csv"
		cls.classes = load_classes_from_csv(classes_file)

	def test_stats_are_parsed_for_every_csv_class(self):
		self.assertTrue(self.classes)
		for class_data in self.classes:
			with self.subTest(class_name=class_data["name"]):
				stats = get_class_stats(class_data["name"], self.classes)
				self.assertEqual(stats, class_data["stats"])
				self.assertTrue(stats)
				self.assertTrue(all(isinstance(value, int) for value in stats.values()))

	def test_unknown_class_returns_none(self):
		self.assertIsNone(get_class_stats("Unknown Program", self.classes))

if __name__ == "__main__":
	unittest.main()
