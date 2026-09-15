from __future__ import annotations

import frappe
from frappe import _

ISSUE_DOCTYPE = "EduEdge Report Card Issue"


def notify_report_card_recipients(issue_name: str) -> list[str]:
	"""Create privacy-safe in-app notices for the Student and verified Guardians.

	Marks are deliberately not copied into Notification Log. Recipients must open
	the authenticated My Results portal where relationship checks are enforced.
	"""
	issue = frappe.db.get_value(
		ISSUE_DOCTYPE,
		issue_name,
		["name", "student", "student_name"],
		as_dict=True,
	)
	if not issue:
		return []

	recipients = _result_recipient_users(issue.student)
	created = []
	for user in recipients:
		if frappe.db.exists(
			"Notification Log",
			{
				"for_user": user,
				"document_type": ISSUE_DOCTYPE,
				"document_name": issue.name,
			},
		):
			continue
		try:
			log = frappe.get_doc(
				{
					"doctype": "Notification Log",
					"title": _("A new school result is available"),
					"description": _("An approved report card is available in My Results."),
					"document_type": ISSUE_DOCTYPE,
					"document_name": issue.name,
					"source_doctype": ISSUE_DOCTYPE,
					"source_name": issue.name,
					"app": "eduedge",
					"link": "/eduedge-results",
					"for_user": user,
					"from_user": frappe.session.user,
					"read": 0,
				}
			)
			log.insert(ignore_permissions=True)
			created.append(log.name)
		except Exception:
			frappe.log_error(
				title="EduEdge result notification failed",
				message=frappe.get_traceback(),
			)
	return created


def _result_recipient_users(student: str) -> list[str]:
	users: set[str] = set()
	student_user = frappe.db.get_value("Student", student, "user")
	if student_user:
		users.add(student_user)

	guardian_names = frappe.get_all(
		"Student Guardian",
		filters={
			"parent": student,
			"parenttype": "Student",
			"parentfield": "guardians",
		},
		pluck="guardian",
	)
	if guardian_names:
		users.update(
			user
			for user in frappe.get_all(
				"Guardian",
				filters={"name": ["in", guardian_names], "user": ["is", "set"]},
				pluck="user",
			)
			if user
		)

	if not users:
		return []
	enabled = set(
		frappe.get_all(
			"User",
			filters={"name": ["in", sorted(users)], "enabled": 1},
			pluck="name",
		)
	)
	return sorted(enabled)
