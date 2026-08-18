import EduEdgeCBTOperations from "./eduedge_cbt_operations/EduEdgeCBTOperations.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";
import { openEduEdgeRoute } from "./eduedge_ui/navigation";

const TEMPLATE_NATIVE_PREFIX = "/app/eduedge-cbt-exam-template/";

function resolveCBTOperationsRoute(route) {
	if (route === "/app/eduedge-cbt-question") return "/app/eduedge-question-bank";
	if (route === "/app/eduedge-cbt-exam-template") return "/app/eduedge-exam-templates";
	if (route === `${TEMPLATE_NATIVE_PREFIX}new-eduedge-cbt-exam-template`) {
		return "/app/eduedge-exam-template-builder";
	}
	if (route?.startsWith(TEMPLATE_NATIVE_PREFIX)) {
		const templateName = route.slice(TEMPLATE_NATIVE_PREFIX.length);
		return `/app/eduedge-exam-template-builder?template=${encodeURIComponent(decodeURIComponent(templateName))}`;
	}
	return route;
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
