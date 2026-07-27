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
	// EdgeSuite contributes its shared registry. EduEdge deliberately owns the
	// quick-editor form dialog because its schema, events, and loading contract
	// must remain stable across shared-runtime versions.
	const app = createApp(rootComponent, rootProps || {});
	runtime.install(app);
	registerFallbackComponent(app, "EdgeModal", EdgeModalFallback);
	app.component("EdgeFormDialog", EdgeFormDialogFallback);
	return app;
}
