import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "eduedge" / "public" / "js" / "eduedge_question_batch.bundle.js"


class TestQuestionBatchNewestFirstIntegratedContract(unittest.TestCase):
	def test_original_component_method_is_overridden_without_wrapper(self):
		bundle = BUNDLE.read_text()
		self.assertIn("const originalAddQuestion = EduEdgeQuestionBatch.methods?.addQuestion", bundle)
		self.assertIn("EduEdgeQuestionBatch.methods.addQuestion", bundle)
		self.assertIn("const newest = this.questions.pop()", bundle)
		self.assertIn("this.questions.unshift(newest)", bundle)
		self.assertIn("this.$nextTick", bundle)
		self.assertIn("?.focus()", bundle)
		self.assertNotIn("extends: EduEdgeQuestionBatch", bundle)
		self.assertNotIn("app.mount =", bundle)


if __name__ == "__main__":
	unittest.main()
