import EduEdgeProgrammeOfferings from "./eduedge_programme_offerings/EduEdgeProgrammeOfferings.vue";
import { applyProgrammeOfferingLevelCascade } from "./eduedge_programme_offerings/level_cascade";
import { applyProgrammeOfferingTerminology } from "./eduedge_programme_offerings/terminology";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const CascadedProgrammeOfferings = applyProgrammeOfferingLevelCascade(EduEdgeProgrammeOfferings);
const TerminologyAwareProgrammeOfferings = applyProgrammeOfferingTerminology(CascadedProgrammeOfferings);

export function createEduEdgeProgrammeOfferingsApp(rootProps = null) {
	return createEduEdgeApp(TerminologyAwareProgrammeOfferings, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeProgrammeOfferings = TerminologyAwareProgrammeOfferings;
	window.createEduEdgeProgrammeOfferingsApp = createEduEdgeProgrammeOfferingsApp;
}

export default TerminologyAwareProgrammeOfferings;
