from __future__ import annotations

import frappe

from eduedge import __version__
from eduedge.platform.config import get_platform_config
from eduedge.product_identity import resolve_product_identity


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

	current_academic_year = _single_value("Education Settings", "current_academic_year")
	current_academic_term = _single_value("Education Settings", "current_academic_term")
	if not current_academic_year:
		warnings.append("No current Academic Year is configured.")
	if not current_academic_term:
		warnings.append("No current Academic Term is configured.")

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
			current_academic_year=current_academic_year,
		),
	}


def _recommended_actions(**state) -> list[dict]:
	actions: list[dict] = []
	if not state["default_company"]:
		actions.append({"label": "Configure EduEdge Settings", "route": "/app/eduedge-settings"})
	if not state["branch_count"]:
		actions.append({"label": "Create School Branch", "route": "/app/eduedge-school-branch/new"})
	elif not state["default_branch"]:
		actions.append({"label": "Select Default School Branch", "route": "/app/eduedge-settings"})
	if not state["current_academic_year"]:
		actions.append({"label": "Configure Education Settings", "route": "/app/education-settings"})
	return actions
