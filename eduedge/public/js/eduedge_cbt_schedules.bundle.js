import EduEdgeCBTSchedules from "./eduedge_cbt_schedules/EduEdgeCBTSchedules.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const methods = EduEdgeCBTSchedules.methods || {};
const computed = EduEdgeCBTSchedules.computed || {};
const candidateFields = methods.candidateFields;
const openCandidateDialog = methods.openCandidateDialog;
const confirmScheduleStatus = methods.confirmScheduleStatus;
const scheduleActions = computed.scheduleActions;

if (typeof candidateFields === "function") {
	methods.candidateFields = function auditedCandidateFields() {
		return candidateFields.call(this).filter(
			(field) => field.fieldname !== "approved_extra_time_minutes",
		);
	};
}

if (typeof openCandidateDialog === "function") {
	methods.openCandidateDialog = async function auditedOpenCandidateDialog(candidate = null) {
		await openCandidateDialog.call(this, candidate);
		if (!this.candidateModal?.open) return;
		const values = { ...(this.candidateModal.values || {}) };
		delete values.approved_extra_time_minutes;
		this.candidateModal.values = values;
		this.candidateModal.subtitle =
			"Student Branch, Schedule Class, duplicates and access windows are server-enforced. Extra time is granted only through an audited Time Extension intervention.";
	};
}

if (typeof scheduleActions === "function") {
	computed.scheduleActions = function auditedScheduleActions() {
		const actions = scheduleActions.call(this) || [];
		const sittingStarted = (this.context?.candidates || []).some((candidate) =>
			["Checked In", "Released", "Completed"].includes(candidate.assignment_status),
		);
		return sittingStarted
			? actions.filter((action) => action.status !== "Cancelled")
			: actions;
	};
}

if (typeof confirmScheduleStatus === "function") {
	methods.confirmScheduleStatus = function auditedConfirmScheduleStatus(status) {
		confirmScheduleStatus.call(this, status);
		if (!this.confirmDialog?.open) return;
		if (status === "Cancelled") {
			this.confirmDialog.detail =
				"Draft and Eligible candidates will be withdrawn with this reason. A Schedule cannot be cancelled after any candidate checks in, is released, or completes the sitting.";
		}
		if (status === "Completed") {
			this.confirmDialog.detail =
				"Every candidate must already be Completed, Withdrawn or Disqualified, and at least one candidate must be Completed.";
		}
	};
}

export function createEduEdgeCBTSchedulesApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCBTSchedules, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCBTSchedules = EduEdgeCBTSchedules;
	window.createEduEdgeCBTSchedulesApp = createEduEdgeCBTSchedulesApp;
}

export default EduEdgeCBTSchedules;
