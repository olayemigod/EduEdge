import EduEdgeCBTSchedules from "./eduedge_cbt_schedules/EduEdgeCBTSchedules.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const methods = EduEdgeCBTSchedules.methods || {};
const candidateFields = methods.candidateFields;
const openCandidateDialog = methods.openCandidateDialog;
const confirmScheduleStatus = methods.confirmScheduleStatus;

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

if (typeof confirmScheduleStatus === "function") {
	methods.confirmScheduleStatus = function auditedConfirmScheduleStatus(status) {
		confirmScheduleStatus.call(this, status);
		if (!this.confirmDialog?.open) return;
		if (status === "Cancelled") {
			this.confirmDialog.detail =
				"Draft and Eligible candidates will be withdrawn with this reason. Checked In or Released candidates must be resolved before cancellation.";
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
