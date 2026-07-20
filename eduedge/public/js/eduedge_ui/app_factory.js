import { createApp } from "vue";

export function createEduEdgeApp(rootComponent, rootProps = null) {
	if (!rootComponent) {
		throw new Error("An EduEdge root component is required.");
	}

	const runtime = window.EdgeSuiteUI || window.EdgeUI;
	if (!runtime?.install || !runtime?.components?.EdgeAppShell) {
		throw new Error("The standalone EdgeSuite UI runtime is unavailable or incomplete.");
	}

	// Product SFC render helpers and createApp must come from the same Vue bundle.
	// EdgeSuite then contributes its shared component registry through install().
	const app = createApp(rootComponent, rootProps || {});
	runtime.install(app);
	return app;
}
