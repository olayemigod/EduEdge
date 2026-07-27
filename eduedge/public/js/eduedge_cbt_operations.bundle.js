import EduEdgeCBTOperations from "./eduedge_cbt_operations/EduEdgeCBTOperations.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";
import { openEduEdgeRoute } from "./eduedge_ui/navigation";

function resolveCBTOperationsRoute(route) {
	return route === "/app/eduedge-cbt-question" ? "/app/eduedge-question-bank" : route;
}

const EduEdgeCBTOperationsPage = {
	...EduEdgeCBTOperations,
	methods: {
		...(EduEdgeCBTOperations.methods || {}),
		openRoute(route) {
			return openEduEdgeRoute(resolveCBTOperationsRoute(route));
		},
	},
};

export function createEduEdgeCBTOperationsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCBTOperationsPage, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCBTOperations = EduEdgeCBTOperationsPage;
	window.createEduEdgeCBTOperationsApp = createEduEdgeCBTOperationsApp;
}

export { resolveCBTOperationsRoute };
export default EduEdgeCBTOperationsPage;
