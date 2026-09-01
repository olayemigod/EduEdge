import EduEdgeQuestionBuilder from "./eduedge_question_builder/EduEdgeQuestionBuilder.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const baseData = EduEdgeQuestionBuilder.data;
const baseMethods = EduEdgeQuestionBuilder.methods || {};
const baseComputed = EduEdgeQuestionBuilder.computed || {};
const baseMounted = EduEdgeQuestionBuilder.mounted;
const baseBeforeUnmount = EduEdgeQuestionBuilder.beforeUnmount;

const TARGET_ACTIONS = Object.freeze({
	"Under Review": "submit_for_review",
	"Under Subject Review": "submit_for_review",
	Approved: "approve",
	Retired: "retire",
});

function actionButton(label, { primary = false, disabled = false, onClick } = {}) {
	const button = document.createElement("button");
	button.type = "button";
	button.className = `edge-button${primary ? " edge-button--primary" : ""}`;
	button.disabled = Boolean(disabled);
	button.textContent = label;
	button.addEventListener("click", onClick);
	return button;
}

function addText(parent, tag, text, className = "") {
	const node = document.createElement(tag);
	if (className) node.className = className;
	node.textContent = text;
	parent.appendChild(node);
	return node;
}

function ensureGovernanceStyles() {
	if (document.getElementById("eduedge-question-governance-styles")) return;
	const style = document.createElement("style");
	style.id = "eduedge-question-governance-styles";
	style.textContent = `
		.eduedge-governance-workflow-panel {
			margin: 1rem 0;
			padding: 1.1rem 1.2rem;
			border: 1px solid var(--edge-border, #e2e8f0);
			border-radius: var(--edge-radius-lg, .9rem);
			background: var(--edge-surface, #fff);
			box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15,23,42,.06));
		}
		.eduedge-governance-workflow__heading,
		.eduedge-governance-workflow__actions,
		.eduedge-governance-workflow__responsibilities {
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: .75rem;
			flex-wrap: wrap;
		}
		.eduedge-governance-workflow__heading h2 { margin: .15rem 0 .25rem; font-size: 1.05rem; }
		.eduedge-governance-workflow__heading p,
		.eduedge-governance-workflow__message,
		.eduedge-governance-workflow__audit { margin: .25rem 0; color: var(--edge-text-muted, #64748b); }
		.eduedge-governance-workflow__responsibilities { justify-content: flex-start; margin: .8rem 0; }
		.eduedge-governance-workflow__responsibilities span {
			padding: .25rem .55rem;
			border-radius: 999px;
			background: var(--edge-surface-muted, #f1f5f9);
			font-size: .78rem;
			font-weight: 600;
		}
		.eduedge-governance-workflow__feedback { display: grid; gap: .35rem; margin: .9rem 0; }
		.eduedge-governance-workflow__feedback textarea { min-height: 5rem; resize: vertical; }
		.eduedge-governance-workflow__blocked { margin: .65rem 0; color: var(--red-600, #dc2626); }
		.eduedge-governance-workflow__actions { justify-content: flex-end; margin-top: .8rem; }
	`;
	document.head.appendChild(style);
}

const EduEdgeQuestionBuilderPage = {
	...EduEdgeQuestionBuilder,
	data() {
		const state = typeof baseData === "function" ? baseData.call(this) : {};
		return {
			...state,
			questionActionLoading: false,
			questionReviewFeedback: "",
		};
	},
	computed: {
		...baseComputed,
		statusTone() {
			const status = this.form?.status || "Draft";
			if (status === "Approved") return "success";
			if (status === "Retired" || status === "Changes Requested") return "danger";
			if (["Under Review", "Under Subject Review", "Recommended"].includes(status)) return "warning";
			return "neutral";
		},
		actionGuidance() {
			const actionState = this.context?.question_action_state || {};
			const status = this.form?.status || "Draft";
			const relevant = {
				Draft: "submit_for_review",
				"Changes Requested": "submit_for_review",
				"Under Subject Review": "recommend",
				"Under Review": actionState.policy?.question_approval_mode === "Standard" ? "recommend" : "approve",
				Recommended: "approve",
				Approved: "retire",
			}[status];
			const blocked = relevant ? this.actionByName(relevant) : null;
			if (blocked && !blocked.allowed && blocked.reason) return blocked.reason;
			if (typeof baseComputed.actionGuidance === "function") {
				return baseComputed.actionGuidance.call(this);
			}
			return "Question actions use the effective Institution policy, current role capability, and scoped responsibility assignment.";
		},
	},
	mounted() {
		ensureGovernanceStyles();
		if (typeof baseMounted === "function") baseMounted.call(this);
	},
	updated() {
		this.$nextTick(() => this.renderGovernancePanel());
	},
	beforeUnmount() {
		this.removeGovernancePanel();
		if (typeof baseBeforeUnmount === "function") baseBeforeUnmount.call(this);
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
				this.$nextTick(() => this.renderGovernancePanel());
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
			this.$nextTick(() => this.renderGovernancePanel());
		},
		actionByName(action) {
			return (this.context?.question_action_state?.actions || []).find((row) => row.action === action) || null;
		},
		resolveTargetAction(targetStatus) {
			const currentStatus = this.form?.status || "Draft";
			if (targetStatus === "Draft" && ["Under Review", "Changes Requested"].includes(currentStatus)) {
				return "return_to_draft";
			}
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
		runGovernedAction(action, feedback = "") {
			const actionState = this.actionByName(action);
			if (!actionState?.allowed) {
				this.saveError = actionState?.reason || "This question action is not available.";
				return;
			}
			if (actionState.requires_feedback && !String(feedback || "").trim()) {
				this.saveError = "Enter the changes required before returning this question to the author.";
				return;
			}
			const execute = () => this.executeSaveAndAction(action, feedback);
			if (actionState.requires_confirmation) {
				frappe.confirm(
					__(`${actionState.label}? This will change the governed Question Status.`),
					execute
				);
				return;
			}
			return execute();
		},
		async executeSaveAndAction(action, feedback = "") {
			if (this.saving || this.questionActionLoading) return;
			const currentStatus = this.form?.status || "Draft";
			const shouldSaveContent = ["Draft", "Changes Requested"].includes(currentStatus);
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
						feedback: String(feedback || "").trim() || undefined,
					});
					this.questionReviewFeedback = "";
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
				this.$nextTick(() => this.renderGovernancePanel());
			}
		},
		removeGovernancePanel() {
			this.$el?.querySelector?.("#eduedge-governance-workflow-panel")?.remove();
		},
		renderGovernancePanel() {
			this.removeGovernancePanel();
			if (!this.form?.name || !this.$el) return;
			const state = this.context?.question_action_state;
			if (!state) return;

			const panel = document.createElement("section");
			panel.id = "eduedge-governance-workflow-panel";
			panel.className = "eduedge-governance-workflow-panel";

			const heading = document.createElement("div");
			heading.className = "eduedge-governance-workflow__heading";
			const copy = document.createElement("div");
			addText(copy, "p", "Policy-driven workflow", "edge-eyebrow");
			addText(copy, "h2", `${state.policy?.question_approval_mode || "Unresolved"} Question Approval`);
			addText(copy, "p", `Status: ${state.status || this.form.status}. Policy source: ${state.policy?.source || "Not resolved"}.`);
			heading.appendChild(copy);
			panel.appendChild(heading);

			const responsibility = state.responsibilities || {};
			const tags = document.createElement("div");
			tags.className = "eduedge-governance-workflow__responsibilities";
			for (const [label, allowed] of [
				["Question Author", responsibility.can_author],
				["Subject Reviewer", responsibility.can_subject_review],
				["Final Approver", responsibility.can_final_approve],
			]) {
				addText(tags, "span", `${label}: ${allowed ? "Assigned" : "Not assigned"}`);
			}
			panel.appendChild(tags);

			const audit = state.audit || {};
			if (audit.review_feedback) addText(panel, "p", `Latest review feedback: ${audit.review_feedback}`, "eduedge-governance-workflow__audit");
			if (audit.recommended_by) addText(panel, "p", `Recommended by ${audit.recommended_by}${audit.recommended_on ? ` on ${audit.recommended_on}` : ""}.`, "eduedge-governance-workflow__audit");
			if (audit.approved_by) addText(panel, "p", `Approved by ${audit.approved_by}${audit.approved_on ? ` on ${audit.approved_on}` : ""}.`, "eduedge-governance-workflow__audit");

			const status = state.status || this.form.status;
			const mode = state.policy?.question_approval_mode;
			const actions = document.createElement("div");
			actions.className = "eduedge-governance-workflow__actions";
			let relevant = [];

			if (mode === "Standard" && ["Under Subject Review", "Under Review"].includes(status)) {
				const feedbackWrap = document.createElement("label");
				feedbackWrap.className = "eduedge-governance-workflow__feedback";
				addText(feedbackWrap, "span", "Subject review note");
				const textarea = document.createElement("textarea");
				textarea.className = "form-control";
				textarea.placeholder = "Required when requesting changes; optional when recommending.";
				textarea.value = this.questionReviewFeedback || "";
				textarea.addEventListener("input", (event) => {
					this.questionReviewFeedback = event.target.value;
				});
				feedbackWrap.appendChild(textarea);
				panel.appendChild(feedbackWrap);
				relevant = ["request_changes", "recommend"];
			} else if (status === "Recommended") {
				relevant = ["approve"];
			} else if (status === "Draft" || status === "Changes Requested") {
				relevant = ["submit_for_review"];
			} else if (status === "Under Review") {
				relevant = ["approve"];
			} else if (status === "Approved") {
				relevant = ["retire"];
			}

			for (const actionName of relevant) {
				const action = this.actionByName(actionName);
				if (!action) continue;
				if (!action.allowed && action.reason) {
					addText(panel, "p", action.reason, "eduedge-governance-workflow__blocked");
				}
				if (["submit_for_review", "approve", "retire"].includes(actionName) && status !== "Recommended") {
					continue;
				}
				actions.appendChild(
					actionButton(action.label, {
						primary: ["recommend", "approve"].includes(actionName),
						disabled:
							this.saving ||
							this.questionActionLoading ||
							!action.allowed ||
							(action.requires_feedback && !String(this.questionReviewFeedback || "").trim()),
						onClick: () => this.runGovernedAction(actionName, this.questionReviewFeedback),
					})
				);
			}
			if (actions.childNodes.length) panel.appendChild(actions);

			const anchor = this.$el.querySelector(".eduedge-question-error") || this.$el.querySelector(".edge-action-bar");
			if (anchor?.parentNode) anchor.parentNode.insertBefore(panel, anchor);
			else this.$el.appendChild(panel);
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
