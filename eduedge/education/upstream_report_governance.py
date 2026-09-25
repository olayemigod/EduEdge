from __future__ import annotations

import frappe

from eduedge.permissions_baseline import PLATFORM_MANAGERS


RAW_SQL_ATTENDANCE_REPORTS = (
	"Absent Student Report",
	"Student Batch-Wise Attendance",
	"Student Monthly Attendance Sheet",
)
SAFE_REPORT_ROLES = PLATFORM_MANAGERS


def ensure_safe_attendance_report_roles() -> dict:
	"""Restrict upstream raw-SQL attendance reports to globally privileged roles.

	Frappe Education v16 implements these reports with direct SQL that does not
	consume EduEdge Branch/record permission conditions. Custom Role is Frappe's
	native override for standard Report role lists, so use it rather than editing
	upstream report JSON.
	"""
	if not frappe.db.exists("DocType", "Custom Role"):
		return {"changed_reports": [], "missing_reports": list(RAW_SQL_ATTENDANCE_REPORTS)}

	desired_roles = [
		role for role in SAFE_REPORT_ROLES
		if frappe.db.exists("Role", role)
	]
	changed_reports: list[str] = []
	missing_reports: list[str] = []

	for report_name in RAW_SQL_ATTENDANCE_REPORTS:
		if not frappe.db.exists("Report", report_name):
			missing_reports.append(report_name)
			continue

		custom_role_name = frappe.db.get_value(
			"Custom Role",
			{"report": report_name},
			"name",
		)
		doc = (
			frappe.get_doc("Custom Role", custom_role_name)
			if custom_role_name
			else frappe.new_doc("Custom Role")
		)
		current_roles = [row.role for row in doc.roles]
		if custom_role_name and current_roles == desired_roles:
			continue

		doc.report = report_name
		doc.set("roles", [])
		for role in desired_roles:
			doc.append("roles", {"role": role})
		if doc.is_new():
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)
		changed_reports.append(report_name)

	if changed_reports:
		frappe.clear_cache()

	return {
		"changed_reports": changed_reports,
		"missing_reports": missing_reports,
		"roles": desired_roles,
	}
