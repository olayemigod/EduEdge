const SCHOOL_BANK = "School Question Bank";
const PUBLIC_BANK = "EduEdge Examination Bank";
const BINARY_ANSWER_PRESETS = {
	"True/False": ["True", "False"],
	"Yes/No": ["Yes", "No"],
};
const CHOICE_TYPES = new Set(["Single Choice", "Multiple Choice"]);
const GENERATED_BINARY_ANSWERS = new Set(["", "true", "false", "yes", "no"]);

function optionLabel(position) {
	let value = Number(position || 0);
	let label = "";
	while (value > 0) {
		value -= 1;
		label = String.fromCharCode(65 + (value % 26)) + label;
		value = Math.floor(value / 26);
	}
	return label;
}

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

function supersededQuestionFilters(frm) {
	const filters = {
		status: ["in", ["Approved", "Retired"]],
		ownership_scope: frm.doc.ownership_scope,
		course: frm.doc.course,
	};
	if (frm.doc.ownership_scope === SCHOOL_BANK && frm.doc.school_branch) {
		filters.school_branch = frm.doc.school_branch;
	}
	return filters;
}

async function applyQuestionBankGovernance(frm) {
	const access = await getPublicExamAccess();
	const canAuthorPublic = Boolean(access.capabilities?.author?.allowed);
	frm.__can_author_public_exams = canAuthorPublic;
	frm.set_df_property(
		"ownership_scope",
		"options",
		canAuthorPublic ? `${SCHOOL_BANK}\n${PUBLIC_BANK}` : SCHOOL_BANK
	);
	if (frm.is_new() && !canAuthorPublic && frm.doc.ownership_scope !== SCHOOL_BANK) {
		await frm.set_value("ownership_scope", SCHOOL_BANK);
	}
	if (!canAuthorPublic && frm.doc.ownership_scope === PUBLIC_BANK) {
		frm.set_df_property("ownership_scope", "read_only", 1);
	}
}

function normaliseAnswerOptions(frm) {
	for (const [index, row] of (frm.doc.options || []).entries()) {
		row.option_key = optionLabel(index + 1);
		row.option_text = String(row.option_text || "").trim();
		row.display_order = index + 1;
	}
	frm.refresh_field("options");
}

function addPreparedAnswer(frm, answerText = "") {
	const row = frm.add_child("options");
	const position = (frm.doc.options || []).length;
	row.option_key = optionLabel(position);
	row.option_text = answerText;
	row.display_order = position;
	return row;
}

function matchesPreset(rows, preset) {
	if (rows.length !== preset.length) return false;
	return rows.every(
		(row, index) =>
			String(row.option_text || "").trim().toLowerCase() === preset[index].toLowerCase()
	);
}

function canReplaceWithBinaryPreset(rows) {
	if (!rows.length) return true;
	return rows.every((row) => {
		const answer = String(row.option_text || "").trim().toLowerCase();
		return GENERATED_BINARY_ANSWERS.has(answer) && !Number(row.is_correct || 0);
	});
}

function applyBinaryPreset(frm, preset) {
	frm.clear_table("options");
	for (const answerText of preset) {
		addPreparedAnswer(frm, answerText);
	}
	normaliseAnswerOptions(frm);
}

function ensureMinimumChoiceAnswers(frm) {
	while ((frm.doc.options || []).length < 2) {
		addPreparedAnswer(frm);
	}
	normaliseAnswerOptions(frm);
}

function prepareAnswerOptions(frm) {
	const questionType = frm.doc.question_type;
	const preset = BINARY_ANSWER_PRESETS[questionType];
	const rows = frm.doc.options || [];

	if (preset) {
		if (matchesPreset(rows, preset)) {
			normaliseAnswerOptions(frm);
			return;
		}
		if (canReplaceWithBinaryPreset(rows)) {
			applyBinaryPreset(frm, preset);
			return;
		}
		frappe.show_alert(
			{
				message: __(
					"Existing answers were kept. Clear them before applying the {0} answers."
				).replace("{0}", questionType),
				indicator: "orange",
			},
			7
		);
		return;
	}

	// A fresh question defaults to Single Choice without preloading answers.
	// These minimum rows are prepared only after the user explicitly changes
	// the Question Type to Single Choice or Multiple Choice.
	if (CHOICE_TYPES.has(questionType)) {
		ensureMinimumChoiceAnswers(frm);
	}
}

frappe.ui.form.on("EduEdge CBT Question", {
	setup(frm) {
		frm.set_query("school_branch", () => ({
			query: "eduedge.api.education.school_branch_query",
		}));
		frm.set_query("topic", () => ({
			query:
				"eduedge.eduedge.doctype.eduedge_cbt_question.eduedge_cbt_question.course_topic_query",
			filters: { course: frm.doc.course },
		}));
		frm.set_query("supersedes_question", () => ({ filters: supersededQuestionFilters(frm) }));
	},

	refresh(frm) {
		applyQuestionBankGovernance(frm).catch((error) => {
			console.error("Failed to resolve EduEdge public question bank access", error);
		});
	},

	validate(frm) {
		normaliseAnswerOptions(frm);
	},

	question_type(frm) {
		prepareAnswerOptions(frm);
	},

	async ownership_scope(frm) {
		await frm.set_value("supersedes_question", null);
		if (frm.doc.ownership_scope !== SCHOOL_BANK) {
			await frm.set_value("school_branch", null);
		}
	},

	async school_branch(frm) {
		await frm.set_value("supersedes_question", null);
	},

	async course(frm) {
		await frm.set_value("topic", null);
		await frm.set_value("supersedes_question", null);
	},

	async supersedes_question(frm) {
		if (!frm.doc.supersedes_question) return;
		const response = await frappe.db.get_value(
			"EduEdge CBT Question",
			frm.doc.supersedes_question,
			"version_number"
		);
		const previousVersion = Number(response?.message?.version_number || 0);
		if (previousVersion) {
			await frm.set_value("version_number", previousVersion + 1);
		}
	},
});

frappe.ui.form.on("EduEdge Question Option", {
	options_add(frm) {
		normaliseAnswerOptions(frm);
	},

	options_move(frm) {
		normaliseAnswerOptions(frm);
	},
});
