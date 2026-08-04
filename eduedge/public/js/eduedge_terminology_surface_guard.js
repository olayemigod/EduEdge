const EDGE_MANAGED_SURFACE_SELECTORS = [
	".edge-app-shell",
	".edge-sidebar",
	".edge-product-menu",
	".edge-product-menu__panel",
	".edge-product-menu-panel",
	"[data-edge-product-menu]",
].join(", ");

function markEdgeManagedTerminologySurfaces(root = document) {
	if (!root?.querySelectorAll) return;
	const candidates = [];
	if (root.matches?.(EDGE_MANAGED_SURFACE_SELECTORS)) candidates.push(root);
	candidates.push(...root.querySelectorAll(EDGE_MANAGED_SURFACE_SELECTORS));
	for (const element of candidates) {
		element.setAttribute("data-eduedge-terminology-managed", "1");
	}
}

function installEdgeManagedTerminologyGuard() {
	markEdgeManagedTerminologySurfaces();
	if (window.__eduedgeTerminologySurfaceGuard || !document.body) return;
	window.__eduedgeTerminologySurfaceGuard = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			for (const node of mutation.addedNodes || []) {
				if (node.nodeType === Node.ELEMENT_NODE) markEdgeManagedTerminologySurfaces(node);
			}
		}
	});
	window.__eduedgeTerminologySurfaceGuard.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", installEdgeManagedTerminologyGuard, { once: true });
} else {
	installEdgeManagedTerminologyGuard();
}

window.markEdgeManagedTerminologySurfaces = markEdgeManagedTerminologySurfaces;
