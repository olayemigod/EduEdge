import EduEdgeResultIntelligence from "./eduedge_result_intelligence/EduEdgeResultIntelligence.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeResultIntelligenceApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeResultIntelligence, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeResultIntelligence = EduEdgeResultIntelligence;
	window.createEduEdgeResultIntelligenceApp = createEduEdgeResultIntelligenceApp;
}

export default EduEdgeResultIntelligence;
