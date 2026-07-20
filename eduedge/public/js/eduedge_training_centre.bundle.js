import EduEdgeTrainingCentre from "./eduedge_training_centre/EduEdgeTrainingCentre.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeTrainingCentreApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeTrainingCentre, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeTrainingCentre = EduEdgeTrainingCentre;
	window.createEduEdgeTrainingCentreApp = createEduEdgeTrainingCentreApp;
}

export default EduEdgeTrainingCentre;
