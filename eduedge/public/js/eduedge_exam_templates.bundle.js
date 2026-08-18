import EduEdgeExamTemplates from "./eduedge_exam_templates/EduEdgeExamTemplates.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const baseMethods = EduEdgeExamTemplates.methods || {};

const EduEdgeExamTemplatesPage = {
	...EduEdgeExamTemplates,
	methods: {
		...baseMethods,
		async loadTemplates({ resetPage = false } = {}) {
			const sequence = ++this.requestSequence;
			this.loading = true;
			this.loadError = "";
			const start = resetPage ? 0 : this.pagination.start || 0;
			try {
				const response = await frappe.call("eduedge.api.exam_templates_list.get_exam_templates", {
					...this.filters,
					start,
					page_length: this.pagination.page_length || 20,
				});
				if (sequence !== this.requestSequence) return;
				this.state = response.message || {
					rows: [], counts: {}, filters: {}, options: {}, pagination: {}, permissions: {}, user: {},
				};
				this.filters = { ...this.filters, ...(this.state.filters || {}) };
				if (!this.courseLabel && this.filters.course) this.courseLabel = this.filters.course;
			} catch (error) {
				if (sequence !== this.requestSequence) return;
				this.loadError = error?.message || "Exam Templates could not be loaded.";
			} finally {
				if (sequence === this.requestSequence) {
					this.loading = false;
					this.initialLoading = false;
				}
			}
		},
	},
};

export function createEduEdgeExamTemplatesApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeExamTemplatesPage, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeExamTemplates = EduEdgeExamTemplatesPage;
	window.createEduEdgeExamTemplatesApp = createEduEdgeExamTemplatesApp;
}

export default EduEdgeExamTemplatesPage;
