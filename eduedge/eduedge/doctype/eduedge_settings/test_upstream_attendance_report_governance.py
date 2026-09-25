from __future__ import annotations

import frappe
from frappe.core.doctype.custom_role.custom_role import get_custom_allowed_roles
from frappe.tests.utils import FrappeTestCase

from eduedge.education.upstream_report_governance import (
	RAW_SQL_ATTENDANCE_REPORTS,
	SAFE_REPORT_ROLES,
	ensure_safe_attendance_report_roles,
)


class TestUpstreamAttendanceReportGovernance(FrappeTestCase):
	def test_raw_sql_attendance_reports_are_platform_admin_only_and_idempotent(self):
		ensure_safe_attendance_report_roles()
		expected = {
			role
			for role in SAFE_REPORT_ROLES
			if frappe.db.exists("Role", role)
		}

		for report_name in RAW_SQL_ATTENDANCE_REPORTS:
			if not frappe.db.exists("Report", report_name):
				continue
			self.assertEqual(
				set(get_custom_allowed_roles("report", report_name)),
				expected,
			)

		second = ensure_safe_attendance_report_roles()
		self.assertEqual(second["changed_reports"], [])
