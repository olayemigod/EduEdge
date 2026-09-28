from __future__ import annotations

from frappe.model.document import Document

from eduedge.education.result_profile import validate_result_profile


class EduEdgeResultProfile(Document):
	def validate(self) -> None:
		validate_result_profile(self)
