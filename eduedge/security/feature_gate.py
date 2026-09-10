from __future__ import annotations

from collections.abc import Callable
from functools import wraps

import frappe
from frappe import _
from frappe.utils import cint


FEATURE_SETTINGS = {
	"cbt": ("enable_cbt", True),
	"student_pickup": ("enable_student_pickup", False),
	"school_intelligence": ("enable_school_intelligence", True),
	"edgefinder_publication": ("enable_edgefinder_publication", False),
}

FEATURE_COMMAND_PREFIXES = {
	"cbt": (
		"eduedge.cbt.",
		"eduedge.api.cbt_",
	),
}

FEATURE_ROUTE_PREFIXES = {
	"cbt": (
		"/app/eduedge-cbt-",
		"/app/eduedge-question-",
		"/app/eduedge-exam-template",
	),
}


def is_feature_enabled(feature: str) -> bool:
	fieldname, default = FEATURE_SETTINGS.get(feature, ("", False))
	if not fieldname:
		return False
	try:
		if not frappe.db.exists("DocType", "EduEdge Settings"):
			return bool(default)
		meta = frappe.get_meta("EduEdge Settings")
		if not meta.has_field(fieldname):
			return bool(default)
		value = frappe.db.get_single_value("EduEdge Settings", fieldname)
		return bool(default if value is None else cint(value))
	except Exception:
		return bool(default)


def feature_for_command(command: str) -> str | None:
	value = str(command or "").strip()
	for feature, prefixes in FEATURE_COMMAND_PREFIXES.items():
		if value.startswith(prefixes):
			return feature
	return None


def feature_for_route(route: str) -> str | None:
	value = str(route or "").strip().lower()
	for feature, prefixes in FEATURE_ROUTE_PREFIXES.items():
		if value.startswith(prefixes):
			return feature
	return None


def require_feature(feature: str) -> None:
	if is_feature_enabled(feature):
		return
	frappe.throw(
		_("This EduEdge feature is not enabled for the current site."),
		frappe.PermissionError,
		title=_("Feature Not Enabled"),
	)


def enforce_feature_for_command(command: str) -> None:
	feature = feature_for_command(command)
	if feature:
		require_feature(feature)


def feature_guard(feature: str) -> Callable:
	def decorator(function: Callable) -> Callable:
		@wraps(function)
		def wrapped(*args, **kwargs):
			require_feature(feature)
			return function(*args, **kwargs)

		return wrapped

	return decorator


def run_cbt_expiry_job() -> None:
	"""Scheduler-safe CBT expiry wrapper that becomes a no-op when CBT is disabled."""
	if not is_feature_enabled("cbt"):
		return
	from eduedge.cbt.attempts import finalize_expired_attempts

	finalize_expired_attempts()
