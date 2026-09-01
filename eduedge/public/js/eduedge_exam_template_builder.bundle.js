import EduEdgeExamTemplateBuilder from "./eduedge_exam_template_builder/EduEdgeExamTemplateBuilder.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const baseMethods = EduEdgeExamTemplateBuilder.methods || {};

const EduEdgeExamTemplateBuilderPage = {
	...EduEdgeExamTemplateBuilder,
	methods: {
		...baseMethods,
		async refreshBuilderOptions() {
			try {
				const response = await frappe.call("eduedge.api.exam_template_scope.get_scope_options", {
					values: JSON.stringify(this.form),
				});
				this.context = {
					...this.context,
					...(response.message || {}),
				};
			} catch (error) {
				this.saveError = error?.message || "Template scope options could not be refreshed.";
			}
		},
	},
};

export function createEduEdgeExamTemplateBuilderApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeExamTemplateBuilderPage, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeExamTemplateBuilder = EduEdgeExamTemplateBuilderPage;
	window.createEduEdgeExamTemplateBuilderApp = createEduEdgeExamTemplateBuilderApp;
}

export default EduEdgeExamTemplateBuilderPage;
