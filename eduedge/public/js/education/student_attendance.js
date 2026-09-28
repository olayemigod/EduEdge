function setStudentAttendanceQueries(frm) {
	frm.set_query('course_schedule', () => ({
		query: 'eduedge.api.academic_operations_review.student_attendance_course_schedule_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			student_group: frm.doc.student_group,
			reference_date: frm.doc.date,
		},
	}));
	frm.set_query('student_group', () => ({
		query: 'eduedge.api.academic_operations.student_group_query',
		filters: {
			eduedge_school_branch: frm.doc.eduedge_school_branch,
			reference_date: frm.doc.date,
		},
	}));
	frm.set_query('student', () => ({
		query: 'eduedge.api.academic_operations.student_group_member_query',
		filters: {
			student_group: frm.doc.student_group,
		},
	}));
}

async function getAttendanceScheduleContext(frm) {
	if (!frm.doc.course_schedule) return null;
	const selectedSchedule = frm.doc.course_schedule;
	const { message } = await frappe.db.get_value(
		'Course Schedule',
		selectedSchedule,
		['student_group', 'schedule_date', 'eduedge_school_branch']
	);
	if (frm.doc.course_schedule !== selectedSchedule) return null;
	return message || null;
}

async function applyAttendanceScheduleContext(frm) {
	if (!frm.doc.course_schedule) {
		setStudentAttendanceQueries(frm);
		return;
	}
	const message = await getAttendanceScheduleContext(frm);
	if (!message) return;
	const nextGroup = message.student_group || null;
	const groupChanged = (frm.doc.student_group || null) !== nextGroup;
	frm.__eduedge_applying_attendance_schedule = true;
	try {
		await frm.set_value({
			student_group: nextGroup,
			date: message.schedule_date || null,
			eduedge_school_branch: message.eduedge_school_branch || null,
		});
		if (groupChanged) await frm.set_value('student', null);
	} finally {
		frm.__eduedge_applying_attendance_schedule = false;
	}
	setStudentAttendanceQueries(frm);
}

async function clearInvalidAttendanceSchedule(frm, fieldname) {
	if (frm.__eduedge_applying_attendance_schedule || !frm.doc.course_schedule) {
		setStudentAttendanceQueries(frm);
		return;
	}
	const message = await getAttendanceScheduleContext(frm);
	if (!message) return;
	const invalid = fieldname === 'student_group'
		? (frm.doc.student_group || null) !== (message.student_group || null)
		: String(frm.doc.date || '') !== String(message.schedule_date || '');
	if (invalid) await frm.set_value('course_schedule', null);
	setStudentAttendanceQueries(frm);
}

frappe.ui.form.on('Student Attendance', {
	setup(frm) {
		setStudentAttendanceQueries(frm);
	},
	refresh(frm) {
		setStudentAttendanceQueries(frm);
	},
	course_schedule(frm) {
		applyAttendanceScheduleContext(frm);
	},
	async student_group(frm) {
		if (!frm.__eduedge_applying_attendance_schedule) {
			await frm.set_value('student', null);
		}
		await clearInvalidAttendanceSchedule(frm, 'student_group');
	},
	async date(frm) {
		await clearInvalidAttendanceSchedule(frm, 'date');
	},
});
