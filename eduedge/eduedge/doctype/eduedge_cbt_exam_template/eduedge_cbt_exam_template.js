const SCHOOL_EXAM = "School Examination";
const PUBLIC_EXAM = "EduEdge Public Examination";

function getPublicExamAccess() {
	if (!window.__eduedgePublicExamAccessPromise) {
		window.__eduedgePublicExamAccessPromise = frappe
			.call("eduedge.api.cbt.get_public_exam_access_context")
			.then((response) => response.message || {})
			.catch((error) => {
				window.__eduedgePublicExamAccessPromise = null;
				throw error;
			});
	}
	return window.__eduedgePublicExamAccessPromise;
}

async function applyTemplateScopeGovernance(frm) {
	const access = await getPublicExamAccess();
	const canAuthorPublic = Boolean(access.capabilities?.author?.allowed);
	frm.__can_author_public_exams = canAuthorPublic;
	frm.set_df_property(
		"exam_scope",
		"options",
		canAuthorPublic ? `${SCHOOL_EXAM}\n${PUBLIC_EXAM}` : SCHOOL_EXAM
	);
	if (frm.is_new() && !canAuthorPublic && frm.doc.exam_scope !== SCHOOL_EXAM) {
		await frm.set_value("exam_scope", SCHOOL_EXAM);
	}
	if (!canAuthorPublic && frm.doc.exam_scope === PUBLIC_EXAM) {
		frm.set_df_property("exam_scope", "read_only", 1);
	}
}

function clearQuestions(frm) {
	if (!(frm.doc.questions || []).length) return;
	frm.clear_table("questions");
	frm.refresh_field("questions");
	frm.set_value("question_count", 0);
	frm.set_value("total_marks", 0);
	frm.set_value("total_negative_marks", 0);
}

function clearStudentGroup(frm) {
	if (frm.doc.student_group) frm.set_value("student_group", null);
}

function clearSupersedesTemplate(frm) {
	if (frm.doc.supersedes_template) frm.set_value("supersedes_template", null);
}

function studentGroupFilters(frm) {
	const filters = { disabled: 0 };
	if (frm.doc.school_branch) filters.eduedge_school_branch = frm.doc.school_branch;
	if (frm.doc.academic_year) filters.academic_year = frm.doc.academic_year;
	if (frm.doc.academic_term) filters.academic_term = ["in", [frm.doc.academic_term, ""]];
	if (frm.doc.program) filters.program = frm.doc.program;
	if (frm.doc.course) filters.course = ["in", [frm.doc.course, ""]];
	return filters;
}

function supersedesTemplateFilters(frm) {
	const filters = {
		status: ["in", ["Approved", "Retired"]],
		exam_scope: frm.doc.exam_scope,
		course: frm.doc.course,
		exam_body: frm.doc.exam_body || "",
	};
	if (frm.doc.exam_scope === SCHOOL_EXAM && frm.doc.school_branch) {
		filters.school_branch = frm.doc.school_branch;
	}
	return filters;
}

function recalculateQuestionTotals(frm) {
	const rows = frm.doc.questions || [];
	frm.set_value("question_count", rows.length);
	frm.set_value(
		"total_marks",
		rows.reduce((total, row) => total + flt(row.mark), 0)
	);
	frm.set_value(
		"total_negative_marks",
		frm.doc.marking_policy === "Disable Negative Marking"
			? 0
			: rows.reduce((total, row) => total + flt(row.negative_mark), 0)
	);
}

frappe.ui.form.on("EduEdge CBT Exam Template", {
	setup(frm) {
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
		}));
		frm.set_query("academic_term", () => ({
			filters: { academic_year: frm.doc.academic_year },
		}));
		frm.set_query("student_group", () => ({ filters: studentGroupFilters(frm) }));
		frm.set_query("default_examination_centre", () => ({
			query: "eduedge.api.cbt.examination_centre_link_query",
			filters: {
				exam_scope: frm.doc.exam_scope,
				school_branch: frm.doc.school_branch,
			},
		}));
		frm.set_query("question", "questions", () => ({
			query: "eduedge.api.cbt.approved_question_query",
			filters: {
				exam_scope: frm.doc.exam_scope,
				school_branch: frm.doc.school_branch,
				course: frm.doc.course,
			},
		}));
		frm.set_query("supersedes_template", () => ({
			filters: supersedesTemplateFilters(frm),
		}));
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.exam_scope) {
			frm.set_value("exam_scope", SCHOOL_EXAM);
		}
	},

	refresh(frm) {
		applyTemplateScopeGovernance(frm).catch((error) => {
			console.error("Failed to resolve EduEdge public exam template access", error);
		});
	},

	exam_scope(frm) {
		frm.set_value("default_examination_centre", null);
		clearSupersedesTemplate(frm);
		clearQuestions(frm);
		if (frm.doc.exam_scope !== SCHOOL_EXAM) {
			frm.set_value("school_branch", null);
			frm.set_value("academic_year", null);
			frm.set_value("academic_term", null);
			frm.set_value("program", null);
			frm.set_value("student_group", null);
			frm.set_value("assessment_group", null);
		}
	},

	school_branch(frm) {
		frm.set_value("default_examination_centre", null);
		clearSupersedesTemplate(frm);
		clearStudentGroup(frm);
		clearQuestions(frm);
	},

	academic_year(frm) {
		if (frm.doc.academic_term) frm.set_value("academic_term", null);
		clearStudentGroup(frm);
	},

	academic_term(frm) {
		clearStudentGroup(frm);
	},

	program(frm) {
		clearStudentGroup(frm);
	},

	course(frm) {
		clearSupersedesTemplate(frm);
		clearStudentGroup(frm);
		clearQuestions(frm);
	},

	exam_body(frm) {
		clearSupersedesTemplate(frm);
	},

	marking_policy(frm) {
		recalculateQuestionTotals(frm);
	},
});

frappe.ui.form.on("EduEdge CBT Template Question", {
	questions_add(frm) {
		recalculateQuestionTotals(frm);
	},

	questions_remove(frm) {
		recalculateQuestionTotals(frm);
	},

	async question(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.question) {
			await frappe.model.set_value(cdt, cdn, "question_type", "");
			await frappe.model.set_value(cdt, cdn, "topic", "");
			await frappe.model.set_value(cdt, cdn, "mark", 0);
			await frappe.model.set_value(cdt, cdn, "negative_mark", 0);
			recalculateQuestionTotals(frm);
			return;
		}
		const response = await frappe.db.get_value("EduEdge CBT Question", row.question, [
			"question_type",
			"topic",
			"default_mark",
			"negative_mark",
		]);
		const values = response.message || {};
		await frappe.model.set_value(cdt, cdn, "question_type", values.question_type || "");
		await frappe.model.set_value(cdt, cdn, "topic", values.topic || "");
		await frappe.model.set_value(cdt, cdn, "mark", flt(values.default_mark));
		await frappe.model.set_value(cdt, cdn, "negative_mark", flt(values.negative_mark));
		recalculateQuestionTotals(frm);
	},

	display_order(frm) {
		recalculateQuestionTotals(frm);
	},
});
