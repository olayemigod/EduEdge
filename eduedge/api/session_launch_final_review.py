from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from eduedge.api.session_launch import LAUNCH_DOCTYPE, _get_launch_by_name, _require_manager
from eduedge.api.session_launch_operational_readiness import (
	STATUS_ATTENTION,
	STATUS_BLOCKED,
	get_session_launch_operational_readiness,
)


ACTIVATION_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}
MIN_WARNING_ACK_LENGTH = 10


def _normalise(value: Any) -> str:
	return " ".join(str(value or "").split())


def _can_activate() -> bool:
	if frappe.session.user == "Administrator":
		return True
	return bool(ACTIVATION_ROLES.intersection(set(frappe.get_roles())))


def _require_activation_permission() -> None:
	_require_manager("activate_session_launch")
	if not _can_activate():
		frappe.throw(
			_("Only an authorised Academic Administrator can activate an Academic Session."),
			frappe.PermissionError,
		)


def _previous_active(doc) -> dict | None:
	row = frappe.db.get_value(
		LAUNCH_DOCTYPE,
		{"institution": doc.institution, "status": "Active", "name": ["!=", doc.name]},
		["name", "academic_year", "activated_by", "activated_on"],
		as_dict=True,
	)
	return dict(row) if row else None


def _launch_audit(doc) -> dict:
	return {
		"status": doc.status,
		"current_step_key": doc.current_step_key,
		"current_step_label": doc.current_step_label,
		"ready_by": doc.get("ready_by") or "",
		"ready_on": str(doc.get("ready_on") or ""),
		"activated_by": doc.get("activated_by") or "",
		"activated_on": str(doc.get("activated_on") or ""),
		"previous_active_launch": doc.get("previous_active_launch") or "",
		"previous_active_academic_year": doc.get("previous_active_academic_year") or "",
		"warning_acknowledgement": doc.get("warning_acknowledgement") or "",
		"readiness_snapshot_hash": doc.get("readiness_snapshot_hash") or "",
	}


def _context(doc, readiness: dict | None = None) -> dict:
	readiness = readiness or get_session_launch_operational_readiness(doc.name)
	blocked = [row for row in readiness.get("categories") or [] if row.get("status") == STATUS_BLOCKED]
	warnings = [row for row in readiness.get("categories") or [] if row.get("status") == STATUS_ATTENTION]
	previous = _previous_active(doc)
	can_activate = _can_activate()
	already_active = doc.status == "Active"
	return {
		"launch": doc.name,
		"institution": doc.institution,
		"academic_year": doc.academic_year,
		"source_academic_year": doc.source_academic_year or "",
		"status": doc.status,
		"readiness": readiness,
		"previous_active": previous,
		"permissions": {"can_activate": can_activate},
		"activation": {
			"allowed": bool(can_activate and not blocked and doc.status not in {"Active", "Closed"}),
			"already_active": already_active,
			"hard_blockers": len(blocked),
			"warnings": len(warnings),
			"warning_acknowledgement_required": bool(warnings),
			"message": (
				_("This Academic Session is already active.")
				if already_active
				else _("Resolve all hard blockers before activation.")
				if blocked
				else _("Review and acknowledge non-blocking warnings before activation.")
				if warnings
				else _("The Session is ready for activation.")
			),
		},
		"audit": _launch_audit(doc),
	}


def _canonical_snapshot(readiness: dict, *, doc, previous: dict | None, warning_acknowledgement: str, generated_on) -> tuple[str, str]:
	snapshot = {
		"schema_version": 1,
		"launch": doc.name,
		"institution": doc.institution,
		"academic_year": doc.academic_year,
		"source_academic_year": doc.source_academic_year or "",
		"generated_by": frappe.session.user,
		"generated_on": str(generated_on),
		"warning_acknowledgement": warning_acknowledgement,
		"previous_active": previous or {},
		"readiness": readiness,
	}
	text = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
	return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _lock_institution(institution: str) -> None:
	# Locking the Institution serialises activation even when no previous Active launch exists.
	frappe.db.sql(
		"select name from `tabEduEdge Institution` where name = %s for update",
		(institution,),
	)


def _close_previous_active(previous: dict | None, closed_on) -> None:
	if not previous:
		return
	previous_doc = frappe.get_doc(LAUNCH_DOCTYPE, previous["name"])
	if previous_doc.status != "Active":
		return
	previous_doc.status = "Closed"
	previous_doc.closed_on = closed_on
	previous_doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_session_launch_final_review(launch: str) -> dict:
	_require_manager("get_session_launch_final_review")
	doc = _get_launch_by_name(_normalise(launch))
	doc.check_permission("read")
	return _context(doc)


@frappe.whitelist(methods=["POST"])
def activate_session_launch(launch: str, warning_acknowledgement: str | None = None) -> dict:
	"""Activate one Session Launch from a fresh, immutable readiness snapshot.

	Hard blockers can never be overridden. Non-blocking warnings require an explicit
	acknowledgement which becomes part of the hashed activation evidence. The
	Institution row is locked so concurrent activation attempts cannot create two
	active Session Launches for the same Institution.
	"""
	_require_activation_permission()
	name = _normalise(launch)
	doc = _get_launch_by_name(name)
	if doc.status == "Closed":
		frappe.throw(_("A closed Session Launch cannot be activated."), frappe.ValidationError)
	if doc.status == "Active":
		return {"status": "Already Active", "context": _context(doc)}

	_lock_institution(doc.institution)
	doc = frappe.get_doc(LAUNCH_DOCTYPE, name)
	if doc.status == "Closed":
		frappe.throw(_("A closed Session Launch cannot be activated."), frappe.ValidationError)
	if doc.status == "Active":
		return {"status": "Already Active", "context": _context(doc)}

	readiness = get_session_launch_operational_readiness(doc.name)
	blocked = [row for row in readiness.get("categories") or [] if row.get("status") == STATUS_BLOCKED]
	warnings = [row for row in readiness.get("categories") or [] if row.get("status") == STATUS_ATTENTION]
	if blocked:
		labels = ", ".join(row.get("label") or row.get("key") for row in blocked[:8])
		frappe.throw(
			_("Session activation is blocked by: {0}.").format(labels),
			frappe.ValidationError,
		)

	acknowledgement = _normalise(warning_acknowledgement)
	if warnings and len(acknowledgement) < MIN_WARNING_ACK_LENGTH:
		frappe.throw(
			_("Enter a meaningful warning acknowledgement before activating with readiness warnings."),
			frappe.ValidationError,
		)

	activated_on = now_datetime()
	previous = _previous_active(doc)
	snapshot_text, snapshot_hash = _canonical_snapshot(
		readiness,
		doc=doc,
		previous=previous,
		warning_acknowledgement=acknowledgement,
		generated_on=activated_on,
	)

	_close_previous_active(previous, activated_on)
	doc.status = "Active"
	doc.current_step_key = "final_review"
	doc.ready_by = frappe.session.user
	doc.ready_on = doc.ready_on or activated_on
	doc.activated_by = frappe.session.user
	doc.activated_on = activated_on
	doc.previous_active_launch = previous.get("name") if previous else None
	doc.previous_active_academic_year = previous.get("academic_year") if previous else None
	doc.warning_acknowledgement = acknowledgement
	doc.readiness_snapshot_hash = snapshot_hash
	doc.readiness_snapshot = snapshot_text
	doc.save(ignore_permissions=True)

	return {
		"status": "Activated",
		"snapshot_hash": snapshot_hash,
		"previous_active": previous,
		"context": _context(doc, readiness=readiness),
	}
