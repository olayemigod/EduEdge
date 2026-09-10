import EduEdgeAttendance from "./eduedge_attendance/EduEdgeAttendance.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeAttendanceApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeAttendance, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeAttendance = EduEdgeAttendance;
	window.createEduEdgeAttendanceApp = createEduEdgeAttendanceApp;
}

export default EduEdgeAttendance;
