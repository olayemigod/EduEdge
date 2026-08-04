import EduEdgeAcademicSessions from "./eduedge_academic_sessions/EduEdgeAcademicSessions.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeAcademicSessionsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeAcademicSessions, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeAcademicSessions = EduEdgeAcademicSessions;
	window.createEduEdgeAcademicSessionsApp = createEduEdgeAcademicSessionsApp;
}

export default EduEdgeAcademicSessions;
