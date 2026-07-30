import EduEdgeProgrammeOfferings from "./eduedge_programme_offerings/EduEdgeProgrammeOfferings.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeProgrammeOfferingsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeProgrammeOfferings, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeProgrammeOfferings = EduEdgeProgrammeOfferings;
	window.createEduEdgeProgrammeOfferingsApp = createEduEdgeProgrammeOfferingsApp;
}

export default EduEdgeProgrammeOfferings;
