import EduEdgeMarksEntry from "./eduedge_marks_entry/EduEdgeMarksEntry.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeMarksEntryApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeMarksEntry, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeMarksEntry = EduEdgeMarksEntry;
	window.createEduEdgeMarksEntryApp = createEduEdgeMarksEntryApp;
}

export default EduEdgeMarksEntry;
