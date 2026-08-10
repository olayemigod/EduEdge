function escapeHtml(value) {
	return frappe.utils.escape_html(String(value ?? ""));
}

function siteToday() {
	return frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10);
}

function replacementArgs(item, values) {
	return {
		name: item.name,
		replacement_instructor: String(values.replacement_instructor || "").trim(),
		handover_date: String(values.handover_date || "").trim(),
		reason: String(values.reason || "").trim(),
	};
}

function sameArgs(left, right) {
	return JSON.stringify(left || {}) === JSON.stringify(right || {});
}

function branchImpactLabel(branch) {
	const action = String(branch?.action || "");
	if (action === "existing") return __("Existing Branch Eligibility already covers the successor period; no Branch change will be made.");
	if (action === "create") return __("A Branch Eligibility period will be created for the incoming Instructor.");
	if (action === "extend") return __("The incoming Instructor's existing Branch Eligibility will be extended only as required for this responsibility.");
	if (action === "enable") return __("An exact disabled Branch Eligibility period will be re-enabled for the incoming Instructor.");
	return __("Branch Eligibility impact is unavailable. Do not confirm until the preview is complete.");
}

function renderConflictList(conflicts) {
	if (!conflicts?.length) return `<div class="alert alert-success mb-2">${__("No replacement conflicts found.")}</div>`;
	const rows = conflicts
		.map((item) => `<li>${escapeHtml(item.reason || item.type || item.name || __("Conflict"))}</li>`)
		.join("");
	return `<div class="alert alert-danger mb-2"><strong>${__("Resolve these conflicts before replacing")}</strong><ul class="mb-0 mt-2">${rows}</ul></div>`;
}

function renderReplacementPreview(plan) {
	const source = plan?.source || {};
	const successor = plan?.successor || {};
	const branch = plan?.incoming_branch_eligibility || {};
	return `
		<div class="eduedge-replacement-preview">
			${renderConflictList(plan?.conflicts || [])}
			<div class="mb-2"><strong>${__("Outgoing responsibility")}</strong><br>
				<span class="text-muted">${escapeHtml(source.assignment_title || source.name || "")}</span><br>
				<span>${escapeHtml(source.valid_from || __("No start restriction"))} → <strong>${escapeHtml(source.final_valid_to || plan?.handover_date || "")}</strong></span>
			</div>
			<div class="mb-2"><strong>${__("Incoming responsibility")}</strong><br>
				<span>${escapeHtml(successor.instructor_name || successor.instructor || "")} · ${escapeHtml(successor.assignment_type || "")}</span><br>
				<span>${escapeHtml(successor.valid_from || "")} → ${escapeHtml(successor.valid_to || __("Open ended"))}</span><br>
				<span class="text-muted">${escapeHtml(successor.school_branch || "")} · ${escapeHtml(successor.program_offering || "")}${successor.student_group ? ` · ${escapeHtml(successor.student_group)}` : ""}${successor.course ? ` · ${escapeHtml(successor.course)}` : ""}</span>
			</div>
			<div class="mb-2"><strong>${__("Branch Eligibility impact")}</strong><br>
				<span>${escapeHtml(branchImpactLabel(branch))}</span>${branch.name ? `<br><span class="text-muted">${escapeHtml(branch.name)}</span>` : ""}
			</div>
			<div class="text-muted">${__("The outgoing Instructor's Branch Eligibility is not changed by Replace / Handover.")}</div>
		</div>
	`;
}

function setPreviewHtml(dialog, html) {
	const field = dialog.get_field("replacement_preview");
	field?.$wrapper?.html(html || `<div class="text-muted">${__("Preview the handover before confirming.")}</div>`);
}

function setBusy(dialog, busy, onBusy, itemName) {
	onBusy?.(busy ? itemName : "");
	dialog.get_primary_btn()?.prop("disabled", Boolean(busy));
}

export function openInstructorAssignmentReplacementDialog({ item, onBusy, onComplete }) {
	if (!item?.name) return;
	const today = siteToday();
	const title = escapeHtml(item.assignment_title || item.assignment_type || item.name);
	let previewPlan = null;
	let previewedArgs = null;
	let dialog;

	const showPreviewAction = () => {
		previewPlan = null;
		previewedArgs = null;
		setPreviewHtml(dialog, "");
		dialog.set_primary_action(__("Preview Replacement"), async (values) => {
			const args = replacementArgs(item, values);
			if (!args.replacement_instructor || !args.handover_date || !args.reason) {
				frappe.msgprint({ title: __("Replacement details required"), message: __("Select the incoming Instructor, Handover Date and Reason before previewing."), indicator: "orange" });
				return;
			}
			if (args.replacement_instructor === item.instructor) {
				frappe.msgprint({ title: __("Choose another Instructor"), message: __("Replacement Instructor must be different from the outgoing Instructor."), indicator: "orange" });
				return;
			}
			setBusy(dialog, true, onBusy, item.name);
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_replacement.preview_instructor_assignment_replacement",
					type: "POST",
					args,
				});
				previewPlan = response.message || null;
				previewedArgs = args;
				setPreviewHtml(dialog, renderReplacementPreview(previewPlan));
				if (previewPlan?.already_replaced) {
					frappe.msgprint({ title: __("Assignment already replaced"), message: __("This responsibility already has a successor. Refresh the register to see the lifecycle relationship."), indicator: "blue" });
					return;
				}
				if (Number(previewPlan?.conflict_count || 0) > 0) return;
				showConfirmAction();
			} catch (error) {
				previewPlan = null;
				previewedArgs = null;
				setPreviewHtml(dialog, `<div class="alert alert-danger">${escapeHtml(error?.message || __("Replacement preview failed."))}</div>`);
			} finally {
				setBusy(dialog, false, onBusy, item.name);
			}
		});
	};

	const showConfirmAction = () => {
		dialog.set_primary_action(__("Confirm Replacement"), async (values) => {
			const currentArgs = replacementArgs(item, values);
			if (!previewPlan || !sameArgs(currentArgs, previewedArgs)) {
				frappe.msgprint({ title: __("Preview required again"), message: __("Replacement details changed after preview. Preview the current values again before confirming."), indicator: "orange" });
				showPreviewAction();
				return;
			}
			if (Number(previewPlan.conflict_count || 0) > 0) {
				frappe.msgprint({ title: __("Replacement conflicts"), message: __("Resolve all preview conflicts before confirming the handover."), indicator: "red" });
				return;
			}
			setBusy(dialog, true, onBusy, item.name);
			try {
				const response = await frappe.call({
					method: "eduedge.api.instructor_assignment_replacement.replace_instructor_assignment",
					type: "POST",
					args: currentArgs,
				});
				const result = response.message || {};
				frappe.show_alert({
					message: result.action === "already-replaced" ? __("Instructor Assignment was already replaced") : __("Instructor Assignment replaced and handed over"),
					indicator: "green",
				});
				dialog.hide();
				await onComplete?.(result);
			} catch (error) {
				frappe.msgprint({ title: __("Unable to replace assignment"), message: error?.message || __("Instructor Assignment could not be replaced."), indicator: "red" });
			} finally {
				setBusy(dialog, false, onBusy, item.name);
			}
		});
	};

	dialog = new frappe.ui.Dialog({
		title: __("Replace / Handover Instructor Assignment"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "assignment_summary",
				options: `<div class="mb-3"><strong>${title}</strong><br><span class="text-muted">${__("Handover Date is the outgoing Instructor's final responsibility day. The incoming Instructor starts the following day. The original assignment remains as history.")}</span></div>`,
			},
			{
				fieldtype: "Link",
				fieldname: "replacement_instructor",
				label: __("Replacement Instructor"),
				options: "Instructor",
				reqd: 1,
				get_query: () => ({ filters: { status: "Active", name: ["!=", item.instructor] } }),
				description: __("Only active Instructors available to your permissions can be selected."),
			},
			{
				fieldtype: "Date",
				fieldname: "handover_date",
				label: __("Handover Date"),
				reqd: 1,
				default: today,
				description: __("Final day of the outgoing responsibility. The successor starts the next calendar day."),
			},
			{
				fieldtype: "Small Text",
				fieldname: "reason",
				label: __("Reason"),
				reqd: 1,
				placeholder: __("Why is this responsibility being handed over?"),
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "HTML",
				fieldname: "replacement_preview",
				options: `<div class="text-muted">${__("Preview the handover before confirming.")}</div>`,
			},
		],
	});

	dialog.show();
	showPreviewAction();
	const handoverField = dialog.get_field("handover_date");
	if (handoverField?.$input) {
		handoverField.$input.attr("min", today);
		if (item.valid_to) handoverField.$input.attr("max", item.valid_to);
	}
}
