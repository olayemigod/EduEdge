"""Cross-cutting EduEdge request and data security controls."""


def _install_authority_compatibility() -> None:
	"""Keep platform authority and legacy HQ defaults consistently fail closed.

	This compatibility hook grants no DocType permission. It only aligns the
	existing Super Administrator role with other platform managers and ensures a
	missing or blank legacy HQ-view setting cannot silently enable all-branch view.
	"""
	try:
		import frappe
		from frappe.utils import cint

		from eduedge.services import branch_context

		branch_context.PRIVILEGED_ROLES.add("EduEdge Super Administrator")

		def safe_hq_all_branch_view_enabled() -> bool:
			meta = frappe.get_meta("EduEdge Settings")
			if not meta.has_field("allow_hq_all_branch_view"):
				return False
			value = frappe.db.get_single_value("EduEdge Settings", "allow_hq_all_branch_view")
			return bool(cint(value or 0))

		branch_context.is_hq_all_branch_view_enabled = safe_hq_all_branch_view_enabled
	except Exception:
		# Frappe may import this package during early installation before all
		# application modules are ready. Normal request imports retry naturally.
		return


_install_authority_compatibility()
