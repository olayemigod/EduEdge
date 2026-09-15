import EduEdgeResultBroadsheet from "./eduedge_result_broadsheet/EduEdgeResultBroadsheet.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeResultBroadsheetApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeResultBroadsheet, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeResultBroadsheet = EduEdgeResultBroadsheet;
	window.createEduEdgeResultBroadsheetApp = createEduEdgeResultBroadsheetApp;
}

export default EduEdgeResultBroadsheet;
