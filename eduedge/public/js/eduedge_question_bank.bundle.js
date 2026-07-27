import EduEdgeQuestionBank from "./eduedge_question_bank/EduEdgeQuestionBank.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const baseData = EduEdgeQuestionBank.data;
const baseMethods = EduEdgeQuestionBank.methods || {};

const EduEdgeQuestionBankPage = {
	...EduEdgeQuestionBank,
	data() {
		const state = typeof baseData === "function" ? baseData.call(this) : {};
		return {
			...state,
			questionBankRequestSerial: 0,
			questionBankLastBranch: state.filters?.branch || "",
		};
	},
	methods: {
		...baseMethods,
		async loadQuestions() {
			const requestId = ++this.questionBankRequestSerial;
			this.loading = true;
			this.loadError = "";
			try {
				const response = await frappe.call("eduedge.api.question_bank.get_question_bank", {
					...this.filters,
					start: this.pagination.start,
					page_length: this.pagination.page_length,
				});
				if (requestId !== this.questionBankRequestSerial) return;
				const next = response.message || {};
				this.state = { ...this.state, ...next, options: { ...this.state.options, ...(next.options || {}) } };
				this.filters = { ...this.filters, ...(next.filters || {}) };
				this.pagination = { ...this.pagination, ...(next.pagination || {}) };
				this.questionBankLastBranch = this.filters.branch || "";
				if (!this.filters.course) this.courseLabel = "";
			} catch (error) {
				if (requestId !== this.questionBankRequestSerial) return;
				this.loadError = error?.message || "Question Bank records could not be loaded.";
			} finally {
				if (requestId === this.questionBankRequestSerial) {
					this.loading = false;
					this.initialLoading = false;
				}
			}
		},
		filterChanged() {
			const branch = this.filters.branch || "";
			if (branch !== this.questionBankLastBranch) {
				this.filters.course = "";
				this.courseLabel = "";
				this.questionBankLastBranch = branch;
			}
			this.pagination.start = 0;
			return this.loadQuestions();
		},
		async searchCourses(query) {
			const response = await frappe.call("eduedge.api.question_bank.search_courses", {
				txt: query || "",
				ownership_scope: this.filters.ownership_scope || undefined,
				institution: this.filters.institution || undefined,
				branch: this.filters.branch || undefined,
				page_length: 20,
			});
			return response.message || [];
		},
		previousPage() {
			if (this.loading || !this.pagination.has_previous) return;
			this.pagination.start = Math.max(0, this.pagination.start - this.pagination.page_length);
			return this.loadQuestions();
		},
		nextPage() {
			if (this.loading || !this.pagination.has_next) return;
			this.pagination.start += this.pagination.page_length;
			return this.loadQuestions();
		},
	},
};

export function createEduEdgeQuestionBankApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionBankPage, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBank = EduEdgeQuestionBankPage;
	window.createEduEdgeQuestionBankApp = createEduEdgeQuestionBankApp;
}

export default EduEdgeQuestionBankPage;
