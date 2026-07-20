import EduEdgeReportCards from "./eduedge_report_cards/EduEdgeReportCards.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeReportCardsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeReportCards, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeReportCards = EduEdgeReportCards;
	window.createEduEdgeReportCardsApp = createEduEdgeReportCardsApp;
}

export default EduEdgeReportCards;
