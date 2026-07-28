import EduEdgeProgrammes from "./eduedge_programmes/EduEdgeProgrammes.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeProgrammesApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeProgrammes, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeProgrammes = EduEdgeProgrammes;
	window.createEduEdgeProgrammesApp = createEduEdgeProgrammesApp;
}

export default EduEdgeProgrammes;
