<template>
	<EdgeAppShell product="eduedge" title="EduEdge" :tenant-name="context.tenant_name || ''" :branch-name="branchLabel" :user-name="context.user?.full_name || ''" :menu-items="menuItems" active-route="/app/eduedge-question-builder" @navigate="openRoute">
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader eyebrow="CBT Question Bank" :title="builderTitle" :subtitle="builderSubtitle" action-label="Back to CBT Operations" @action="openRoute('/app/eduedge-cbt-operations')" />
			</template>
			<EdgeLoadingState v-if="loading" message="Loading Question Builder..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Question Builder could not load" :message="error" action-label="Try again" @retry="loadBuilder" />
			<template v-else>
				<section class="question-summary"><div><p class="edge-eyebrow">Question governance</p><strong>{{ form.question_code || 'Unsaved question' }}</strong><span v-if="form.name">Version {{ form.version_number || 1 }}</span></div><EdgeStatusBadge :label="form.status || 'Draft'" :status="form.status || 'Draft'" :tone="statusTone" /></section>

				<section class="question-panel">
					<div class="panel-heading"><div><p class="edge-eyebrow">Academic classification</p><h2>Question identity</h2><p>Classify the question against the assigned Branch, Class, Class Arm, Subject and Topic.</p></div></div>
					<div class="question-fields">
						<label><span>Question Code *</span><input v-model.trim="form.question_code" class="form-control" placeholder="e.g. MATH-JSS1-001" :disabled="isReadOnly || Boolean(form.name)" /><small v-if="form.name">The code is fixed after the first save.</small></label>
						<label><span>Question Bank *</span><select v-model="form.ownership_scope" class="form-control" :disabled="isReadOnly" @change="scopeChanged"><option v-for="option in context.scope_options" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>

						<label v-if="isSchoolQuestion"><span>School Branch / Campus *</span><select v-model="form.school_branch" class="form-control" :disabled="isReadOnly" @change="branchChanged"><option value="">Select branch</option><option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">{{ branch.branch_name || branch.name }}</option></select></label>
						<label v-if="isSchoolQuestion"><span>Class / Programme Offering <b v-if="context.permissions?.is_assigned_teacher">*</b></span><select v-model="form.program_offering" class="form-control" :disabled="isReadOnly || !form.school_branch" @change="offeringChanged"><option value="">{{ context.permissions?.is_assigned_teacher ? 'Select assigned Class' : 'Branch-wide question' }}</option><option v-for="row in context.offerings" :key="row.name" :value="row.name">{{ row.offering_title || row.name }} · {{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }}</option></select></label>
						<label v-if="isSchoolQuestion && form.program_offering"><span>Class Arm / Student Group</span><select v-model="form.student_group" class="form-control" :disabled="isReadOnly" @change="groupChanged"><option value="">Class-wide / all Class Arms</option><option v-for="row in context.groups" :key="row.name" :value="row.name">{{ row.eduedge_display_name || row.student_group_name || row.name }}</option></select></label>

						<div class="lookup-field"><span>Subject / Course *</span><input v-model="courseQuery" class="form-control" placeholder="Search assigned subject or course" autocomplete="off" :disabled="isReadOnly || (isSchoolQuestion && context.permissions?.is_assigned_teacher && !form.program_offering)" @focus="searchCourses" @input="scheduleCourseSearch" /><div v-if="courseSuggestions.length && !isReadOnly" class="suggestions"><button v-for="course in courseSuggestions" :key="course.value" type="button" @click="selectCourse(course)">{{ course.label }}</button></div><small v-if="form.course">Selected: {{ form.course }}</small></div>
						<label><span>Topic</span><select v-model="form.topic" class="form-control" :disabled="isReadOnly || !form.course"><option value="">No topic selected</option><option v-for="topic in topicOptions" :key="topic.value" :value="topic.value">{{ topic.label }}</option></select><small>Only Topics configured under the selected Course are shown.</small></label>
						<label><span>Curriculum / Syllabus</span><input v-model.trim="form.curriculum" class="form-control" placeholder="Optional syllabus reference" :disabled="isReadOnly" /></label>
						<label><span>Exam Body / Source Type</span><select v-model="form.exam_body" class="form-control" :disabled="isReadOnly"><option v-for="body in context.exam_bodies" :key="body" :value="body">{{ body }}</option></select></label>
						<label><span>Difficulty *</span><select v-model="form.difficulty" class="form-control" :disabled="isReadOnly"><option value="">Select difficulty</option><option v-for="difficulty in context.difficulties" :key="difficulty" :value="difficulty">{{ difficulty }}</option></select></label>
					</div>
					<EdgeActionBar v-if="isSchoolQuestion && context.permissions?.is_assigned_teacher" :label="form.program_offering ? `Subject choices are limited to your active Teacher Assignment for this ${form.student_group ? 'Class Arm' : 'Class'}.` : 'Select an assigned Class before choosing a Subject.'" />
				</section>

				<section class="question-panel">
					<div class="panel-heading"><div><p class="edge-eyebrow">Question and answer</p><h2>Build the question</h2><p>Enter candidate-facing content and the protected answer or marking guide.</p></div></div>
					<label><span>Question Type *</span><select v-model="form.question_type" class="form-control" :disabled="isReadOnly" @change="questionTypeChanged"><option v-for="type in context.question_types" :key="type" :value="type">{{ type }}</option></select></label>
					<div class="question-editor-field"><span>Question *</span><div class="question-editor" :class="{ 'is-read-only': isReadOnly }" :contenteditable="isReadOnly ? 'false' : 'true'" v-html="form.question_text" @input="questionTextChanged"></div></div>

					<div v-if="isObjective" class="answer-builder">
						<div class="answer-heading"><div><strong>Answer Choices</strong><span>{{ answerGuidance }}</span></div><button v-if="!isReadOnly && !isBinary" type="button" class="edge-button" @click="addAnswer">Add Answer</button></div>
						<EdgeEmptyState v-if="!form.options.length" title="No answers added" description="Add at least two answer choices and mark the Correct Answer." />
						<div v-else class="answer-list">
							<div v-for="(answer,index) in form.options" :key="answer.local_id || index" class="answer-row">
								<div class="answer-label">{{ optionLabel(index + 1) }}</div>
								<textarea v-model="answer.option_text" class="form-control" rows="2" placeholder="Enter answer shown to candidates" :disabled="isReadOnly || isBinary"></textarea>
								<label class="correct-choice"><input :type="isMultipleChoice ? 'checkbox' : 'radio'" name="eduedge-correct-answer" :checked="Boolean(Number(answer.is_correct))" :disabled="isReadOnly" @change="correctAnswerChanged(index, $event.target.checked)" /><span>Correct Answer</span></label>
								<div v-if="!isReadOnly && !isBinary" class="answer-actions"><button type="button" title="Move answer up" :disabled="index === 0" @click="moveAnswer(index, -1)">↑</button><button type="button" title="Move answer down" :disabled="index === form.options.length - 1" @click="moveAnswer(index, 1)">↓</button><button type="button" title="Remove answer" @click="removeAnswer(index)">×</button></div>
							</div>
						</div>
					</div>
					<label v-if="usesAnswerKey"><span>Answer Key *</span><textarea v-model="form.answer_key" class="form-control" rows="3" :disabled="isReadOnly"></textarea></label>
					<label><span>Marking Guide <b v-if="form.question_type === 'Essay'">*</b></span><textarea v-model="form.marking_guide" class="form-control" rows="4" :disabled="isReadOnly"></textarea></label>
					<div class="marks-grid"><label><span>Default Mark *</span><input v-model.number="form.default_mark" type="number" min="0.01" step="0.25" class="form-control" :disabled="isReadOnly" /></label><label><span>Negative Mark</span><input v-model.number="form.negative_mark" type="number" min="0" step="0.25" class="form-control" :disabled="isReadOnly" /></label></div>
					<label><span>Internal Notes</span><textarea v-model="form.notes" class="form-control" rows="3" :disabled="isReadOnly"></textarea></label>
				</section>

				<p v-if="saveError" class="question-error">{{ saveError }}</p>
				<EdgeActionBar :label="actionGuidance">
					<template #actions>
						<button v-if="!isReadOnly && editableStatus" type="button" class="edge-button" :disabled="saving || !canSave" @click="saveAs('Draft')">Save Draft</button>
						<button v-if="!isReadOnly && editableStatus" type="button" class="edge-button edge-button--primary" :disabled="saving || !canSave" @click="saveAs('Under Review')">Send for Review</button>
						<button v-if="form.status === 'Under Review' && context.permissions?.can_review" type="button" class="edge-button edge-button--primary" :disabled="saving" @click="saveAs('Approved')">Approve Question</button>
						<button v-if="form.status === 'Approved' && context.permissions?.can_review" type="button" class="edge-button" :disabled="saving" @click="saveAs('Retired')">Retire Question</button>
						<button v-if="context.permissions?.can_create_version" type="button" class="edge-button edge-button--primary" :disabled="saving" @click="createVersion">Create New Version</button>
						<button v-if="form.name && context.permissions?.can_open_technical_record" type="button" class="edge-button" @click="openTechnicalRecord">Open Technical Record</button>
					</template>
				</EdgeActionBar>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const SCHOOL_BANK = "School Question Bank";
const BINARY_PRESETS = {
	"True/False": ["True", "False"],
	"Yes/No": ["Yes", "No"],
};
const CHOICE_TYPES = new Set(["Single Choice", "Multiple Choice"]);
const OBJECTIVE_TYPES = new Set([...CHOICE_TYPES, ...Object.keys(BINARY_PRESETS)]);

function blankQuestion() {
	return {
		name: null, question_code: "", ownership_scope: SCHOOL_BANK, school_branch: "", institution: "",
		program_offering: "", student_group: "", version_number: 1, supersedes_question: "",
		course: "", course_label: "", topic: "", topic_label: "", curriculum: "", exam_body: "School Internal",
		difficulty: "", question_type: "Single Choice", question_text: "", options: [], answer_key: "",
		marking_guide: "", default_mark: 1, negative_mark: 0, status: "Draft", notes: "",
	};
}

export default {
	name: "EduEdgeQuestionBuilder",
	props: { pageName: { type: String, default: "eduedge-question-builder" }, questionName: { type: String, default: null } },
	data() { return { loading: true, saving: false, error: "", saveError: "", menuItems: EDUEDGE_MENU_ITEMS, currentQuestionName: this.questionName || null, courseQuery: "", courseSuggestions: [], topicOptions: [], courseTimer: null, previousQuestionType: "Single Choice", context: { user: {}, current_branch: null, allowed_branches: [], offerings: [], groups: [], scope_options: [{ value: SCHOOL_BANK, label: SCHOOL_BANK }], question_types: [], difficulties: [], exam_bodies: [], permissions: {} }, form: blankQuestion() }; },
	computed: {
		builderTitle() { return this.form.name ? `Edit ${this.form.question_code || this.form.name}` : "Create CBT Question"; },
		builderSubtitle() { if (this.form.status === "Approved") return "Approved content is protected. Create a new version to revise it."; if (this.form.status === "Retired") return "This question is retained for audit history and can start a new version."; return "Create clear, reusable questions in the correct Class and Subject context."; },
		branchLabel() { return this.context.allowed_branches.find((row) => row.name === this.form.school_branch)?.branch_name || this.context.current_branch?.branch_name || "Question Bank"; },
		isReadOnly() { return !Boolean(this.context.permissions?.can_write); }, isSchoolQuestion() { return this.form.ownership_scope === SCHOOL_BANK; },
		isObjective() { return OBJECTIVE_TYPES.has(this.form.question_type); }, isBinary() { return Boolean(BINARY_PRESETS[this.form.question_type]); }, isMultipleChoice() { return this.form.question_type === "Multiple Choice"; }, usesAnswerKey() { return ["Short Answer", "Numeric"].includes(this.form.question_type); }, editableStatus() { return ["Draft", "Changes Requested"].includes(this.form.status); },
		statusTone() { if (this.form.status === "Approved") return "success"; if (this.form.status === "Under Review") return "warning"; if (this.form.status === "Retired") return "danger"; return "neutral"; },
		answerGuidance() { if (this.isBinary) return "Select the one correct answer."; if (this.isMultipleChoice) return "Add at least two answers and mark every Correct Answer."; return "Add at least two answers and mark exactly one Correct Answer."; },
		actionGuidance() { if (this.form.status === "Approved") return "Approved questions are immutable. Retire them or create a new version."; if (this.form.status === "Retired") return "Retired questions remain available for historical exam records."; return "Saving uses governed permissions, Branch isolation, Teacher Assignment and server validation."; },
		canSave() { if (!this.form.question_code || !this.form.course || !this.form.difficulty || !String(this.form.question_text || "").replace(/<[^>]*>/g, "").trim()) return false; if (this.isSchoolQuestion && !this.form.school_branch) return false; if (this.isSchoolQuestion && this.context.permissions?.is_assigned_teacher && !this.form.program_offering) return false; if (this.isObjective) { if (this.form.options.length < 2) return false; const correct = this.form.options.filter((row) => Number(row.is_correct)).length; if (this.isMultipleChoice ? correct < 1 : correct !== 1) return false; } if (this.usesAnswerKey && !String(this.form.answer_key || "").trim()) return false; if (this.form.question_type === "Essay" && !String(this.form.marking_guide || "").trim()) return false; return Number(this.form.default_mark) > 0 && Number(this.form.negative_mark || 0) <= Number(this.form.default_mark); },
	},
	mounted() { this.loadBuilder(); }, beforeUnmount() { if (this.courseTimer) window.clearTimeout(this.courseTimer); },
	methods: {
		openRoute: openEduEdgeRoute,
		optionLabel(position) { let value = Number(position || 0); let label = ""; while (value > 0) { value -= 1; label = String.fromCharCode(65 + (value % 26)) + label; value = Math.floor(value / 26); } return label; },
		questionTextChanged(event) { this.form.question_text = event.target.innerHTML; this.saveError = ""; },
		async loadBuilder() { this.loading = true; this.error = ""; try { const response = await frappe.call("eduedge.api.question_builder.get_question_builder_context", { question: this.currentQuestionName || undefined }); await this.applyState(response.message || {}); } catch (error) { this.error = error?.message || "Question Builder could not be loaded."; } finally { this.loading = false; } },
		async applyState(state) { this.context = { ...this.context, ...state }; this.form = { ...blankQuestion(), ...(state.question || {}) }; this.form.options = (this.form.options || []).map((row,index) => ({ ...row, local_id: `${Date.now()}-${index}` })); this.currentQuestionName = this.form.name || null; this.courseQuery = this.form.course_label || this.form.course || ""; this.previousQuestionType = this.form.question_type || "Single Choice"; this.courseSuggestions = []; await this.loadTopics(); this.saveError = ""; },
		async refreshAcademicOptions() { if (!this.form.school_branch) { this.context.offerings = []; this.context.groups = []; return; } const response = await frappe.call("eduedge.api.question_builder.get_question_academic_options", { branch: this.form.school_branch, program_offering: this.form.program_offering || undefined }); const result = response.message || {}; this.context.offerings = result.offerings || []; this.context.groups = result.groups || []; this.form.institution = result.institution || ""; },
		async branchChanged() { this.form.program_offering = ""; this.form.student_group = ""; this.clearCourse(); await this.refreshAcademicOptions(); },
		async offeringChanged() { this.form.student_group = ""; this.clearCourse(); await this.refreshAcademicOptions(); },
		groupChanged() { this.clearCourse(); },
		clearCourse() { this.form.course = ""; this.form.course_label = ""; this.courseQuery = ""; this.form.topic = ""; this.topicOptions = []; this.courseSuggestions = []; },
		scopeChanged() { if (!this.isSchoolQuestion) { this.form.school_branch = ""; this.form.institution = ""; this.form.program_offering = ""; this.form.student_group = ""; this.context.offerings = []; this.context.groups = []; } else if (!this.form.school_branch) this.form.school_branch = this.context.current_branch?.name || ""; this.clearCourse(); if (this.isSchoolQuestion) this.refreshAcademicOptions(); },
		scheduleCourseSearch() { this.form.course = ""; this.form.topic = ""; this.topicOptions = []; if (this.courseTimer) window.clearTimeout(this.courseTimer); this.courseTimer = window.setTimeout(() => this.searchCourses(), 250); },
		async searchCourses() { if (this.isReadOnly) return; try { const response = await frappe.call("eduedge.api.question_builder.search_courses", { txt: this.courseQuery || "", page_len: 20, branch: this.form.school_branch || undefined, program_offering: this.form.program_offering || undefined, student_group: this.form.student_group || undefined }); this.courseSuggestions = response.message || []; } catch (error) { this.saveError = error?.message || "Courses could not be loaded."; } },
		async selectCourse(course) { this.form.course = course.value; this.form.course_label = course.label; this.courseQuery = course.label; this.courseSuggestions = []; this.form.topic = ""; await this.loadTopics(); },
		async loadTopics() { if (!this.form.course) { this.topicOptions = []; return; } try { const response = await frappe.call("eduedge.api.question_builder.search_topics", { course: this.form.course, txt: "", page_len: 100, program_offering: this.form.program_offering || undefined, student_group: this.form.student_group || undefined }); this.topicOptions = response.message || []; if (this.form.topic && !this.topicOptions.some((topic) => topic.value === this.form.topic)) this.topicOptions.unshift({ value: this.form.topic, label: this.form.topic_label || this.form.topic }); } catch (error) { this.topicOptions = []; this.saveError = error?.message || "Topics could not be loaded."; } },
		questionTypeChanged() { const nextType = this.form.question_type; const previousType = this.previousQuestionType; const existingAnswers = (this.form.options || []).some((row) => String(row.option_text || "").trim()); const apply = () => { this.applyQuestionType(nextType); this.previousQuestionType = nextType; }; const revert = () => { this.form.question_type = previousType; }; if (existingAnswers && (BINARY_PRESETS[nextType] || !OBJECTIVE_TYPES.has(nextType))) { frappe.confirm(__("Changing the Question Type will replace or remove the current answers. Continue?"), apply, revert); return; } apply(); },
		applyQuestionType(type) { const preset = BINARY_PRESETS[type]; if (preset) { this.form.options = preset.map((answer,index) => ({ local_id: `${Date.now()}-${index}`, option_key: this.optionLabel(index + 1), option_text: answer, is_correct: 0, display_order: index + 1 })); return; } if (CHOICE_TYPES.has(type)) { while (this.form.options.length < 2) this.addAnswer(); if (type === "Single Choice") { let found = false; this.form.options.forEach((row) => { if (Number(row.is_correct) && !found) found = true; else if (Number(row.is_correct)) row.is_correct = 0; }); } return; } this.form.options = []; },
		addAnswer() { if (this.isReadOnly || this.isBinary) return; const index = this.form.options.length; this.form.options.push({ local_id: `${Date.now()}-${index}-${Math.random()}`, option_key: this.optionLabel(index + 1), option_text: "", is_correct: 0, display_order: index + 1 }); },
		removeAnswer(index) { this.form.options.splice(index, 1); this.normaliseAnswers(); },
		moveAnswer(index, direction) { const target = index + direction; if (target < 0 || target >= this.form.options.length) return; const rows = [...this.form.options]; [rows[index], rows[target]] = [rows[target], rows[index]]; this.form.options = rows; this.normaliseAnswers(); },
		normaliseAnswers() { this.form.options = (this.form.options || []).map((row,index) => ({ ...row, option_key: this.optionLabel(index + 1), display_order: index + 1 })); },
		correctAnswerChanged(index, checked) { if (this.isMultipleChoice) this.form.options[index].is_correct = checked ? 1 : 0; else this.form.options.forEach((row,rowIndex) => { row.is_correct = rowIndex === index && checked ? 1 : 0; }); },
		async saveAs(status) { if (!this.canSave && ["Draft", "Under Review"].includes(status)) return; this.saving = true; this.saveError = ""; try { const response = await frappe.call("eduedge.api.question_builder.save_question", { payload: JSON.stringify({ ...this.form, status }) }); await this.applyState(response.message || {}); frappe.show_alert({ message: __(`Question saved as ${status}`), indicator: "green" }); } catch (error) { this.saveError = error?.message || "Question could not be saved."; } finally { this.saving = false; } },
		async createVersion() { this.saving = true; this.saveError = ""; try { const response = await frappe.call("eduedge.api.question_builder.create_question_version", { question: this.form.name }); await this.applyState(response.message || {}); frappe.show_alert({ message: __("New question version created"), indicator: "green" }); } catch (error) { this.saveError = error?.message || "New version could not be created."; } finally { this.saving = false; } },
		openTechnicalRecord() { if (this.form.name) window.open(`/app/eduedge-cbt-question/${encodeURIComponent(this.form.name)}`, "_blank", "noopener,noreferrer"); },
	},
};
</script>

<style scoped>
.question-summary,.panel-heading,.answer-heading { display:flex; align-items:center; justify-content:space-between; gap:1rem; }.question-summary { margin-bottom:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.question-summary>div { display:grid; gap:.2rem; }.question-panel { display:grid; gap:1rem; margin-bottom:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.panel-heading h2 { margin:.15rem 0; }.panel-heading p,.question-panel small,.answer-heading span { color:var(--text-muted); }.question-fields,.marks-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }.question-fields label,.question-panel>label,.lookup-field,.question-editor-field { display:grid; gap:.35rem; font-weight:600; }.lookup-field { position:relative; }.suggestions { position:absolute; z-index:10; top:100%; left:0; right:0; display:grid; max-height:15rem; overflow:auto; border:1px solid var(--border-color); background:var(--card-bg); box-shadow:var(--shadow-md); }.suggestions button { padding:.65rem; border:0; border-bottom:1px solid var(--border-color); background:transparent; text-align:left; }.question-editor { min-height:9rem; padding:.75rem; border:1px solid var(--border-color); border-radius:6px; background:var(--control-bg); }.question-editor.is-read-only { opacity:.8; }.answer-builder,.answer-list { display:grid; gap:.75rem; }.answer-row { display:grid; grid-template-columns:2.5rem minmax(0,1fr) auto auto; gap:.65rem; align-items:center; }.answer-label { display:grid; place-items:center; width:2.2rem; height:2.2rem; border-radius:50%; background:var(--control-bg); font-weight:700; }.correct-choice { display:flex !important; align-items:center; gap:.4rem !important; }.answer-actions { display:flex; gap:.25rem; }.answer-actions button { border:1px solid var(--border-color); border-radius:5px; background:var(--card-bg); }.question-error { color:var(--red-600,#b42318); } @media (max-width:760px) { .question-fields,.marks-grid,.answer-row { grid-template-columns:1fr; }.question-summary,.panel-heading,.answer-heading { align-items:stretch; flex-direction:column; } }
</style>
