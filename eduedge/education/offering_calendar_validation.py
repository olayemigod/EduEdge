from __future__ import annotations

from eduedge.services.academic_calendar import assert_institution_calendar_context


IDENTITY_FIELDS = ("school_branch", "academic_year", "academic_term")


def validate_programme_offering_calendar(doc, method=None) -> None:
	"""Require a configured Institution Session for period and year-wide Offerings."""
	if not doc.school_branch or not doc.academic_year:
		return
	context_changed = doc.is_new() or any(doc.has_value_changed(fieldname) for fieldname in IDENTITY_FIELDS)
	if not context_changed:
		# Keep unrelated edits to legacy records backward compatible.
		return
	assert_institution_calendar_context(
		branch=doc.school_branch,
		academic_year=doc.academic_year,
		academic_term=doc.academic_term or None,
	)
