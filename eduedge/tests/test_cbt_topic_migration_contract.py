from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TestCBTTopicMigrationContract(unittest.TestCase):
	def test_legacy_question_topics_are_migrated_to_course_topics(self):
		patches = (ROOT / "eduedge" / "patches.txt").read_text()
		patch = (
			ROOT
			/ "eduedge"
			/ "patches"
			/ "v0_8"
			/ "backfill_cbt_question_topics.py"
		).read_text()
		self.assertIn("backfill_cbt_question_topics", patches)
		self.assertIn('frappe.db.get_value("Topic", {"topic_name": legacy_topic}', patch)
		self.assertIn('"doctype": "Topic"', patch)
		self.assertIn('course_doc.append("topics", {"topic": topic})', patch)
		self.assertIn("update_modified=False", patch)


if __name__ == "__main__":
	unittest.main()
