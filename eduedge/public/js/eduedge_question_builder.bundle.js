import EduEdgeQuestionBuilder from "./eduedge_question_builder/EduEdgeQuestionBuilder.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const baseData = EduEdgeQuestionBuilder.data;
const baseMethods = EduEdgeQuestionBuilder.methods || {};
const baseComputed = EduEdgeQuestionBuilder.computed || {};

const TARGET_ACTIONS = Object.freeze({
	"Under Review": "submit_for_review",
	Approved: "approve",
	Retired: "retire",
});

const EduEdgeQuestionBuilderPage = {
	...EduEdgeQuestionBuilder,
	data() {
		const state = typeof baseData === "function" ? baseData.call(this) : {};
		return {
			...state,
			questionActionLoading: false,
		};
	},
	computed: {
		...baseComputed,
		actionGuidance() {
			const actionState = this.context?.question_action_state || {};
			const status = this.form?.status || "Draft";
			const relevantAction = status === "Under Review" ? "approve" : status === "Approved" ? "retire" : null;
			const blocked = relevantAction
				? (actionState.actions || []).find((row) => row.action === relevantAction && !row.allowed)
				: null;
			if (blocked?.reason) return blocked.reason;
			if (typeof baseComputed.actionGuidance === "function") {
				return baseComputed.actionGuidance.call(this);
			}
			return "Question actions use the effective Institution governance policy and current role permissions.";
		},
	},
	methods: {
		...baseMethods,
		async applyState(state) {
			await baseMethods.applyState.call(this, state);
			await this.loadQuestionActionState();
		},
		async loadQuestionActionState() {
			if (!this.form?.name) {
				this.context = { ...this.context, question_action_state: { status: "Draft", actions: [] } };
				return;
			}
			try {
				const response = await frappe.call("eduedge.api.question_governance.get_action_state", {
					question: this.form.name,
				});
				const actionState = response.message || { actions: [] };
				const canReviewCurrentStatus = (actionState.actions || []).some(
					(row) => row.allowed && ["approve", "retire"].includes(row.action)
				);
				this.context = {
					...this.context,
					question_action_state: actionState,
					permissions: {
						...(this.context.permissions || {}),
						can_review: canReviewCurrentStatus,
					},
				};
			} catch (error) {
				this.context = {
					...this.context,
					question_action_state: {
						status: this.form.status || "Draft",
						actions: [],
						error: error?.message || "Question governance actions could not be loaded.",
					},
					permissions: { ...(this.context.permissions || {}), can_review: false },
				};
			}
		},
		actionByName(action) {
			return (this.context?.question_action_state?.actions || []).find((row) => row.action === action) || null;
		},
		resolveTargetAction(targetStatus) {
			const currentStatus = this.form?.status || "Draft";
			if (targetStatus === "Draft" && currentStatus === "Under Review") return "return_to_draft";
			if (targetStatus === currentStatus) return null;
			return TARGET_ACTIONS[targetStatus] || null;
		},
		saveAs(targetStatus) {
			if (this.saving || this.questionActionLoading) return;
			const action = this.resolveTargetAction(targetStatus);
			const actionState = action ? this.actionByName(action) : null;
			if (actionState && !actionState.allowed) {
				this.saveError = actionState.reason || "This question action is not available.";
				return;
			}
			if (actionState?.requires_confirmation) {
				frappe.confirm(
					__(`${actionState.label}? This will change the governed Question Status.`),
					() => this.executeSaveAndAction(action)
				);
				return;
			}
			return this.executeSaveAndAction(action);
		},
		async executeSaveAndAction(action) {
			if (this.saving || this.questionActionLoading) return;
			const currentStatus = this.form?.status || "Draft";
			const shouldSaveContent = !["Approved", "Retired"].includes(currentStatus);
			if (shouldSaveContent) {
				const errors = this.validateForm();
				if (errors.length) {
					this.saveError = errors.join(" ");
					return;
				}
			}

			this.saving = true;
			this.questionActionLoading = Boolean(action);
			this.saveError = "";
			try {
				if (shouldSaveContent) {
					const saveResponse = await frappe.call("eduedge.api.question_builder.save_question", {
						payload: JSON.stringify(this.payload(currentStatus)),
					});
					await this.applyState(saveResponse.message || {});
					this.updateQuestionUrl();
				}

				if (action) {
					const actionResponse = await frappe.call("eduedge.api.question_governance.perform_action", {
						question: this.form.name,
						action,
						expected_modified: this.context?.question_action_state?.modified || undefined,
					});
					await this.loadBuilder();
					frappe.show_alert(
						{ message: actionResponse.message?.action_label || __("Question action completed."), indicator: "green" },
						5
					);
				} else {
					frappe.show_alert({ message: __("Question saved successfully."), indicator: "green" }, 5);
				}
			} catch (error) {
				this.saveError = error?.message || "The question action could not be completed.";
			} finally {
				this.saving = false;
				this.questionActionLoading = false;
			}
		},
	},
};

export function createEduEdgeQuestionBuilderApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeQuestionBuilderPage, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeQuestionBuilder = EduEdgeQuestionBuilderPage;
	window.createEduEdgeQuestionBuilderApp = createEduEdgeQuestionBuilderApp;
}

export default EduEdgeQuestionBuilderPage;
