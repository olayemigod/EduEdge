import { createApp, defineComponent, h } from "vue";
import EdgeFormDialogFallback from "./components/EdgeFormDialogFallback.vue";
import EdgeLinkFieldFallback from "./components/EdgeLinkFieldFallback.vue";
import EdgeModalFallback from "./components/EdgeModalFallback.vue";
import EduEdgeMultiLinkField from "./components/EduEdgeMultiLinkField.vue";
import { EDUEDGE_SECTION_STATE_KEY } from "./navigation";

export function resolveEdgeSuiteRuntime(requiredComponents = ["EdgeAppShell"]) {
	const componentNames = Array.isArray(requiredComponents)
		? requiredComponents.filter(Boolean)
		: [requiredComponents].filter(Boolean);
	return (
		[window.EdgeSuiteUI, window.EdgeUI].find(
			(candidate) =>
				typeof candidate?.install === "function" &&
				componentNames.every((componentName) => Boolean(candidate?.components?.[componentName]))
		) || null
	);
}

function createEduEdgeShell(sharedShell) {
	return defineComponent({
		name: "EduEdgeAppShell",
		inheritAttrs: false,
		setup(_props, context) {
			return () =>
				h(
					sharedShell,
					{
						...(context.attrs || {}),
						sectionStateKey: context.attrs?.sectionStateKey || EDUEDGE_SECTION_STATE_KEY,
						accordion: context.attrs?.accordion ?? true,
						exclusiveSections: context.attrs?.exclusiveSections ?? true,
					},
					context.slots
				);
		},
	});
}

export function createEduEdgeApp(rootComponent, rootProps = null) {
	if (!rootComponent) {
		throw new Error("An EduEdge root component is required.");
	}

	const runtime = resolveEdgeSuiteRuntime(["EdgeAppShell"]);
	if (!runtime) {
		throw new Error("The standalone EdgeSuite UI runtime is unavailable or incomplete.");
	}

	// Product SFC render helpers and createApp must come from the same Vue bundle.
	// EdgeSuite contributes its shared registry. EduEdge deliberately replaces the
	// stateful components below because refs, slots, async search, dialog state, and
	// product events must execute inside the same Vue runtime as the product app.
	const app = createApp(rootComponent, rootProps || {});
	const sharedShell = runtime.components?.EdgeAppShell;
	runtime.install(app);
	if (sharedShell) app.component("EdgeAppShell", createEduEdgeShell(sharedShell));
	app.component("EdgeModal", EdgeModalFallback);
	app.component("EdgeLinkField", EdgeLinkFieldFallback);
	app.component("EdgeFormDialog", EdgeFormDialogFallback);
	app.component("EduEdgeMultiLinkField", EduEdgeMultiLinkField);
	return app;
}
