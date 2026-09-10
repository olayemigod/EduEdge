import EduEdgeCurriculum from "./eduedge_curriculum/EduEdgeCurriculum.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeCurriculumApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCurriculum, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCurriculum = EduEdgeCurriculum;
	window.createEduEdgeCurriculumApp = createEduEdgeCurriculumApp;
}

export default EduEdgeCurriculum;
