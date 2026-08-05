import EduEdgeInstructorAssignments from "./eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

function keepNewestAssignmentRowOnTop(methodName) {
	const methods = EduEdgeInstructorAssignments.methods || {};
	const original = methods[methodName];
	if (typeof original !== "function") return;

	methods[methodName] = function (...args) {
		const existingIds = new Set((this.rows || []).map((row) => row.row_id));
		const result = original.apply(this, args);
		const createdIndex = (this.rows || []).findIndex((row) => !existingIds.has(row.row_id));
		if (createdIndex > 0) {
			const [newest] = this.rows.splice(createdIndex, 1);
			this.rows.unshift(newest);
		}
		this.$nextTick?.(() => {
			document.querySelector(".rows-stack .assignment-row")?.scrollIntoView({
				behavior: "smooth",
				block: "start",
			});
		});
		return result;
	};
}

keepNewestAssignmentRowOnTop("addAcademicRow");
keepNewestAssignmentRowOnTop("addBranchAccessRow");
keepNewestAssignmentRowOnTop("duplicateRow");

export function createEduEdgeInstructorAssignmentsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstructorAssignments, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstructorAssignments = EduEdgeInstructorAssignments;
	window.createEduEdgeInstructorAssignmentsApp = createEduEdgeInstructorAssignmentsApp;
}

export default EduEdgeInstructorAssignments;
