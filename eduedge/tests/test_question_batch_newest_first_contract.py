import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "eduedge" / "public" / "js" / "eduedge_question_batch.bundle.js"


class TestQuestionBatchNewestFirstContract(unittest.TestCase):
	def test_new_manual_question_is_moved_to_top_and_focused(self):
		bundle = BUNDLE.read_text()
		self.assertIn("const baseMethods = EduEdgeQuestionBatch.methods || {}", bundle)
		self.assertIn("const newest = this.questions.pop()", bundle)
		self.assertIn("this.questions.unshift(newest)", bundle)
		self.assertIn("this.$nextTick", bundle)
		self.assertIn('.querySelector(".eduedge-question-card input.form-control")', bundle)
		self.assertIn("?.focus()", bundle)
		self.assertNotIn("app.mount =", bundle)
		self.assertNotIn("MutationObserver", bundle)


if __name__ == "__main__":
	unittest.main()
