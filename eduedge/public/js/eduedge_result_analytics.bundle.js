import EduEdgeResultAnalytics from "./eduedge_result_analytics/EduEdgeResultAnalytics.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeResultAnalyticsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeResultAnalytics, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeResultAnalytics = EduEdgeResultAnalytics;
	window.createEduEdgeResultAnalyticsApp = createEduEdgeResultAnalyticsApp;
}

export default EduEdgeResultAnalytics;
