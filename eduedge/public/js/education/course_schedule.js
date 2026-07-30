function setCourseScheduleQueries(frm) {
	frm.set_query('student_group', () => ({
		query: 'eduedge.api.academic_operations.student_group_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			reference_date: frm.doc.schedule_date,
			program: frm.__eduedge_student_group_program || undefined,
		},
	}));
	frm.set_query('course', () => ({
		query: 'eduedge.api.academic_operations_review.course_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			program: frm.__eduedge_student_group_program || '',
			eduedge_academic_level: frm.__eduedge_student_group_level || '',
			academic_year: frm.__eduedge_student_group_year || '',
			academic_term: frm.__eduedge_student_group_term || '',
		},
	}));
	frm.set_query('instructor', () => ({
		query: 'eduedge.api.academic_operations.instructor_query',
		filters: { eduedge_school_branch: frm.doc.eduedge_school_branch, reference_date: frm.doc.schedule_date },
	}));
	frm.set_query('room', () => ({
		query: 'eduedge.api.academic_operations.room_query',
		filters: { eduedge_school_branch: frm.doc.eduedge_school_branch },
	}));
}

function clearCachedGroupContext(frm) {
	frm.__eduedge_student_group_program = '';
	frm.__eduedge_student_group_level = '';
	frm.__eduedge_student_group_year = '';
	frm.__eduedge_student_group_term = '';
}

async function applyStudentGroupContext(frm, { clearDependents = true } = {}) {
	if (!frm.doc.student_group) {
		clearCachedGroupContext(frm);
		if (clearDependents) await frm.set_value({ eduedge_school_branch: null, eduedge_academic_level: null, course: null, instructor: null, room: null });
		setCourseScheduleQueries(frm);
		return;
	}
	const selectedGroup = frm.doc.student_group;
	const { message } = await frappe.db.get_value('Student Group', selectedGroup, ['eduedge_school_branch', 'eduedge_academic_level', 'program', 'academic_year', 'academic_term', 'course']);
	if (frm.doc.student_group !== selectedGroup) return;
	frm.__eduedge_student_group_program = message?.program || '';
	frm.__eduedge_student_group_level = message?.eduedge_academic_level || '';
	frm.__eduedge_student_group_year = message?.academic_year || '';
	frm.__eduedge_student_group_term = message?.academic_term || '';
	const values = {
		eduedge_school_branch: message?.eduedge_school_branch || null,
		eduedge_academic_level: message?.eduedge_academic_level || null,
	};
	if (clearDependents) {
		values.course = message?.course || null;
		values.instructor = null;
		values.room = null;
	}
	await frm.set_value(values);
	setCourseScheduleQueries(frm);
}

frappe.ui.form.on('Course Schedule', {
	setup(frm) { setCourseScheduleQueries(frm); },
	refresh(frm) {
		frm.set_df_property('student_group', 'label', frappe.eduedge?.term?.('student_group', { fallback: __('Student Group / Class Arm / Lecture Group') }) || __('Student Group / Class Arm / Lecture Group'));
		frm.set_df_property('course', 'label', frappe.eduedge?.term?.('course', { fallback: __('Course / Subject') }) || __('Course / Subject'));
		frm.set_df_property('instructor', 'label', frappe.eduedge?.term?.('instructor', { fallback: __('Instructor') }) || __('Instructor'));
		frm.set_df_property('room', 'label', frappe.eduedge?.term?.('room', { fallback: __('Room') }) || __('Room'));
		if (frm.fields_dict.eduedge_academic_level) {
			frm.set_df_property('eduedge_academic_level', 'label', frappe.eduedge?.term?.('academic_level', { fallback: __('Academic Level') }) || __('Academic Level'));
			frm.set_df_property('eduedge_academic_level', 'read_only', 1);
		}
		if (frm.doc.student_group) applyStudentGroupContext(frm, { clearDependents: false });
		else setCourseScheduleQueries(frm);
	},
	student_group(frm) { applyStudentGroupContext(frm, { clearDependents: true }); },
	async schedule_date(frm) {
		clearCachedGroupContext(frm);
		await frm.set_value({ student_group: null, eduedge_academic_level: null, course: null, instructor: null, room: null, eduedge_school_branch: null });
		setCourseScheduleQueries(frm);
	},
	async eduedge_school_branch(frm) {
		if (frm.doc.student_group) {
			const { message } = await frappe.db.get_value('Student Group', frm.doc.student_group, 'eduedge_school_branch');
			if (message?.eduedge_school_branch !== frm.doc.eduedge_school_branch) {
				clearCachedGroupContext(frm);
				await frm.set_value({ student_group: null, eduedge_academic_level: null, course: null });
			}
		}
		await frm.set_value({ instructor: null, room: null });
		setCourseScheduleQueries(frm);
	},
});
