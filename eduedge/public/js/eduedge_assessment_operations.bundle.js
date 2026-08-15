import EduEdgeAssessmentOperations from "./eduedge_assessment_operations/EduEdgeAssessmentOperations.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

// Programme Offerings and Class Arms are session-wide. Assessment Plans and
// Result Publications remain Term/Semester scoped, so use the session-aware
// context endpoint that keeps a blank-term Student Group visible in every
// valid Term of its Academic Session while preserving exact legacy term groups.
EduEdgeAssessmentOperations.methods.loadContext = async function loadContext() {
	this.loading = true;
	this.error = "";
	try {
		const response = await frappe.call("eduedge.api.assessment_operations_sessional.get_assessment_context", {
			branch: this.filters.branch || undefined,
			academic_year: this.filters.academic_year || undefined,
			academic_term: this.filters.academic_term || undefined,
			student_group: this.filters.student_group || undefined,
			assessment_group: this.filters.assessment_group || undefined,
		});
		this.context = response.message || this.context;
		this.filters = { ...this.filters, ...(this.context.filters || {}) };
	} catch (error) {
		this.error = error?.message || "Assessment operations could not be loaded.";
	} finally {
		this.loading = false;
	}
};

export function createEduEdgeAssessmentOperationsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeAssessmentOperations, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeAssessmentOperations = EduEdgeAssessmentOperations;
	window.createEduEdgeAssessmentOperationsApp = createEduEdgeAssessmentOperationsApp;
}

export default EduEdgeAssessmentOperations;
