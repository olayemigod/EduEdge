"""Cross-cutting EduEdge request and data security controls."""


def _install_authority_compatibility() -> None:
	"""Keep the platform-manager role consistent in legacy authority modules.

	Branch context predates the shared EduEdge permission baseline and originally
	listed only System Manager and EduEdge Administrator. The compatibility hook
	is intentionally additive: it grants no DocType permission and only makes the
	existing Super Administrator role follow the same platform-level context path.
	"""
	try:
		from eduedge.services import branch_context

		branch_context.PRIVILEGED_ROLES.add("EduEdge Super Administrator")
	except Exception:
		# Frappe may import this package during early installation before all
		# application modules are ready. Normal request imports retry naturally.
		return


_install_authority_compatibility()
