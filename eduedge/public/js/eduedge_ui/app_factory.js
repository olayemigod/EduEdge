import { createApp } from "vue";
import EdgeFormDialogFallback from "./components/EdgeFormDialogFallback.vue";
import EdgeLinkFieldFallback from "./components/EdgeLinkFieldFallback.vue";
import EdgeModalFallback from "./components/EdgeModalFallback.vue";

export function createEduEdgeApp(rootComponent, rootProps = null) {
	if (!rootComponent) {
		throw new Error("An EduEdge root component is required.");
	}

	const runtime = window.EdgeSuiteUI || window.EdgeUI;
	if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
		throw new Error("The standalone EdgeSuite UI runtime is unavailable or incomplete.");
	}

	// Product SFC render helpers and createApp must come from the same Vue bundle.
	// EdgeSuite contributes its shared registry. EduEdge deliberately replaces the
	// stateful components below because refs, slots, async search, dialog state, and
	// product events must execute inside the same Vue runtime as the product app.
	const app = createApp(rootComponent, rootProps || {});
	runtime.install(app);
	app.component("EdgeModal", EdgeModalFallback);
	app.component("EdgeLinkField", EdgeLinkFieldFallback);
	app.component("EdgeFormDialog", EdgeFormDialogFallback);
	return app;
}
