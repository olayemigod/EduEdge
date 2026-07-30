function setEnrollmentQueries(frm) {
	frm.set_query('eduedge_school_branch', () => ({
		query: 'eduedge.api.education.school_branch_query',
	}));
	frm.set_query('student', () => ({
		query: 'eduedge.api.education.student_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			allow_cross_branch: 1,
		},
	}));
	frm.set_query('program', () => ({
		query: 'eduedge.api.education.program_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			purpose: 'enrollment',
		},
	}));
	frm.set_query('eduedge_program_offering', () => ({
		query: 'eduedge.api.academic_context.program_offering_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.doc.program,
			eduedge_academic_level: frm.doc.eduedge_academic_level,
			academic_year: frm.doc.academic_year,
			academic_term: frm.doc.academic_term,
			purpose: 'enrollment',
		},
	}));
}

function updateEnrollmentContextLocks(frm) {
	const locked = Boolean(frm.doc.eduedge_program_offering) || frm.doc.docstatus !== 0;
	for (const fieldname of ['eduedge_school_branch', 'eduedge_academic_level']) {
		if (frm.fields_dict[fieldname]) frm.set_df_property(fieldname, 'read_only', locked ? 1 : 0);
	}
}

async function applyOffering(frm) {
	if (!frm.doc.eduedge_program_offering) {
		updateEnrollmentContextLocks(frm);
		return;
	}
	const selectedOffering = frm.doc.eduedge_program_offering;
	frm.__eduedge_applying_offering = true;
	try {
		const { message } = await frappe.call('eduedge.api.academic_context.get_programme_offering_context', {
			offering: selectedOffering,
		});
		if (!message || frm.doc.eduedge_program_offering !== selectedOffering) return;
		await frappe.model.set_value(frm.doctype, frm.docname, {
			eduedge_school_branch: message.school_branch || null,
			eduedge_institution: message.institution || null,
			program: message.program || null,
			academic_year: message.academic_year || null,
			academic_term: message.academic_term || null,
			student_batch_name: message.student_batch || null,
			eduedge_academic_level: message.eduedge_academic_level || message.academic_level || null,
		});
		setEnrollmentQueries(frm);
	} finally {
		frm.__eduedge_applying_offering = false;
		updateEnrollmentContextLocks(frm);
	}
}

function candidateRows(payload, outcome) {
	if (outcome === 'Promote') return payload.promotion_offerings || [];
	if (outcome === 'Repeat') return payload.repeat_offerings || [];
	if (outcome === 'Transfer') return payload.transfer_offerings || [];
	return [];
}

function offeringLabel(row) {
	return [
		row.offering_title || row.name,
		row.academic_level,
		row.academic_year,
		row.academic_term,
		row.school_branch,
	].filter(Boolean).join(' · ');
}

function renderCandidateHelp(rows) {
	if (!rows.length) return '<p class="text-muted">No eligible target Programme Offering is configured.</p>';
	return `<div class="small text-muted">${rows.slice(0, 20).map((row) => `<div><strong>${frappe.utils.escape_html(row.name)}</strong> — ${frappe.utils.escape_html(offeringLabel(row))}</div>`).join('')}</div>`;
}

async function openProgressionDialog(frm) {
	const { message: payload } = await frappe.call('eduedge.api.progression_workflow.get_progression_options', {
		program_enrollment: frm.doc.name,
	});
	if (!payload) return;
	const outcomes = payload.outcomes || [];
	if (!outcomes.length) {
		frappe.msgprint({ title: __('Enrollment Progression'), message: __('No further lifecycle action is available from status {0}.', [payload.current_status]), indicator: 'blue' });
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __('Manage Enrollment Progression'),
		fields: [
			{ fieldname: 'current_context', fieldtype: 'HTML', options: `<p><strong>${frappe.utils.escape_html(payload.source.student_name || payload.source.student)}</strong><br>${frappe.utils.escape_html([payload.source.program, payload.source.academic_level, payload.source.academic_year, payload.source.academic_term].filter(Boolean).join(' · '))}<br><span class="text-muted">Current status: ${frappe.utils.escape_html(payload.current_status)}</span></p>` },
			{ fieldname: 'outcome', fieldtype: 'Select', label: __('Outcome'), options: outcomes.join('\n'), reqd: 1 },
			{ fieldname: 'target_program_offering', fieldtype: 'Select', label: __('Target Programme Offering') },
			{ fieldname: 'candidate_help', fieldtype: 'HTML' },
			{ fieldname: 'reason', fieldtype: 'Small Text', label: __('Reason / Approval Note'), reqd: 1 },
			{ fieldname: 'effective_date', fieldtype: 'Date', label: __('Effective Date'), default: frappe.datetime.get_today() },
		],
		primary_action_label: __('Continue'),
		async primary_action(values) {
			const targetOutcome = ['Promote', 'Repeat', 'Transfer'].includes(values.outcome);
			if (targetOutcome && !values.target_program_offering) {
				frappe.msgprint(__('Select a target Programme Offering.'));
				return;
			}
			dialog.get_primary_btn().prop('disabled', true);
			try {
				if (targetOutcome) {
					const { message } = await frappe.call('eduedge.api.progression_workflow.create_progression_draft', {
						program_enrollment: frm.doc.name,
						outcome: values.outcome,
						target_program_offering: values.target_program_offering,
						reason: values.reason,
					});
					dialog.hide();
					frappe.show_alert({ message: message.created ? __('Target enrollment draft created') : __('Existing progression draft opened'), indicator: 'green' });
					frappe.set_route('Form', 'Program Enrollment', message.name);
				} else {
					await frappe.call('eduedge.api.progression_workflow.record_enrollment_outcome', {
						program_enrollment: frm.doc.name,
						outcome: values.outcome,
						reason: values.reason,
						effective_date: values.effective_date || frappe.datetime.get_today(),
					});
					dialog.hide();
					await frm.reload_doc();
					frappe.show_alert({ message: __('Enrollment status recorded'), indicator: 'green' });
				}
			} finally {
				dialog.get_primary_btn().prop('disabled', false);
			}
		},
	});
	function refreshOutcome() {
		const outcome = dialog.get_value('outcome');
		const rows = candidateRows(payload, outcome);
		const targetRequired = ['Promote', 'Repeat', 'Transfer'].includes(outcome);
		dialog.set_df_property('target_program_offering', 'hidden', targetRequired ? 0 : 1);
		dialog.set_df_property('target_program_offering', 'reqd', targetRequired ? 1 : 0);
		dialog.set_df_property('target_program_offering', 'options', ['', ...rows.map((row) => row.name)].join('\n'));
		dialog.set_value('target_program_offering', '');
		dialog.fields_dict.candidate_help.$wrapper.html(targetRequired ? renderCandidateHelp(rows) : '<p class="text-muted">This outcome records an append-only status change and does not create another enrollment.</p>');
		dialog.refresh();
	}
	dialog.fields_dict.outcome.df.onchange = refreshOutcome;
	dialog.set_value('outcome', outcomes[0]);
	refreshOutcome();
	dialog.show();
}

function addProgressionActions(frm) {
	if (frm.doc.docstatus === 1 && !frm.doc.eduedge_progression_source_enrollment) {
		frm.add_custom_button(__('Manage Progression / Status'), () => openProgressionDialog(frm), __('Enrollment'));
	}
	if (frm.doc.eduedge_progression_source_enrollment) {
		frm.add_custom_button(__('Open Source Enrollment'), () => frappe.set_route('Form', 'Program Enrollment', frm.doc.eduedge_progression_source_enrollment), __('Progression'));
		if (frm.doc.docstatus === 1 && frappe.model.can_create('EduEdge Enrollment Status Log')) {
			frm.add_custom_button(__('Finalize Progression'), async () => {
				frappe.confirm(
					__('Finalize {0} and record the source enrollment lifecycle status?', [frm.doc.eduedge_progression_outcome || __('progression')]),
					async () => {
						await frappe.call('eduedge.api.progression_workflow.finalize_progression', {
							program_enrollment: frm.doc.eduedge_progression_source_enrollment,
							target_program_enrollment: frm.doc.name,
							outcome: frm.doc.eduedge_progression_outcome,
							reason: frm.doc.eduedge_progression_reason || __('Approved progression'),
							effective_date: frappe.datetime.get_today(),
						});
						frappe.show_alert({ message: __('Progression finalized'), indicator: 'green' });
						frappe.set_route('Form', 'Program Enrollment', frm.doc.eduedge_progression_source_enrollment);
					},
				);
			}, __('Progression'));
		}
	}
	frm.add_custom_button(__('View Status History'), () => {
		frappe.set_route('List', 'EduEdge Enrollment Status Log', { program_enrollment: frm.doc.eduedge_progression_source_enrollment || frm.doc.name });
	}, __('Enrollment'));
}

frappe.ui.form.on('Program Enrollment', {
	setup(frm) { setEnrollmentQueries(frm); },
	onload(frm) {
		if (!frm.is_new() || frm.doc.eduedge_school_branch) return;
		frappe.call('eduedge.api.branch_context.get_current_school_branch').then(({ message }) => {
			if (message?.name && !frm.doc.eduedge_school_branch) frm.set_value('eduedge_school_branch', message.name);
		});
	},
	refresh(frm) {
		frm.set_df_property('eduedge_program_offering', 'label', frappe.eduedge?.term?.('programme_offering', { fallback: __('Programme Offering') }) || __('Programme Offering'));
		frm.set_df_property('program', 'label', frappe.eduedge?.term?.('programme', { fallback: __('Program') }) || __('Program'));
		frm.set_df_property('eduedge_academic_level', 'label', frappe.eduedge?.term?.('academic_level', { fallback: __('Academic Level') }) || __('Academic Level'));
		updateEnrollmentContextLocks(frm);
		addProgressionActions(frm);
	},
	async student(frm) {
		if (!frm.doc.student) { setEnrollmentQueries(frm); return; }
		if (!frm.doc.eduedge_program_offering && !frm.doc.eduedge_school_branch) {
			const { message } = await frappe.db.get_value('Student', frm.doc.student, 'eduedge_school_branch');
			if (message?.eduedge_school_branch) await frm.set_value('eduedge_school_branch', message.eduedge_school_branch);
		}
		setEnrollmentQueries(frm);
	},
	eduedge_program_offering(frm) { applyOffering(frm); },
	academic_year(frm) { if (!frm.__eduedge_applying_offering && !frm.doc.eduedge_program_offering) frm.set_value('academic_term', null); setEnrollmentQueries(frm); },
	academic_term(frm) { setEnrollmentQueries(frm); },
	program(frm) { if (!frm.__eduedge_applying_offering) frm.set_value('eduedge_academic_level', null); setEnrollmentQueries(frm); },
	eduedge_academic_level(frm) { setEnrollmentQueries(frm); },
	eduedge_school_branch(frm) {
		if (frm.__eduedge_applying_offering) return;
		if (frm.doc.eduedge_program_offering) frm.set_value('eduedge_program_offering', null);
		frm.set_value({ program: null, eduedge_academic_level: null });
		setEnrollmentQueries(frm);
		updateEnrollmentContextLocks(frm);
	},
});
