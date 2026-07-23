import { createApp } from "vue";
import EdgeFormDialogFallback from "./components/EdgeFormDialogFallback.vue";
import EdgeModalFallback from "./components/EdgeModalFallback.vue";

function registerFallbackComponent(app, name, component) {
	if (!app.component(name)) app.component(name, component);
}

export function createEduEdgeApp(rootComponent, rootProps = null) {
	if (!rootComponent) {
		throw new Error("An EduEdge root component is required.");
	}

	const runtime = window.EdgeSuiteUI || window.EdgeUI;
	if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
		throw new Error("The standalone EdgeSuite UI runtime is unavailable or incomplete.");
	}

	// Product SFC render helpers and createApp must come from the same Vue bundle.
	// EdgeSuite contributes its shared registry; EduEdge fills only components that
	// are absent so older shared runtimes cannot silently break product dialogs.
	const app = createApp(rootComponent, rootProps || {});
	runtime.install(app);
	registerFallbackComponent(app, "EdgeModal", EdgeModalFallback);
	registerFallbackComponent(app, "EdgeFormDialog", EdgeFormDialogFallback);
	return app;
}
