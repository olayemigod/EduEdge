from __future__ import annotations

from eduedge.education import academic_validation
from eduedge.education.academic_fields import OFFERING_FIELD


def before_validate_fee_schedule(doc, method=None) -> None:
	selected_offering = doc.get(OFFERING_FIELD) if doc.meta.has_field(OFFERING_FIELD) else None
	academic_validation.before_validate_fee_schedule(doc, method)
	# The base resolver clears stale derived context before rebuilding it. Preserve
	# the user's explicit Offering source so the Fee Schedule remains auditable.
	if selected_offering and doc.meta.has_field(OFFERING_FIELD):
		doc.set(OFFERING_FIELD, selected_offering)
