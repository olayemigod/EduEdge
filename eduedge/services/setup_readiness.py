from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate

from eduedge import __version__
from eduedge.platform.config import get_platform_config
from eduedge.product_identity import resolve_product_identity
from eduedge.services.branch_accounting import ACCOUNTING_FIELDS, get_missing_core_defaults
from eduedge.services.branch_context import is_branch_access_enforced


def _single_value(doctype: str, fieldname: str):
	if not frappe.db.exists("DocType", doctype):
		return None
	meta = frappe.get_meta(doctype)
	if not meta.has_field(fieldname):
		return None
	return frappe.db.get_single_value(doctype, fieldname)


def get_setup_readiness() -> dict:
	installed_apps = set(frappe.get_installed_apps())
	config = get_platform_config()
	platform = config.sanitized()
	blockers = list(platform.get("blockers") or [])
	warnings = list(platform.get("warnings") or [])

	default_company = frappe.db.get_single_value("EduEdge Settings", "default_company")
	default_branch = frappe.db.get_single_value("EduEdge Settings", "default_school_branch")
	branch_count = frappe.db.count("EduEdge School Branch", {"enabled": 1})
	program_offering_count = (
		frappe.db.count("EduEdge Program Offering", {"is_active": 1})
		if frappe.db.exists("DocType", "EduEdge Program Offering")
		else 0
	)
	branch_access_count = _active_branch_access_count()
	enforcement_enabled = is_branch_access_enforced()
	accounting_ready_count = _accounting_ready_count()

	if "education" not in installed_apps:
		blockers.append("Frappe Education is not installed.")
	if "edgesuite_ui" not in installed_apps:
		blockers.append("EdgeSuite UI is not installed.")
	if not default_company:
		blockers.append("No default Company is configured in EduEdge Settings.")
	if not branch_count:
		blockers.append("No enabled School Branch has been configured.")
	elif not default_branch:
		warnings.append("No default School Branch has been selected.")

	if enforcement_enabled and not branch_access_count:
		blockers.append("User Branch Access enforcement is enabled but no active assignments exist.")
	elif not enforcement_enabled:
		warnings.append(
			"User Branch Access enforcement is disabled. Configure and review assignments before activation."
		)
	if branch_count and accounting_ready_count < branch_count:
		warnings.append(
			f"{branch_count - accounting_ready_count} enabled School Branch record(s) are missing core accounting defaults."
		)

	current_academic_year = _single_value("Education Settings", "current_academic_year")
	current_academic_term = _single_value("Education Settings", "current_academic_term")
	if not current_academic_year:
		warnings.append("No current Academic Year is configured.")
	if not current_academic_term:
		warnings.append("No current Academic Term is configured.")
	if branch_count and current_academic_year and not program_offering_count:
		warnings.append(
			"No active Program Offering has been configured for branch-aware admissions and enrollment."
		)

	settings = frappe.get_single("EduEdge Settings")
	return {
		"application": {
			**resolve_product_identity(),
			"version": __version__,
		},
		"dependencies": {
			"frappe": "frappe" in installed_apps,
			"erpnext": "erpnext" in installed_apps,
			"education": "education" in installed_apps,
			"edgesuite_ui": "edgesuite_ui" in installed_apps,
		},
		"platform": platform,
		"school": {
			"default_company": default_company,
			"default_school_branch": default_branch,
			"enabled_branch_count": branch_count,
			"active_program_offering_count": program_offering_count,
			"active_branch_access_count": branch_access_count,
			"branch_access_enforcement_enabled": enforcement_enabled,
			"accounting_ready_branch_count": accounting_ready_count,
			"current_academic_year": current_academic_year,
			"current_academic_term": current_academic_term,
		},
		"features": {
			"cbt": bool(settings.enable_cbt),
			"student_pickup": bool(settings.enable_student_pickup),
			"school_intelligence": bool(settings.enable_school_intelligence),
			"edgefinder_publication": bool(settings.enable_edgefinder_publication),
		},
		"ready": not blockers,
		"blockers": blockers,
		"warnings": warnings,
		"recommended_actions": _recommended_actions(
			default_company=default_company,
			branch_count=branch_count,
			default_branch=default_branch,
			branch_access_count=branch_access_count,
			enforcement_enabled=enforcement_enabled,
			accounting_ready_count=accounting_ready_count,
			current_academic_year=current_academic_year,
			program_offering_count=program_offering_count,
		),
	}


def _active_branch_access_count() -> int:
	if not frappe.db.exists("DocType", "EduEdge User Branch Access"):
		return 0
	rows = frappe.get_all(
		"EduEdge User Branch Access",
		filters={"enabled": 1},
		fields=["valid_from", "valid_to"],
	)
	today = getdate(nowdate())
	return sum(
		1
		for row in rows
		if (not row.valid_from or getdate(row.valid_from) <= today)
		and (not row.valid_to or getdate(row.valid_to) >= today)
	)


def _accounting_ready_count() -> int:
	if not frappe.db.exists("DocType", "EduEdge School Branch"):
		return 0
	meta = frappe.get_meta("EduEdge School Branch")
	available_fields = [fieldname for fieldname in ACCOUNTING_FIELDS if meta.has_field(fieldname)]
	core_fields = {"cost_center", "school_fees_income_account", "default_receivable_account"}
	if not core_fields.issubset(set(available_fields)):
		return 0
	rows = frappe.get_all(
		"EduEdge School Branch",
		filters={"enabled": 1},
		fields=["name", *available_fields],
	)
	return sum(1 for row in rows if not get_missing_core_defaults(row))


def _recommended_actions(**state) -> list[dict]:
	actions: list[dict] = []
	if not state["default_company"]:
		actions.append({"label": "Configure EduEdge Settings", "route": "/app/eduedge-settings"})
	if not state["branch_count"]:
		actions.append({"label": "Create School Branch", "route": "/app/eduedge-school-branch/new"})
	elif not state["default_branch"]:
		actions.append({"label": "Select Default School Branch", "route": "/app/eduedge-settings"})
	if not state["branch_access_count"]:
		actions.append({"label": "Configure User Branch Access", "route": "/app/eduedge-user-branch-access"})
	elif not state["enforcement_enabled"]:
		actions.append({"label": "Review and Enable Branch Enforcement", "route": "/app/eduedge-settings"})
	if state["branch_count"] and state["accounting_ready_count"] < state["branch_count"]:
		actions.append({"label": "Complete Branch Accounting Defaults", "route": "/app/eduedge-school-branch"})
	if not state["current_academic_year"]:
		actions.append({"label": "Configure Education Settings", "route": "/app/education-settings"})
	if (
		state["branch_count"]
		and state["current_academic_year"]
		and not state["program_offering_count"]
	):
		actions.append(
			{
				"label": "Create Program Offering",
				"route": "/app/eduedge-program-offering/new",
			}
		)
	return actions
