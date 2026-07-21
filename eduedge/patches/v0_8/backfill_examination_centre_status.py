from __future__ import annotations

import frappe


def execute() -> None:
	if not frappe.db.table_exists("EduEdge Examination Centre"):
		return
	if not frappe.db.has_column("EduEdge Examination Centre", "centre_status"):
		return

	# Before V0.8A governance, `enabled` was the only centre lifecycle flag.
	# Preserve enabled centres as Active while leaving disabled records as Draft.
	# Records already changed through the new status workflow have an audit time
	# and are deliberately excluded so rerunning the patch is idempotent.
	frappe.db.sql(
		"""
		UPDATE `tabEduEdge Examination Centre`
		SET `centre_status` = CASE
			WHEN COALESCE(`enabled`, 0) = 1 THEN 'Active'
			ELSE 'Draft'
		END
		WHERE `status_changed_on` IS NULL
		"""
	)

	if frappe.db.has_column("EduEdge Examination Centre", "public_hosting_status"):
		# Existing centres predate public-hosting governance. Normalise the empty
		# state so an ordinary school-side edit is not mistaken for a protected
		# ProcessEdge status change on first save.
		frappe.db.sql(
			"""
			UPDATE `tabEduEdge Examination Centre`
			SET `public_hosting_status` = 'Not Requested'
			WHERE COALESCE(`public_hosting_status`, '') = ''
			"""
		)
