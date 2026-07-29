import EduEdgeProgrammeOfferings from "./eduedge_programme_offerings/EduEdgeProgrammeOfferings.vue";
import { applyProgrammeOfferingLevelCascade } from "./eduedge_programme_offerings/level_cascade";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const CascadedProgrammeOfferings = applyProgrammeOfferingLevelCascade(EduEdgeProgrammeOfferings);

export function createEduEdgeProgrammeOfferingsApp(rootProps = null) {
	return createEduEdgeApp(CascadedProgrammeOfferings, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeProgrammeOfferings = CascadedProgrammeOfferings;
	window.createEduEdgeProgrammeOfferingsApp = createEduEdgeProgrammeOfferingsApp;
}

export default CascadedProgrammeOfferings;
