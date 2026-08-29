import EduEdgeSchoolCalendar from "./eduedge_school_calendar/EduEdgeSchoolCalendar.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeSchoolCalendarApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeSchoolCalendar, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeSchoolCalendar = EduEdgeSchoolCalendar;
	window.createEduEdgeSchoolCalendarApp = createEduEdgeSchoolCalendarApp;
}

export default EduEdgeSchoolCalendar;
