import EduEdgeInstructorAssignments from "./eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

let promotedRowSequence = 0;

function uniquePromotedRowId() {
	promotedRowSequence += 1;
	return `assignment-row-${Date.now()}-promoted-${promotedRowSequence}`;
}

function keepNewestAssignmentRowOnTop(methodName) {
	const methods = EduEdgeInstructorAssignments.methods || {};
	const original = methods[methodName];
	if (typeof original !== "function") return;

	methods[methodName] = function (...args) {
		const existingIds = new Set((this.rows || []).map((row) => row.row_id));
		const previousLength = (this.rows || []).length;
		const result = original.apply(this, args);
		if ((this.rows || []).length > previousLength) {
			const [newest] = this.rows.splice(this.rows.length - 1, 1);
			if (!newest.row_id || existingIds.has(newest.row_id)) {
				newest.row_id = uniquePromotedRowId();
			}
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

function labelInstitutionSubjectsByClassMembership() {
	const methods = EduEdgeInstructorAssignments.methods || {};
	const original = methods.coursesFor;
	if (typeof original !== "function") return;

	methods.coursesFor = function (row) {
		const courses = original.call(this, row) || [];
		const offering = this.offeringRecord?.(row?.program_offering);
		const configured = new Set(
			this.data?.configured_course_map?.[offering?.program] || [],
		);
		return courses.map((course) => {
			const isConfigured = configured.has(course.name);
			const name = course.course_name || course.name;
			return {
				...course,
				eduedge_configured_in_class: isConfigured,
				course_name: isConfigured
					? name
					: `${name} · Add to Class curriculum`,
			};
		});
	};
}

keepNewestAssignmentRowOnTop("addAcademicRow");
keepNewestAssignmentRowOnTop("addBranchAccessRow");
keepNewestAssignmentRowOnTop("duplicateRow");
labelInstitutionSubjectsByClassMembership();

export function createEduEdgeInstructorAssignmentsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstructorAssignments, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstructorAssignments = EduEdgeInstructorAssignments;
	window.createEduEdgeInstructorAssignmentsApp = createEduEdgeInstructorAssignmentsApp;
}

export default EduEdgeInstructorAssignments;
