from __future__ import annotations

import frappe
from frappe import _

from eduedge.platform.access import get_eduedge_capability_decision
from eduedge.platform.config import get_platform_config, parse_bool

PUBLIC_EXAM_FEATURE = "cbt_public_exam"
PUBLIC_EXAM_ACTIONS = (
	"catalog",
	"assign",
	"host",
	"launch",
	"results",
	"author",
)
PUBLIC_EXAM_AUTHOR_ROLES = {
	"EduEdge Super Administrator",
	"EduEdge Public Exam Administrator",
}


def is_public_exam_authority_site() -> bool:
	"""Return whether this site is an approved ProcessEdge public-exam authority.

	This server-side flag is intended only for the centrally operated EduEdge
	Exam Service (and controlled development sites). Tenant and white-label sites
	must not set it merely because they have a local Administrator or System
	Manager.
	"""
	return parse_bool(frappe.conf.get("eduedge_public_exam_authority"), default=False)


def get_public_exam_access_decision(
	action: str,
	*,
	user: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> dict:
	action = str(action or "").strip().lower()
	if action not in PUBLIC_EXAM_ACTIONS:
		frappe.throw(_("Select a valid EduEdge public examination capability."), frappe.ValidationError)

	resolved_user = user or frappe.session.user
	if is_public_exam_authority_site():
		return {
			"allowed": True,
			"enforcement_action": "Allow",
			"primary_reason_code": "PUBLIC_EXAM_AUTHORITY_SITE",
			"reason": _("This site is configured as the ProcessEdge public examination authority."),
			"platform_mode": get_platform_config().mode,
			"feature_key": PUBLIC_EXAM_FEATURE,
			"action": action,
		}

	config = get_platform_config()
	if config.remote_enabled:
		decision = get_eduedge_capability_decision(
			user=resolved_user,
			feature_key=PUBLIC_EXAM_FEATURE,
			action=action,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
		return {**decision, "action": action}

	return {
		"allowed": False,
		"enforcement_action": "Block",
		"primary_reason_code": "PUBLIC_EXAM_ACCESS_NOT_ACTIVATED",
		"reason": _(
			"EduEdge public examination access is not activated for this site. "
			"Connect the site to CoreEdge and activate the required capability."
		),
		"platform_mode": config.mode,
		"feature_key": PUBLIC_EXAM_FEATURE,
		"action": action,
	}


def has_public_exam_capability(action: str, *, user: str | None = None) -> bool:
	return bool(get_public_exam_access_decision(action, user=user).get("allowed"))


def has_public_exam_author_role(user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	if resolved_user == "Guest":
		return False
	if resolved_user == "Administrator":
		# Administrator is accepted as a technical bootstrap identity only when
		# the site itself is authorised or CoreEdge explicitly grants authoring.
		return True
	return bool(set(frappe.get_roles(resolved_user)).intersection(PUBLIC_EXAM_AUTHOR_ROLES))


def can_author_public_exams(user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	return has_public_exam_author_role(resolved_user) and has_public_exam_capability(
		"author", user=resolved_user
	)


def require_public_exam_capability(
	action: str,
	*,
	user: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> dict:
	decision = get_public_exam_access_decision(
		action,
		user=user,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
	)
	if not decision.get("allowed"):
		frappe.throw(
			decision.get("reason") or _("EduEdge public examination access is not available."),
			frappe.PermissionError,
			title=_("Public Examination Access Required"),
		)
	return decision


def require_public_exam_authoring(user: str | None = None) -> dict:
	resolved_user = user or frappe.session.user
	decision = require_public_exam_capability("author", user=resolved_user)
	if not has_public_exam_author_role(resolved_user):
		frappe.throw(
			_("Only an authorised ProcessEdge public examination administrator can manage public examination masters."),
			frappe.PermissionError,
			title=_("Public Examination Authoring Restricted"),
		)
	return decision


def get_public_exam_capability_summary(user: str | None = None) -> dict:
	resolved_user = user or frappe.session.user
	result = {}
	for action in PUBLIC_EXAM_ACTIONS:
		decision = get_public_exam_access_decision(action, user=resolved_user)
		allowed = bool(decision.get("allowed"))
		if action == "author":
			allowed = allowed and has_public_exam_author_role(resolved_user)
		result[action] = {
			"allowed": allowed,
			"reason_code": decision.get("primary_reason_code"),
			"reason": decision.get("reason") or "",
			"cached": bool(decision.get("cached")),
		}
	return {
		"feature_key": PUBLIC_EXAM_FEATURE,
		"authority_site": is_public_exam_authority_site(),
		"platform_mode": get_platform_config().mode,
		"capabilities": result,
	}
