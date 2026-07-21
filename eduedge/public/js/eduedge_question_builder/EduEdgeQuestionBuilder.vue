<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="context.current_branch?.branch_name || 'Question Bank'"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-question-builder"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="CBT Question Bank"
					:title="builderTitle"
					:subtitle="builderSubtitle"
					action-label="Back to CBT Operations"
					@action="openRoute('/app/eduedge-cbt-operations')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading Question Builder..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Question Builder could not load"
				:message="error"
				action-label="Try again"
				@retry="loadBuilder"
			/>
			<template v-else>
				<section class="eduedge-question-summary">
					<div>
						<p class="edge-eyebrow">Question governance</p>
						<strong>{{ form.question_code || 'Unsaved question' }}</strong>
						<span v-if="form.name">Version {{ form.version_number || 1 }}</span>
					</div>
					<EdgeStatusBadge :label="form.status || 'Draft'" :status="form.status || 'Draft'" :tone="statusTone" />
				</section>

				<div class="eduedge-question-layout">
					<section class="eduedge-question-panel">
						<div class="eduedge-question-panel__heading">
							<div>
								<p class="edge-eyebrow">Academic classification</p>
								<h2>Question identity</h2>
								<p>Classify the question once so teachers can find and reuse it consistently.</p>
							</div>
						</div>

						<div class="eduedge-question-fields">
							<label class="eduedge-question-field">
								<span>Question Code <b>*</b></span>
								<input
									v-model.trim="form.question_code"
									class="form-control"
									placeholder="e.g. MATH-JSS1-001"
									:disabled="isReadOnly || Boolean(form.name)"
								/>
								<small v-if="form.name">The code is fixed after the first save.</small>
							</label>

							<label class="eduedge-question-field">
								<span>Question Bank <b>*</b></span>
								<select v-model="form.ownership_scope" class="form-control" :disabled="isReadOnly" @change="scopeChanged">
									<option v-for="option in context.scope_options" :key="option.value" :value="option.value">
										{{ option.label }}
									</option>
								</select>
							</label>

							<label v-if="isSchoolQuestion" class="eduedge-question-field">
								<span>School Branch / Campus <b>*</b></span>
								<select v-model="form.school_branch" class="form-control" :disabled="isReadOnly">
									<option value="">Select branch</option>
									<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">
										{{ branch.branch_name || branch.name }}
									</option>
								</select>
							</label>

							<div class="eduedge-question-field eduedge-question-lookup">
								<span>Subject / Course <b>*</b></span>
								<input
									v-model="courseQuery"
									class="form-control"
									placeholder="Search subject or course"
									autocomplete="off"
									:disabled="isReadOnly"
									@focus="searchCourses"
									@input="scheduleCourseSearch"
								/>
								<div v-if="courseSuggestions.length && !isReadOnly" class="eduedge-question-suggestions">
									<button
										v-for="course in courseSuggestions"
										:key="course.value"
										type="button"
										@click="selectCourse(course)"
									>
										{{ course.label }}
									</button>
								</div>
								<small v-if="form.course">Selected: {{ form.course }}</small>
							</div>

							<label class="eduedge-question-field">
								<span>Topic</span>
								<select v-model="form.topic" class="form-control" :disabled="isReadOnly || !form.course">
									<option value="">No topic selected</option>
									<option v-for="topic in topicOptions" :key="topic.value" :value="topic.value">
										{{ topic.label }}
									</option>
								</select>
								<small>Only Topics configured under the selected Course are shown.</small>
							</label>

							<label class="eduedge-question-field">
								<span>Curriculum / Syllabus</span>
								<input v-model.trim="form.curriculum" class="form-control" placeholder="Optional syllabus reference" :disabled="isReadOnly" />
							</label>

							<label class="eduedge-question-field">
								<span>Exam Body / Source Type</span>
								<select v-model="form.exam_body" class="form-control" :disabled="isReadOnly">
									<option v-for="body in context.exam_bodies" :key="body" :value="body">{{ body }}</option>
								</select>
							</label>

							<label class="eduedge-question-field">
								<span>Difficulty <b>*</b></span>
								<select v-model="form.difficulty" class="form-control" :disabled="isReadOnly">
									<option value="">Select difficulty</option>
									<option v-for="difficulty in context.difficulties" :key="difficulty" :value="difficulty">
										{{ difficulty }}
									</option>
								</select>
							</label>
						</div>
					</section>

					<section class="eduedge-question-panel eduedge-question-panel--editor">
						<div class="eduedge-question-panel__heading">
							<div>
								<p class="edge-eyebrow">Question and answer</p>
								<h2>Build the question</h2>
								<p>Enter candidate-facing answers, then mark the correct answer or answers.</p>
							</div>
						</div>

						<label class="eduedge-question-field">
							<span>Question Type <b>*</b></span>
							<select v-model="form.question_type" class="form-control" :disabled="isReadOnly" @change="questionTypeChanged">
								<option v-for="type in context.question_types" :key="type" :value="type">{{ type }}</option>
							</select>
						</label>

						<div class="eduedge-question-field">
							<span>Question <b>*</b></span>
							<div
								class="eduedge-question-editor"
								:class="{ 'is-read-only': isReadOnly }"
								:contenteditable="isReadOnly ? 'false' : 'true'"
								v-html="form.question_text"
								@input="questionTextChanged"
							></div>
							<small>Basic formatting can be pasted or entered directly.</small>
						</div>

						<div v-if="isObjective" class="eduedge-answer-builder">
							<div class="eduedge-answer-builder__heading">
								<div>
									<strong>Answer Choices</strong>
									<span>{{ answerGuidance }}</span>
								</div>
								<button v-if="!isReadOnly && !isBinary" type="button" class="edge-button" @click="addAnswer">
									Add Answer
								</button>
							</div>

							<div v-if="!form.options.length" class="eduedge-answer-empty">
								<p>No answers added yet.</p>
								<button v-if="!isReadOnly" type="button" class="edge-button edge-button--primary" @click="addAnswer">
									Add first answer
								</button>
							</div>

							<div v-else class="eduedge-answer-list">
								<div v-for="(answer, index) in form.options" :key="answer.local_id || index" class="eduedge-answer-row">
									<div class="eduedge-answer-label">{{ optionLabel(index + 1) }}</div>
									<textarea
										v-model="answer.option_text"
										class="form-control"
										rows="2"
										placeholder="Enter answer shown to candidates"
										:disabled="isReadOnly || isBinary"
									></textarea>
									<label class="eduedge-correct-choice">
										<input
											:type="isMultipleChoice ? 'checkbox' : 'radio'"
											name="eduedge-correct-answer"
											:checked="Boolean(Number(answer.is_correct))"
											:disabled="isReadOnly"
											@change="correctAnswerChanged(index, $event.target.checked)"
										/>
										<span>Correct</span>
									</label>
									<div v-if="!isReadOnly && !isBinary" class="eduedge-answer-actions">
										<button type="button" title="Move answer up" :disabled="index === 0" @click="moveAnswer(index, -1)">↑</button>
										<button type="button" title="Move answer down" :disabled="index === form.options.length - 1" @click="moveAnswer(index, 1)">↓</button>
										<button type="button" title="Remove answer" @click="removeAnswer(index)">×</button>
									</div>
								</div>
							</div>
						</div>

						<label v-if="usesAnswerKey" class="eduedge-question-field">
							<span>Answer Key <b>*</b></span>
							<textarea v-model="form.answer_key" class="form-control" rows="3" :disabled="isReadOnly"></textarea>
						</label>

						<label class="eduedge-question-field">
							<span>Marking Guide <b v-if="form.question_type === 'Essay'">*</b></span>
							<textarea v-model="form.marking_guide" class="form-control" rows="3" :disabled="isReadOnly"></textarea>
						</label>

						<div class="eduedge-question-marks">
							<label class="eduedge-question-field">
								<span>Default Mark <b>*</b></span>
								<input v-model.number="form.default_mark" type="number" min="0.01" step="0.25" class="form-control" :disabled="isReadOnly" />
							</label>
							<label class="eduedge-question-field">
								<span>Negative Mark</span>
								<input v-model.number="form.negative_mark" type="number" min="0" step="0.25" class="form-control" :disabled="isReadOnly" />
							</label>
						</div>
					</section>
				</div>

				<details class="eduedge-question-panel eduedge-question-more">
					<summary>More details and audit information</summary>
					<div class="eduedge-question-fields">
						<label class="eduedge-question-field">
							<span>Previous Question Version</span>
							<input :value="form.supersedes_question || 'Not applicable'" class="form-control" disabled />
						</label>
						<label class="eduedge-question-field">
							<span>Version</span>
							<input :value="form.version_number || 1" class="form-control" disabled />
						</label>
						<label class="eduedge-question-field eduedge-question-field--wide">
							<span>Internal Notes</span>
							<textarea v-model="form.notes" class="form-control" rows="3" :disabled="isReadOnly"></textarea>
						</label>
					</div>
					<p v-if="form.reviewed_by" class="eduedge-question-audit">
						Reviewed by {{ form.reviewed_by }}<template v-if="form.reviewed_on"> on {{ form.reviewed_on }}</template>.
					</p>
				</details>

				<div v-if="saveError" class="eduedge-question-error" role="alert">
					<strong>Check the question before saving</strong>
					<div>{{ saveError }}</div>
				</div>

				<EdgeActionBar :label="actionGuidance">
					<template #actions>
						<button type="button" class="edge-button" :disabled="saving" @click="openRoute('/app/eduedge-cbt-operations')">Cancel</button>
						<button
							v-if="context.permissions.can_open_technical_record && form.name"
							type="button"
							class="edge-button"
							:disabled="saving"
							@click="openTechnicalRecord"
						>
							Open Technical Record
						</button>
						<button
							v-if="context.permissions.can_create_version"
							type="button"
							class="edge-button edge-button--primary"
							:disabled="saving"
							@click="createNewVersion"
						>
							Create New Version
						</button>
						<template v-if="!isReadOnly">
							<button type="button" class="edge-button" :disabled="saving" @click="saveAs('Draft')">
								{{ saving ? 'Saving...' : 'Save Draft' }}
							</button>
							<button
								v-if="form.status === 'Draft'"
								type="button"
								class="edge-button edge-button--primary"
								:disabled="saving"
								@click="saveAs('Under Review')"
							>
								Send for Review
							</button>
							<button
								v-if="form.status === 'Under Review' && context.permissions.can_review"
								type="button"
								class="edge-button edge-button--primary"
								:disabled="saving"
								@click="saveAs('Approved')"
							>
								Approve Question
							</button>
						</template>
						<button
							v-if="form.status === 'Approved' && context.permissions.can_review"
							type="button"
							class="edge-button"
							:disabled="saving"
							@click="saveAs('Retired')"
						>
							Retire Question
						</button>
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
		name: null,
		question_code: "",
		ownership_scope: SCHOOL_BANK,
		school_branch: "",
		version_number: 1,
		supersedes_question: "",
		course: "",
		course_label: "",
		topic: "",
		topic_label: "",
		curriculum: "",
		exam_body: "School Internal",
		difficulty: "",
		question_type: "Single Choice",
		question_text: "",
		options: [],
		answer_key: "",
		marking_guide: "",
		default_mark: 1,
		negative_mark: 0,
		status: "Draft",
		notes: "",
	};
}

export default {
	name: "EduEdgeQuestionBuilder",
	props: {
		pageName: { type: String, default: "eduedge-question-builder" },
		questionName: { type: String, default: null },
	},
	data() {
		return {
			loading: true,
			saving: false,
			error: "",
			saveError: "",
			menuItems: EDUEDGE_MENU_ITEMS,
			currentQuestionName: this.questionName || null,
			courseQuery: "",
			courseSuggestions: [],
			topicOptions: [],
			courseTimer: null,
			previousQuestionType: "Single Choice",
			context: {
				user: {},
				current_branch: null,
				allowed_branches: [],
				scope_options: [{ value: SCHOOL_BANK, label: SCHOOL_BANK }],
				question_types: [],
				difficulties: [],
				exam_bodies: [],
				permissions: {},
			},
			form: blankQuestion(),
		};
	},
	computed: {
		builderTitle() {
			return this.form.name ? `Edit ${this.form.question_code || this.form.name}` : "Create CBT Question";
		},
		builderSubtitle() {
			if (this.form.status === "Approved") return "Approved content is protected. Create a new version to revise it.";
			if (this.form.status === "Retired") return "This question is retained for audit history and can start a new version.";
			return "Create clear, reusable questions without exposing technical Frappe fields to teachers.";
		},
		isReadOnly() {
			return !Boolean(this.context.permissions?.can_write);
		},
		isSchoolQuestion() {
			return this.form.ownership_scope === SCHOOL_BANK;
		},
		isObjective() {
			return OBJECTIVE_TYPES.has(this.form.question_type);
		},
		isBinary() {
			return Boolean(BINARY_PRESETS[this.form.question_type]);
		},
		isMultipleChoice() {
			return this.form.question_type === "Multiple Choice";
		},
		usesAnswerKey() {
			return ["Short Answer", "Numeric"].includes(this.form.question_type);
		},
		statusTone() {
			if (this.form.status === "Approved") return "success";
			if (this.form.status === "Under Review") return "warning";
			if (this.form.status === "Retired") return "danger";
			return "neutral";
		},
		answerGuidance() {
			if (this.isBinary) return "Select the one correct answer.";
			if (this.isMultipleChoice) return "Add at least two answers and mark every correct answer.";
			return "Add at least two answers and mark exactly one correct answer.";
		},
		actionGuidance() {
			if (this.form.status === "Approved") return "Approved questions are immutable. Retire them or create a new version.";
			if (this.form.status === "Retired") return "Retired questions remain available for historical exam records.";
			return "Saving uses the governed CBT Question DocType, permissions, branch checks, and server validation.";
		},
	},
	mounted() {
		this.loadBuilder();
	},
	beforeUnmount() {
		if (this.courseTimer) window.clearTimeout(this.courseTimer);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		optionLabel(position) {
			let value = Number(position || 0);
			let label = "";
			while (value > 0) {
				value -= 1;
				label = String.fromCharCode(65 + (value % 26)) + label;
				value = Math.floor(value / 26);
			}
			return label;
		},
		questionTextChanged(event) {
			this.form.question_text = event.target.innerHTML;
			this.saveError = "";
		},
		async loadBuilder() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.question_builder.get_question_builder_context", {
					question: this.currentQuestionName || undefined,
				});
				await this.applyState(response.message || {});
			} catch (error) {
				this.error = error?.message || "Question Builder could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async applyState(state) {
			this.context = { ...this.context, ...state };
			this.form = { ...blankQuestion(), ...(state.question || {}) };
			this.form.options = (this.form.options || []).map((row, index) => ({
				...row,
				local_id: `${Date.now()}-${index}`,
			}));
			this.currentQuestionName = this.form.name || null;
			this.courseQuery = this.form.course_label || this.form.course || "";
			this.previousQuestionType = this.form.question_type || "Single Choice";
			this.courseSuggestions = [];
			await this.loadTopics();
			this.saveError = "";
		},
		scheduleCourseSearch() {
			this.form.course = "";
			this.form.topic = "";
			this.topicOptions = [];
			if (this.courseTimer) window.clearTimeout(this.courseTimer);
			this.courseTimer = window.setTimeout(() => this.searchCourses(), 250);
		},
		async searchCourses() {
			if (this.isReadOnly) return;
			try {
				const response = await frappe.call("eduedge.api.question_builder.search_courses", {
					txt: this.courseQuery || "",
					page_len: 20,
				});
				this.courseSuggestions = response.message || [];
			} catch (error) {
				this.saveError = error?.message || "Courses could not be loaded.";
			}
		},
		async selectCourse(course) {
			this.form.course = course.value;
			this.form.course_label = course.label;
			this.courseQuery = course.label;
			this.courseSuggestions = [];
			this.form.topic = "";
			await this.loadTopics();
		},
		async loadTopics() {
			if (!this.form.course) {
				this.topicOptions = [];
				return;
			}
			try {
				const response = await frappe.call("eduedge.api.question_builder.search_topics", {
					course: this.form.course,
					txt: "",
					page_len: 100,
				});
				this.topicOptions = response.message || [];
				if (this.form.topic && !this.topicOptions.some((topic) => topic.value === this.form.topic)) {
					this.topicOptions.unshift({ value: this.form.topic, label: this.form.topic_label || this.form.topic });
				}
			} catch (error) {
				this.topicOptions = [];
				this.saveError = error?.message || "Topics could not be loaded.";
			}
		},
		scopeChanged() {
			if (!this.isSchoolQuestion) this.form.school_branch = "";
			if (this.isSchoolQuestion && !this.form.school_branch) {
				this.form.school_branch = this.context.current_branch?.name || "";
			}
		},
		questionTypeChanged() {
			const nextType = this.form.question_type;
			const previousType = this.previousQuestionType;
			const existingAnswers = (this.form.options || []).some((row) => String(row.option_text || "").trim());
			const apply = () => {
				this.applyQuestionType(nextType);
				this.previousQuestionType = nextType;
			};
			const revert = () => {
				this.form.question_type = previousType;
			};

			if (existingAnswers && (BINARY_PRESETS[nextType] || !OBJECTIVE_TYPES.has(nextType))) {
				frappe.confirm(
					__("Changing the Question Type will replace or remove the current answers. Continue?"),
					apply,
					revert
				);
				return;
			}
			apply();
		},
		applyQuestionType(type) {
			const preset = BINARY_PRESETS[type];
			if (preset) {
				this.form.options = preset.map((answer, index) => ({
					local_id: `${Date.now()}-${index}`,
					option_key: this.optionLabel(index + 1),
					option_text: answer,
					is_correct: 0,
					display_order: index + 1,
				}));
				return;
			}
			if (CHOICE_TYPES.has(type)) {
				while (this.form.options.length < 2) this.addAnswer();
				if (type === "Single Choice") {
					let found = false;
					this.form.options.forEach((row) => {
						if (Number(row.is_correct) && !found) found = true;
						else if (Number(row.is_correct)) row.is_correct = 0;
					});
				}
				return;
			}
			this.form.options = [];
		},
		addAnswer() {
			if (this.isReadOnly || this.isBinary) return;
			const index = this.form.options.length;
			this.form.options.push({
				local_id: `${Date.now()}-${index}-${Math.random()}`,
				option_key: this.optionLabel(index + 1),
				option_text: "",
				is_correct: 0,
				display_order: index + 1,
			});
		},
		removeAnswer(index) {
			this.form.options.splice(index, 1);
			this.normaliseAnswers();
		},
		moveAnswer(index, direction) {
			const target = index + direction;
			if (target < 0 || target >= this.form.options.length) return;
			const rows = [...this.form.options];
			[rows[index], rows[target]] = [rows[target], rows[index]];
			this.form.options = rows;
			this.normaliseAnswers();
		},
		normaliseAnswers() {
			this.form.options = (this.form.options || []).map((row, index) => ({
				...row,
				option_key: this.optionLabel(index + 1),
				display_order: index + 1,
			}));
		},
		correctAnswerChanged(index, checked) {
			if (this.isMultipleChoice) {
				this.form.options[index].is_correct = checked ? 1 : 0;
				return;
			}
			this.form.options.forEach((row, rowIndex) => {
				row.is_correct = rowIndex === index && checked ? 1 : 0;
			});
		},
		validateForm() {
			const errors = [];
			if (!String(this.form.question_code || "").trim()) errors.push("Enter a Question Code.");
			if (this.isSchoolQuestion && !this.form.school_branch) errors.push("Select a School Branch / Campus.");
			if (!this.form.course) errors.push("Select a Subject / Course from the search results.");
			if (!this.form.difficulty) errors.push("Select the question Difficulty.");
			if (!String(this.form.question_text || "").replace(/<[^>]+>/g, "").trim()) errors.push("Enter the Question.");
			if (Number(this.form.default_mark || 0) <= 0) errors.push("Default Mark must be greater than zero.");
			if (Number(this.form.negative_mark || 0) < 0) errors.push("Negative Mark cannot be negative.");
			if (Number(this.form.negative_mark || 0) > Number(this.form.default_mark || 0)) errors.push("Negative Mark cannot exceed Default Mark.");

			if (this.isObjective) {
				if (this.form.options.length < 2) errors.push("Add at least two Answers.");
				if (this.isBinary && this.form.options.length !== 2) errors.push(`${this.form.question_type} requires exactly two Answers.`);
				this.form.options.forEach((answer, index) => {
					if (!String(answer.option_text || "").trim()) errors.push(`Enter an Answer for option ${this.optionLabel(index + 1)}.`);
				});
				const correctCount = this.form.options.filter((answer) => Number(answer.is_correct)).length;
				if (this.isMultipleChoice && correctCount < 1) errors.push("Mark at least one Correct Answer.");
				if (!this.isMultipleChoice && correctCount !== 1) errors.push("Mark exactly one Correct Answer.");
			}
			if (this.usesAnswerKey && !String(this.form.answer_key || "").trim()) errors.push("Enter the Answer Key.");
			if (this.form.question_type === "Essay" && !String(this.form.marking_guide || "").trim()) errors.push("Enter the Essay Marking Guide.");
			return errors;
		},
		payload(status) {
			this.normaliseAnswers();
			return {
				...this.form,
				status,
				options: this.form.options.map((row) => ({
					option_text: String(row.option_text || "").trim(),
					is_correct: Number(row.is_correct) ? 1 : 0,
				})),
			};
		},
		async saveAs(status) {
			if (this.saving) return;
			const errors = this.validateForm();
			if (errors.length) {
				this.saveError = errors.join(" ");
				return;
			}
			this.saving = true;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.question_builder.save_question", {
					payload: JSON.stringify(this.payload(status)),
				});
				await this.applyState(response.message || {});
				this.updateQuestionUrl();
				frappe.show_alert({ message: __("Question saved successfully."), indicator: "green" }, 5);
			} catch (error) {
				this.saveError = error?.message || "The question could not be saved.";
			} finally {
				this.saving = false;
			}
		},
		updateQuestionUrl() {
			if (!this.form.name) return;
			const url = new URL("/app/eduedge-question-builder", window.location.origin);
			url.searchParams.set("question", this.form.name);
			window.history.replaceState({}, "", `${url.pathname}${url.search}`);
		},
		async createNewVersion() {
			if (!this.form.name || this.saving) return;
			this.saving = true;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.question_builder.create_question_version", {
					question: this.form.name,
				});
				await this.applyState(response.message || {});
				this.updateQuestionUrl();
				frappe.show_alert({ message: __("New Draft version created."), indicator: "green" }, 5);
			} catch (error) {
				this.saveError = error?.message || "A new version could not be created.";
			} finally {
				this.saving = false;
			}
		},
		openTechnicalRecord() {
			if (!this.form.name) return;
			const route = `/app/eduedge-cbt-question/${encodeURIComponent(this.form.name)}`;
			const opened = window.open(route, "_blank", "noopener,noreferrer");
			if (opened) opened.opener = null;
		},
	},
};
</script>

<style scoped>
.eduedge-question-summary,
.eduedge-question-panel__heading,
.eduedge-answer-builder__heading,
.eduedge-answer-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
}

.eduedge-question-summary {
	padding: 0.9rem 1rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface, #fff);
}

.eduedge-question-summary > div {
	display: grid;
	gap: 0.2rem;
}

.eduedge-question-summary span,
.eduedge-question-panel__heading p,
.eduedge-answer-builder__heading span,
.eduedge-question-field small,
.eduedge-question-audit {
	color: var(--edge-text-muted, #64748b);
}

.eduedge-question-layout {
	display: grid;
	grid-template-columns: minmax(18rem, 0.85fr) minmax(24rem, 1.35fr);
	gap: 1rem;
	margin-top: 1rem;
}

.eduedge-question-panel {
	min-width: 0;
	padding: 1.25rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface, #fff);
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.06));
}

.eduedge-question-panel__heading {
	align-items: flex-start;
	margin-bottom: 1rem;
}

.eduedge-question-panel__heading h2 {
	margin: 0.2rem 0 0.35rem;
	font-size: 1.08rem;
}

.eduedge-question-panel__heading p {
	margin: 0;
}

.eduedge-question-fields {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 1rem;
}

.eduedge-question-field {
	display: grid;
	gap: 0.35rem;
	margin-bottom: 1rem;
	font-size: 0.84rem;
	font-weight: 600;
	color: var(--edge-text-muted, #64748b);
}

.eduedge-question-field b {
	color: var(--red-500, #dc2626);
}

.eduedge-question-field--wide {
	grid-column: 1 / -1;
}

.eduedge-question-lookup {
	position: relative;
}

.eduedge-question-suggestions {
	position: absolute;
	top: calc(100% - 1rem);
	left: 0;
	right: 0;
	z-index: 20;
	display: grid;
	max-height: 14rem;
	overflow: auto;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: 0.6rem;
	background: var(--edge-surface, #fff);
	box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
}

.eduedge-question-suggestions button {
	padding: 0.75rem;
	border: 0;
	border-bottom: 1px solid var(--edge-border, #e2e8f0);
	background: transparent;
	text-align: left;
}

.eduedge-question-suggestions button:hover {
	background: var(--edge-primary-soft, #eff6ff);
}

.eduedge-question-editor {
	min-height: 9rem;
	padding: 0.85rem;
	border: 1px solid var(--edge-border, #d1d5db);
	border-radius: 0.5rem;
	background: var(--edge-surface, #fff);
	color: var(--edge-text, #111827);
	font-weight: 400;
}

.eduedge-question-editor:focus {
	outline: 2px solid var(--edge-primary-soft, #dbeafe);
	border-color: var(--edge-primary, #2563eb);
}

.eduedge-question-editor.is-read-only {
	background: var(--edge-surface-subtle, #f8fafc);
}

.eduedge-answer-builder {
	margin: 1rem 0;
	padding: 1rem;
	border-radius: var(--edge-radius-md, 0.7rem);
	background: var(--edge-surface-subtle, #f8fafc);
}

.eduedge-answer-builder__heading {
	align-items: flex-start;
	margin-bottom: 0.85rem;
}

.eduedge-answer-builder__heading > div {
	display: grid;
	gap: 0.2rem;
}

.eduedge-answer-list {
	display: grid;
	gap: 0.7rem;
}

.eduedge-answer-row {
	justify-content: flex-start;
	padding: 0.75rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: 0.65rem;
	background: var(--edge-surface, #fff);
}

.eduedge-answer-label {
	display: grid;
	place-items: center;
	width: 2.25rem;
	height: 2.25rem;
	flex: 0 0 2.25rem;
	border-radius: 999px;
	background: var(--edge-primary-soft, #eff6ff);
	color: var(--edge-primary, #1d4ed8);
	font-weight: 700;
}

.eduedge-answer-row textarea {
	flex: 1 1 auto;
	min-width: 0;
}

.eduedge-correct-choice {
	display: flex;
	align-items: center;
	gap: 0.4rem;
	white-space: nowrap;
	font-size: 0.83rem;
	font-weight: 600;
}

.eduedge-answer-actions {
	display: flex;
	gap: 0.25rem;
}

.eduedge-answer-actions button {
	width: 2rem;
	height: 2rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: 0.45rem;
	background: var(--edge-surface, #fff);
}

.eduedge-answer-empty {
	display: grid;
	place-items: center;
	gap: 0.75rem;
	padding: 1.5rem;
	border: 1px dashed var(--edge-border, #cbd5e1);
	border-radius: 0.65rem;
	text-align: center;
}

.eduedge-question-marks {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 1rem;
}

.eduedge-question-more {
	margin-top: 1rem;
}

.eduedge-question-more summary {
	cursor: pointer;
	font-weight: 700;
}

.eduedge-question-more[open] summary {
	margin-bottom: 1rem;
}

.eduedge-question-error {
	margin-top: 1rem;
	padding: 0.9rem 1rem;
	border: 1px solid #fecaca;
	border-radius: 0.65rem;
	background: #fef2f2;
	color: #991b1b;
}

@media (max-width: 980px) {
	.eduedge-question-layout {
		grid-template-columns: 1fr;
	}
}

@media (max-width: 640px) {
	.eduedge-question-summary,
	.eduedge-question-panel__heading,
	.eduedge-answer-builder__heading,
	.eduedge-answer-row {
		align-items: stretch;
		flex-direction: column;
	}

	.eduedge-question-fields,
	.eduedge-question-marks {
		grid-template-columns: 1fr;
	}

	.eduedge-answer-label {
		width: 2rem;
		height: 2rem;
	}
}
</style>
