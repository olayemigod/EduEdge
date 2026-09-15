from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultScoreStateDisplayContract(unittest.TestCase):
	def test_result_components_preserve_non_numeric_academic_states(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn('component["status"] = _component_status(component)', engine)
		self.assertIn('component["status_code"] = _component_status_code', engine)
		self.assertIn('"Absent": "ABS"', engine)
		self.assertIn('"Exempt": "EX"', engine)
		self.assertIn('"Not Offered": "N/O"', engine)
		self.assertIn('"Missing": "-"', engine)

	def test_genuine_scored_zero_remains_scored_not_missing(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn('if state == "Scored":', engine)
		self.assertIn('component["states"].append("Scored")', engine)
		self.assertIn('return "Scored"', engine)

	def test_absence_treated_as_zero_still_remains_visibly_absent(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn('component["states"].append(state)', engine)
		self.assertIn('if states and all(state == "Absent" for state in states):', engine)
		self.assertIn('return "Absent"', engine)


if __name__ == "__main__":
	unittest.main()
