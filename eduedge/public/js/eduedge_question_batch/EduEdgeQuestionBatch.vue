<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="context.current_branch?.branch_name || 'Question Bank'"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-question-batch"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="CBT Question Bank"
					title="Multiple Questions"
					subtitle="Enter several questions with shared academic details or validate a prepared CSV/XLSX file before importing Draft questions."
					action-label="Single Question Builder"
					@action="openRoute('/app/eduedge-question-builder')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading multiple question entry..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Multiple question entry could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<nav class="eduedge-batch-tabs" aria-label="Question entry method">
					<button
						type="button"
						:class="{ active: mode === 'entry' }"
						@click="setMode('entry')"
					>
						Multiple Entry
					</button>
					<button
						type="button"
						:class="{ active: mode === 'upload' }"
						@click="setMode('upload')"
					>
						Upload Questions
					</button>
				</nav>

				<section class="eduedge-batch-panel">
					<div class="eduedge-batch-panel__heading">
						<div>
							<p class="edge-eyebrow">Shared academic details</p>
							<h2>Apply once to every question</h2>
							<p>Branch, Subject/Course, Topic and source details are validated again for every created question.</p>
						</div>
						<EdgeStatusBadge label="Draft only" status="Draft" tone="neutral" />
					</div>

					<div class="eduedge-common-fields">
						<label class="eduedge-batch-field">
							<span>Question Bank <b>*</b></span>
							<select v-model="common.ownership_scope" class="form-control" :disabled="busy" @change="scopeChanged">
								<option v-for="option in context.scope_options" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</select>
						</label>

						<label v-if="isSchoolQuestion" class="eduedge-batch-field">
							<span>School Branch / Campus <b>*</b></span>
							<select v-model="common.school_branch" class="form-control" :disabled="busy">
								<option value="">Select branch</option>
								<option v-for="branch in context.allowed_branches" :key="branch.name" :value="branch.name">
									{{ branch.branch_name || branch.name }}
								</option>
							</select>
						</label>

						<div class="eduedge-batch-field eduedge-batch-lookup">
							<span>Subject / Course <b>*</b></span>
							<input
								v-model="courseQuery"
								class="form-control"
								placeholder="Search subject or course"
								autocomplete="off"
								:disabled="busy"
								@focus="searchCourses"
								@input="scheduleCourseSearch"
							/>
							<div v-if="courseSuggestions.length && !busy" class="eduedge-batch-suggestions">
								<button
									v-for="course in courseSuggestions"
									:key="course.value"
									type="button"
									@click="selectCourse(course)"
								>
									{{ course.label }}
								</button>
							</div>
							<small v-if="common.course">Selected: {{ common.course }}</small>
						</div>

						<label class="eduedge-batch-field">
							<span>Topic</span>
							<select v-model="common.topic" class="form-control" :disabled="busy || !common.course">
								<option value="">No topic selected</option>
								<option v-for="topic in topicOptions" :key="topic.value" :value="topic.value">
									{{ topic.label }}
								</option>
							</select>
							<small>Only Topics configured under the selected Course are shown.</small>
						</label>

						<label class="eduedge-batch-field">
							<span>Curriculum / Syllabus</span>
							<input v-model.trim="common.curriculum" class="form-control" placeholder="Optional syllabus reference" :disabled="busy" />
						</label>

						<label class="eduedge-batch-field">
							<span>Exam Body / Source Type</span>
							<select v-model="common.exam_body" class="form-control" :disabled="busy">
								<option v-for="body in context.exam_bodies" :key="body" :value="body">{{ body }}</option>
							</select>
						</label>

						<label class="eduedge-batch-field">
							<span>Default Difficulty</span>
							<select v-model="common.difficulty" class="form-control" :disabled="busy">
								<option v-for="difficulty in context.difficulties" :key="difficulty" :value="difficulty">
									{{ difficulty }}
								</option>
							</select>
						</label>

						<label class="eduedge-batch-field">
							<span>Default Mark</span>
							<input v-model.number="common.default_mark" type="number" min="0.01" step="0.25" class="form-control" :disabled="busy" />
						</label>

						<label class="eduedge-batch-field">
							<span>Default Negative Mark</span>
							<input v-model.number="common.negative_mark" type="number" min="0" step="0.25" class="form-control" :disabled="busy" />
						</label>
					</div>
				</section>

				<section v-if="mode === 'entry'" class="eduedge-batch-workspace">
					<div class="eduedge-batch-workspace__heading">
						<div>
							<p class="edge-eyebrow">Multiple entry</p>
							<h2>Question cards</h2>
							<p>Each card becomes a separate governed Draft question.</p>
						</div>
						<div class="eduedge-batch-heading-actions">
							<EdgeStatusBadge :label="`${questions.length} Question${questions.length === 1 ? '' : 's'}`" status="Draft" tone="neutral" />
							<button type="button" class="edge-button" :disabled="busy || questions.length >= context.limits.manual_questions" @click="addQuestion">
								Add Question
							</button>
						</div>
					</div>

					<div class="eduedge-question-cards">
						<article v-for="(question, questionIndex) in questions" :key="question.local_id" class="eduedge-question-card">
							<div class="eduedge-question-card__heading">
								<div>
									<span class="eduedge-question-number">{{ questionIndex + 1 }}</span>
									<strong>{{ question.question_code || `Question ${questionIndex + 1}` }}</strong>
								</div>
								<button v-if="questions.length > 1" type="button" class="eduedge-remove-question" :disabled="busy" @click="removeQuestion(questionIndex)">
									Remove
								</button>
							</div>

							<div class="eduedge-question-card__grid">
								<label class="eduedge-batch-field">
									<span>Question Code <b>*</b></span>
									<input v-model.trim="question.question_code" class="form-control" placeholder="e.g. MATH-JSS1-001" :disabled="busy" />
								</label>
								<label class="eduedge-batch-field">
									<span>Question Type <b>*</b></span>
									<select v-model="question.question_type" class="form-control" :disabled="busy" @change="questionTypeChanged(question)">
										<option v-for="type in context.question_types" :key="type" :value="type">{{ type }}</option>
									</select>
								</label>
								<label class="eduedge-batch-field">
									<span>Difficulty</span>
									<select v-model="question.difficulty" class="form-control" :disabled="busy">
										<option value="">Use {{ common.difficulty }}</option>
										<option v-for="difficulty in context.difficulties" :key="difficulty" :value="difficulty">{{ difficulty }}</option>
									</select>
								</label>
							</div>

							<label class="eduedge-batch-field eduedge-batch-field--wide">
								<span>Question <b>*</b></span>
								<textarea v-model="question.question_text" class="form-control" rows="3" placeholder="Enter the question shown to candidates" :disabled="busy"></textarea>
							</label>

							<div v-if="isObjective(question)" class="eduedge-card-answers">
								<div class="eduedge-card-answers__heading">
									<div>
										<strong>Answer Choices</strong>
										<span>{{ answerGuidance(question) }}</span>
									</div>
									<button v-if="!isBinary(question)" type="button" class="edge-button" :disabled="busy" @click="addAnswer(question)">Add Answer</button>
								</div>

								<div v-if="!question.options.length" class="eduedge-card-empty">
									<span>No answer choices added.</span>
									<button type="button" class="edge-button" :disabled="busy" @click="addAnswer(question)">Add first answer</button>
								</div>

								<div v-else class="eduedge-card-answer-list">
									<div v-for="(answer, answerIndex) in question.options" :key="answer.local_id" class="eduedge-card-answer-row">
										<span class="eduedge-answer-option">{{ optionLabel(answerIndex + 1) }}</span>
										<textarea
											v-model="answer.option_text"
											class="form-control"
											rows="2"
											placeholder="Enter answer shown to candidates"
											:disabled="busy || isBinary(question)"
										></textarea>
										<label class="eduedge-answer-correct">
											<input
												:type="question.question_type === 'Multiple Choice' ? 'checkbox' : 'radio'"
												:name="`correct-${question.local_id}`"
												:checked="Boolean(Number(answer.is_correct))"
												:disabled="busy"
												@change="correctAnswerChanged(question, answerIndex, $event.target.checked)"
											/>
											<span>Correct</span>
										</label>
										<div v-if="!isBinary(question)" class="eduedge-answer-controls">
											<button type="button" title="Move up" :disabled="busy || answerIndex === 0" @click="moveAnswer(question, answerIndex, -1)">↑</button>
											<button type="button" title="Move down" :disabled="busy || answerIndex === question.options.length - 1" @click="moveAnswer(question, answerIndex, 1)">↓</button>
											<button type="button" title="Remove" :disabled="busy" @click="removeAnswer(question, answerIndex)">×</button>
										</div>
									</div>
								</div>
							</div>

							<label v-if="usesAnswerKey(question)" class="eduedge-batch-field eduedge-batch-field--wide">
								<span>Answer Key <b>*</b></span>
								<textarea v-model="question.answer_key" class="form-control" rows="2" :disabled="busy"></textarea>
							</label>

							<label v-if="question.question_type === 'Essay'" class="eduedge-batch-field eduedge-batch-field--wide">
								<span>Marking Guide <b>*</b></span>
								<textarea v-model="question.marking_guide" class="form-control" rows="3" :disabled="busy"></textarea>
							</label>

							<div class="eduedge-question-card__grid eduedge-question-card__grid--marks">
								<label class="eduedge-batch-field">
									<span>Mark</span>
									<input v-model.number="question.default_mark" type="number" min="0.01" step="0.25" class="form-control" placeholder="Use shared default" :disabled="busy" />
								</label>
								<label class="eduedge-batch-field">
									<span>Negative Mark</span>
									<input v-model.number="question.negative_mark" type="number" min="0" step="0.25" class="form-control" placeholder="Use shared default" :disabled="busy" />
								</label>
							</div>
						</article>
					</div>

					<div v-if="operationError" class="eduedge-batch-error" role="alert">
						<strong>Questions could not be saved</strong>
						<span>{{ operationError }}</span>
					</div>
					<div v-if="successMessage" class="eduedge-batch-success" role="status">
						<strong>{{ successMessage }}</strong>
						<span>All records were created as Draft questions and remain subject to review.</span>
					</div>

					<EdgeActionBar :label="`Maximum ${context.limits.manual_questions} questions per save. The operation is all-or-nothing.`">
						<template #actions>
							<button type="button" class="edge-button" :disabled="busy" @click="resetEntry">Reset</button>
							<button type="button" class="edge-button edge-button--primary" :disabled="busy" @click="saveBatch">
								{{ saving ? 'Saving Questions...' : `Save ${questions.length} Draft Question${questions.length === 1 ? '' : 's'}` }}
							</button>
						</template>
					</EdgeActionBar>
				</section>

				<section v-else class="eduedge-batch-workspace">
					<div class="eduedge-batch-workspace__heading">
						<div>
							<p class="edge-eyebrow">CSV or XLSX upload</p>
							<h2>Validate before import</h2>
							<p>The file is read in memory, previewed row by row and revalidated on import.</p>
						</div>
						<button type="button" class="edge-button" :disabled="busy" @click="downloadTemplate">Download CSV Template</button>
					</div>

					<div class="eduedge-upload-guide">
						<strong>Required columns</strong>
						<p><code>question_code</code>, <code>question_type</code>, <code>question</code>, and objective answer columns such as <code>answer_a</code>, <code>answer_b</code>.</p>
						<p>Use <code>correct_answers</code> as <code>B</code> for one answer or <code>B|D</code> for multiple answers. Yes/No and True/False answers are generated automatically.</p>
					</div>

					<label class="eduedge-upload-drop" :class="{ 'has-file': upload.fileName }">
						<input type="file" accept=".csv,.xlsx" :disabled="busy" @change="fileChanged" />
						<strong>{{ upload.fileName || 'Choose CSV or XLSX question file' }}</strong>
						<span v-if="upload.fileName">{{ formatBytes(upload.fileSize) }}</span>
						<span v-else>Maximum 5 MB and {{ context.limits.upload_rows }} question rows.</span>
					</label>

					<div class="eduedge-upload-actions">
						<button type="button" class="edge-button" :disabled="busy || !upload.fileContent" @click="clearUpload">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="busy || !upload.fileContent" @click="previewUpload">
							{{ previewing ? 'Validating...' : 'Validate File' }}
						</button>
					</div>

					<div v-if="operationError" class="eduedge-batch-error" role="alert">
						<strong>Upload could not be processed</strong>
						<span>{{ operationError }}</span>
					</div>

					<template v-if="upload.preview">
						<div class="eduedge-preview-summary">
							<div><span>Total rows</span><strong>{{ upload.preview.total_rows }}</strong></div>
							<div><span>Valid rows</span><strong>{{ upload.preview.valid_rows }}</strong></div>
							<div><span>Rows with errors</span><strong>{{ upload.preview.error_rows }}</strong></div>
						</div>

						<div class="eduedge-preview-table-wrap">
							<table class="eduedge-preview-table">
								<thead>
									<tr>
										<th>Row</th>
										<th>Question Code</th>
										<th>Type</th>
										<th>Question</th>
										<th>Validation</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="row in upload.preview.rows" :key="row.row_number" :class="{ invalid: !row.valid }">
										<td>{{ row.row_number }}</td>
										<td>{{ row.question_code || 'Missing' }}</td>
										<td>{{ row.question_type || 'Missing' }}</td>
										<td>{{ row.question_text || 'Missing' }}</td>
										<td>
											<span v-if="row.valid" class="eduedge-valid-row">Ready</span>
											<span v-else class="eduedge-invalid-row">{{ row.error }}</span>
										</td>
									</tr>
								</tbody>
							</table>
						</div>

						<div v-if="successMessage" class="eduedge-batch-success" role="status">
							<strong>{{ successMessage }}</strong>
							<span>The imported records are Draft questions and must still pass the normal review workflow.</span>
						</div>

						<EdgeActionBar :label="upload.preview.can_import ? 'All rows passed validation and may be imported.' : 'Resolve every validation error before importing.'">
							<template #actions>
								<button type="button" class="edge-button" :disabled="busy" @click="previewUpload">Validate Again</button>
								<button type="button" class="edge-button edge-button--primary" :disabled="busy || !upload.preview.can_import" @click="importUpload">
									{{ importing ? 'Importing...' : `Import ${upload.preview.valid_rows} Draft Question${upload.preview.valid_rows === 1 ? '' : 's'}` }}
								</button>
							</template>
						</EdgeActionBar>
					</template>
				</section>
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
const TEMPLATE_HEADERS = [
	"question_code",
	"question_type",
	"question",
	"difficulty",
	"answer_a",
	"answer_b",
	"answer_c",
	"answer_d",
	"answer_e",
	"answer_f",
	"answer_g",
	"answer_h",
	"correct_answers",
	"answer_key",
	"marking_guide",
	"default_mark",
	"negative_mark",
	"notes",
];

function blankQuestion() {
	return {
		local_id: `${Date.now()}-${Math.random()}`,
		question_code: "",
		question_type: "Single Choice",
		_previous_type: "Single Choice",
		difficulty: "",
		question_text: "",
		options: [],
		answer_key: "",
		marking_guide: "",
		default_mark: "",
		negative_mark: "",
		notes: "",
	};
}

export default {
	name: "EduEdgeQuestionBatch",
	props: {
		pageName: { type: String, default: "eduedge-question-batch" },
		initialMode: { type: String, default: "entry" },
	},
	data() {
		return {
			loading: true,
			saving: false,
			previewing: false,
			importing: false,
			error: "",
			operationError: "",
			successMessage: "",
			mode: this.initialMode === "upload" ? "upload" : "entry",
			menuItems: EDUEDGE_MENU_ITEMS,
			context: {
				user: {},
				current_branch: null,
				allowed_branches: [],
				scope_options: [],
				question_types: [],
				difficulties: [],
				exam_bodies: [],
				limits: { manual_questions: 50, upload_rows: 500, upload_bytes: 5242880 },
			},
			common: {
				ownership_scope: SCHOOL_BANK,
				school_branch: "",
				course: "",
				course_label: "",
				topic: "",
				topic_label: "",
				curriculum: "",
				exam_body: "School Internal",
				difficulty: "Moderate",
				default_mark: 1,
				negative_mark: 0,
			},
			questions: [blankQuestion()],
			courseQuery: "",
			courseSuggestions: [],
			topicOptions: [],
			courseTimer: null,
			upload: {
				fileName: "",
				fileSize: 0,
				fileContent: "",
				preview: null,
			},
		};
	},
	computed: {
		busy() {
			return this.saving || this.previewing || this.importing;
		},
		isSchoolQuestion() {
			return this.common.ownership_scope === SCHOOL_BANK;
		},
	},
	mounted() {
		this.loadContext();
	},
	beforeUnmount() {
		if (this.courseTimer) window.clearTimeout(this.courseTimer);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.question_batch.get_question_batch_context");
				const state = response.message || {};
				this.context = { ...this.context, ...state };
				this.common = { ...this.common, ...(state.defaults || {}) };
				this.courseQuery = this.common.course_label || this.common.course || "";
				await this.loadTopics();
			} catch (error) {
				this.error = error?.message || "Multiple question entry could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		setMode(mode) {
			this.mode = mode;
			this.operationError = "";
			this.successMessage = "";
			const url = new URL(window.location.href);
			url.searchParams.set("mode", mode);
			window.history.replaceState({}, "", url.toString());
		},
		scopeChanged() {
			if (!this.isSchoolQuestion) this.common.school_branch = "";
			if (this.isSchoolQuestion && !this.common.school_branch) {
				this.common.school_branch = this.context.current_branch?.name || "";
			}
			this.invalidatePreview();
		},
		scheduleCourseSearch() {
			this.common.course = "";
			this.common.topic = "";
			this.topicOptions = [];
			this.invalidatePreview();
			if (this.courseTimer) window.clearTimeout(this.courseTimer);
			this.courseTimer = window.setTimeout(() => this.searchCourses(), 250);
		},
		async searchCourses() {
			try {
				const response = await frappe.call("eduedge.api.question_builder.search_courses", {
					txt: this.courseQuery || "",
					page_len: 20,
				});
				this.courseSuggestions = response.message || [];
			} catch (error) {
				this.operationError = error?.message || "Courses could not be loaded.";
			}
		},
		async selectCourse(course) {
			this.common.course = course.value;
			this.common.course_label = course.label;
			this.courseQuery = course.label;
			this.courseSuggestions = [];
			this.common.topic = "";
			this.invalidatePreview();
			await this.loadTopics();
		},
		async loadTopics() {
			if (!this.common.course) {
				this.topicOptions = [];
				return;
			}
			try {
				const response = await frappe.call("eduedge.api.question_builder.search_topics", {
					course: this.common.course,
					txt: "",
					page_len: 100,
				});
				this.topicOptions = response.message || [];
			} catch (error) {
				this.topicOptions = [];
				this.operationError = error?.message || "Topics could not be loaded.";
			}
		},
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
		addQuestion() {
			if (this.questions.length >= this.context.limits.manual_questions) return;
			this.questions.push(blankQuestion());
		},
		removeQuestion(index) {
			this.questions.splice(index, 1);
			if (!this.questions.length) this.questions.push(blankQuestion());
		},
		resetEntry() {
			this.questions = [blankQuestion()];
			this.operationError = "";
			this.successMessage = "";
		},
		isObjective(question) {
			return OBJECTIVE_TYPES.has(question.question_type);
		},
		isBinary(question) {
			return Boolean(BINARY_PRESETS[question.question_type]);
		},
		usesAnswerKey(question) {
			return ["Short Answer", "Numeric"].includes(question.question_type);
		},
		answerGuidance(question) {
			if (this.isBinary(question)) return "Select the one correct answer.";
			if (question.question_type === "Multiple Choice") return "Add at least two answers and mark every correct answer.";
			return "Add at least two answers and mark exactly one correct answer.";
		},
		questionTypeChanged(question) {
			const nextType = question.question_type;
			const previousType = question._previous_type || "Single Choice";
			const hasAnswers = question.options.some((answer) => String(answer.option_text || "").trim());
			const apply = () => {
				this.applyQuestionType(question, nextType);
				question._previous_type = nextType;
			};
			const revert = () => {
				question.question_type = previousType;
			};
			if (hasAnswers && (BINARY_PRESETS[nextType] || !OBJECTIVE_TYPES.has(nextType))) {
				frappe.confirm(
					__("Changing the Question Type will replace or remove the current answers. Continue?"),
					apply,
					revert
				);
				return;
			}
			apply();
		},
		applyQuestionType(question, type) {
			const preset = BINARY_PRESETS[type];
			if (preset) {
				question.options = preset.map((answer, index) => ({
					local_id: `${Date.now()}-${Math.random()}-${index}`,
					option_text: answer,
					is_correct: 0,
				}));
				return;
			}
			if (CHOICE_TYPES.has(type)) {
				while (question.options.length < 2) this.addAnswer(question);
				if (type === "Single Choice") {
					let correctFound = false;
					question.options.forEach((answer) => {
						if (Number(answer.is_correct) && !correctFound) correctFound = true;
						else if (Number(answer.is_correct)) answer.is_correct = 0;
					});
				}
				return;
			}
			question.options = [];
		},
		addAnswer(question) {
			if (this.isBinary(question)) return;
			question.options.push({
				local_id: `${Date.now()}-${Math.random()}`,
				option_text: "",
				is_correct: 0,
			});
		},
		removeAnswer(question, index) {
			question.options.splice(index, 1);
		},
		moveAnswer(question, index, direction) {
			const target = index + direction;
			if (target < 0 || target >= question.options.length) return;
			const rows = [...question.options];
			[rows[index], rows[target]] = [rows[target], rows[index]];
			question.options = rows;
		},
		correctAnswerChanged(question, index, checked) {
			if (question.question_type === "Multiple Choice") {
				question.options[index].is_correct = checked ? 1 : 0;
				return;
			}
			question.options.forEach((answer, answerIndex) => {
				answer.is_correct = answerIndex === index && checked ? 1 : 0;
			});
		},
		validateCommon() {
			if (!this.common.ownership_scope) return "Select a Question Bank.";
			if (this.isSchoolQuestion && !this.common.school_branch) return "Select a School Branch / Campus.";
			if (!this.common.course) return "Select a Subject / Course from the search results.";
			if (Number(this.common.default_mark) <= 0) return "Default Mark must be greater than zero.";
			if (Number(this.common.negative_mark) < 0) return "Default Negative Mark cannot be negative.";
			if (Number(this.common.negative_mark) > Number(this.common.default_mark)) return "Default Negative Mark cannot exceed Default Mark.";
			return "";
		},
		validateQuestion(question, index) {
			const label = `Question ${index + 1}`;
			if (!String(question.question_code || "").trim()) return `${label}: enter a Question Code.`;
			if (!String(question.question_text || "").trim()) return `${label}: enter the Question.`;
			if (!this.context.question_types.includes(question.question_type)) return `${label}: select a valid Question Type.`;
			if (this.isObjective(question)) {
				if (question.options.length < 2) return `${label}: add at least two Answers.`;
				if (question.options.some((answer) => !String(answer.option_text || "").trim())) return `${label}: every Answer must have text.`;
				const correctCount = question.options.filter((answer) => Number(answer.is_correct)).length;
				if (question.question_type === "Multiple Choice" && correctCount < 1) return `${label}: mark at least one Correct Answer.`;
				if (question.question_type !== "Multiple Choice" && correctCount !== 1) return `${label}: mark exactly one Correct Answer.`;
			}
			if (this.usesAnswerKey(question) && !String(question.answer_key || "").trim()) return `${label}: enter the Answer Key.`;
			if (question.question_type === "Essay" && !String(question.marking_guide || "").trim()) return `${label}: enter the Marking Guide.`;
			const mark = question.default_mark === "" ? Number(this.common.default_mark) : Number(question.default_mark);
			const negative = question.negative_mark === "" ? Number(this.common.negative_mark) : Number(question.negative_mark);
			if (!(mark > 0)) return `${label}: Mark must be greater than zero.`;
			if (negative < 0 || negative > mark) return `${label}: Negative Mark must be between zero and the Mark.`;
			return "";
		},
		validateBatch() {
			const commonError = this.validateCommon();
			if (commonError) return commonError;
			const codes = new Set();
			for (const [index, question] of this.questions.entries()) {
				const error = this.validateQuestion(question, index);
				if (error) return error;
				const code = String(question.question_code || "").trim().toUpperCase();
				if (codes.has(code)) return `Question ${index + 1}: Question Code ${code} is repeated in this batch.`;
				codes.add(code);
			}
			return "";
		},
		async saveBatch() {
			if (this.saving) return;
			this.operationError = this.validateBatch();
			this.successMessage = "";
			if (this.operationError) return;
			this.saving = true;
			try {
				const response = await frappe.call("eduedge.api.question_batch.save_question_batch", {
					common: JSON.stringify(this.common),
					questions: JSON.stringify(this.questions),
					source: "manual",
				});
				const result = response.message || {};
				this.successMessage = `${result.count || 0} Draft question${result.count === 1 ? '' : 's'} created successfully.`;
				this.questions = [blankQuestion()];
			} catch (error) {
				this.operationError = error?.message || "The questions could not be saved.";
			} finally {
				this.saving = false;
			}
		},
		invalidatePreview() {
			this.upload.preview = null;
			this.successMessage = "";
		},
		fileChanged(event) {
			const file = event.target.files?.[0];
			this.clearUpload(false);
			if (!file) return;
			const extension = file.name.toLowerCase().split(".").pop();
			if (!["csv", "xlsx"].includes(extension)) {
				this.operationError = "Only CSV and XLSX files are supported.";
				event.target.value = "";
				return;
			}
			if (file.size > this.context.limits.upload_bytes) {
				this.operationError = "The upload file cannot exceed 5 MB.";
				event.target.value = "";
				return;
			}
			const reader = new FileReader();
			reader.onload = () => {
				this.upload.fileName = file.name;
				this.upload.fileSize = file.size;
				this.upload.fileContent = String(reader.result || "");
				this.operationError = "";
			};
			reader.onerror = () => {
				this.operationError = "The selected file could not be read.";
			};
			reader.readAsDataURL(file);
		},
		clearUpload(clearInput = true) {
			this.upload = { fileName: "", fileSize: 0, fileContent: "", preview: null };
			this.operationError = "";
			this.successMessage = "";
			if (clearInput) {
				const input = this.$el?.querySelector('.eduedge-upload-drop input[type="file"]');
				if (input) input.value = "";
			}
		},
		formatBytes(bytes) {
			if (!bytes) return "0 KB";
			if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
			return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
		},
		async previewUpload() {
			if (this.previewing || !this.upload.fileContent) return;
			this.operationError = this.validateCommon();
			this.successMessage = "";
			if (this.operationError) return;
			this.previewing = true;
			try {
				const response = await frappe.call("eduedge.api.question_batch.preview_question_upload", {
					file_name: this.upload.fileName,
					file_content: this.upload.fileContent,
					common: JSON.stringify(this.common),
				});
				this.upload.preview = response.message || null;
			} catch (error) {
				this.upload.preview = null;
				this.operationError = error?.message || "The upload file could not be validated.";
			} finally {
				this.previewing = false;
			}
		},
		async importUpload() {
			if (this.importing || !this.upload.preview?.can_import) return;
			this.operationError = this.validateCommon();
			this.successMessage = "";
			if (this.operationError) return;
			this.importing = true;
			try {
				const response = await frappe.call("eduedge.api.question_upload.import_question_upload", {
					file_name: this.upload.fileName,
					file_content: this.upload.fileContent,
					common: JSON.stringify(this.common),
				});
				const result = response.message || {};
				this.successMessage = `${result.count || 0} Draft question${result.count === 1 ? '' : 's'} imported successfully.`;
				this.upload.preview = null;
			} catch (error) {
				this.operationError = error?.message || "The questions could not be imported.";
			} finally {
				this.importing = false;
			}
		},
		csvCell(value) {
			const text = String(value ?? "");
			return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
		},
		downloadTemplate() {
			const rows = [
				TEMPLATE_HEADERS,
				["MATH-JSS1-001", "Single Choice", "What is 2 + 2?", "Easy", "3", "4", "5", "6", "", "", "", "", "B", "", "", "1", "0", ""],
				["MATH-JSS1-002", "Yes/No", "Is 5 greater than 3?", "Easy", "", "", "", "", "", "", "", "", "Yes", "", "", "1", "0", ""],
				["MATH-JSS1-003", "Multiple Choice", "Select the even numbers.", "Moderate", "1", "2", "3", "4", "", "", "", "", "B|D", "", "", "2", "0", ""],
			];
			const csv = rows.map((row) => row.map((cell) => this.csvCell(cell)).join(",")).join("\r\n");
			const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = "eduedge-question-upload-template.csv";
			document.body.appendChild(link);
			link.click();
			link.remove();
			URL.revokeObjectURL(url);
		},
	},
};
</script>

<style scoped>
.eduedge-batch-tabs {
	display: inline-flex;
	gap: 0.35rem;
	padding: 0.35rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface-subtle, #f8fafc);
}

.eduedge-batch-tabs button {
	padding: 0.65rem 1rem;
	border: 0;
	border-radius: var(--edge-radius-md, 0.7rem);
	background: transparent;
	font-weight: 600;
}

.eduedge-batch-tabs button.active {
	background: var(--edge-surface, #fff);
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.08));
	color: var(--edge-primary, #1f6feb);
}

.eduedge-batch-panel,
.eduedge-batch-workspace,
.eduedge-question-card {
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface, #fff);
	box-shadow: var(--edge-shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.06));
}

.eduedge-batch-panel,
.eduedge-batch-workspace {
	margin-top: 1rem;
	padding: 1.25rem;
}

.eduedge-batch-panel__heading,
.eduedge-batch-workspace__heading,
.eduedge-question-card__heading,
.eduedge-card-answers__heading,
.eduedge-batch-heading-actions,
.eduedge-upload-actions {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.eduedge-batch-panel__heading h2,
.eduedge-batch-workspace__heading h2 {
	margin: 0.2rem 0 0.3rem;
	font-size: 1.15rem;
}

.eduedge-batch-panel__heading p,
.eduedge-batch-workspace__heading p,
.eduedge-card-answers__heading span,
.eduedge-batch-field small,
.eduedge-upload-guide,
.eduedge-upload-drop span {
	color: var(--edge-text-muted, #64748b);
}

.eduedge-common-fields,
.eduedge-question-card__grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
	gap: 1rem;
	margin-top: 1rem;
}

.eduedge-question-card__grid--marks {
	grid-template-columns: repeat(2, minmax(10rem, 14rem));
}

.eduedge-batch-field {
	display: grid;
	gap: 0.38rem;
	min-width: 0;
	font-size: 0.84rem;
	font-weight: 600;
	color: var(--edge-text-muted, #64748b);
}

.eduedge-batch-field b {
	color: var(--edge-danger, #dc2626);
}

.eduedge-batch-field--wide {
	margin-top: 1rem;
}

.eduedge-batch-lookup {
	position: relative;
}

.eduedge-batch-suggestions {
	position: absolute;
	top: calc(100% - 0.2rem);
	z-index: 20;
	display: grid;
	width: 100%;
	max-height: 15rem;
	overflow: auto;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-md, 0.7rem);
	background: var(--edge-surface, #fff);
	box-shadow: var(--edge-shadow-lg, 0 12px 24px rgba(15, 23, 42, 0.12));
}

.eduedge-batch-suggestions button {
	padding: 0.7rem;
	border: 0;
	border-bottom: 1px solid var(--edge-border, #e2e8f0);
	background: transparent;
	text-align: left;
}

.eduedge-batch-suggestions button:hover {
	background: var(--edge-primary-soft, #eff6ff);
}

.eduedge-question-cards {
	display: grid;
	gap: 1rem;
	margin-top: 1rem;
}

.eduedge-question-card {
	padding: 1rem;
}

.eduedge-question-card__heading {
	align-items: center;
	padding-bottom: 0.75rem;
	border-bottom: 1px solid var(--edge-border, #e2e8f0);
}

.eduedge-question-card__heading > div {
	display: flex;
	align-items: center;
	gap: 0.7rem;
}

.eduedge-question-number,
.eduedge-answer-option {
	display: inline-grid;
	place-items: center;
	width: 2rem;
	height: 2rem;
	border-radius: 999px;
	background: var(--edge-primary-soft, #eff6ff);
	color: var(--edge-primary, #1f6feb);
	font-weight: 700;
}

.eduedge-remove-question {
	border: 0;
	background: transparent;
	color: var(--edge-danger, #dc2626);
	font-weight: 600;
}

.eduedge-card-answers {
	margin-top: 1rem;
	padding: 1rem;
	border-radius: var(--edge-radius-md, 0.7rem);
	background: var(--edge-surface-subtle, #f8fafc);
}

.eduedge-card-answers__heading {
	align-items: center;
}

.eduedge-card-answers__heading > div {
	display: grid;
	gap: 0.2rem;
}

.eduedge-card-answer-list {
	display: grid;
	gap: 0.65rem;
	margin-top: 0.8rem;
}

.eduedge-card-answer-row {
	display: grid;
	grid-template-columns: auto minmax(12rem, 1fr) auto auto;
	align-items: center;
	gap: 0.7rem;
}

.eduedge-answer-correct {
	display: flex;
	align-items: center;
	gap: 0.35rem;
	margin: 0;
	font-weight: 600;
}

.eduedge-answer-controls {
	display: flex;
	gap: 0.25rem;
}

.eduedge-answer-controls button {
	width: 2rem;
	height: 2rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: 0.45rem;
	background: var(--edge-surface, #fff);
}

.eduedge-card-empty,
.eduedge-upload-guide {
	margin-top: 0.8rem;
	padding: 0.9rem;
	border: 1px dashed var(--edge-border, #cbd5e1);
	border-radius: var(--edge-radius-md, 0.7rem);
	background: var(--edge-surface, #fff);
}

.eduedge-card-empty {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
}

.eduedge-upload-guide code {
	font-size: 0.82rem;
}

.eduedge-upload-drop {
	display: grid;
	place-items: center;
	gap: 0.35rem;
	margin-top: 1rem;
	padding: 2rem;
	border: 2px dashed var(--edge-border, #cbd5e1);
	border-radius: var(--edge-radius-lg, 0.9rem);
	background: var(--edge-surface-subtle, #f8fafc);
	text-align: center;
	cursor: pointer;
}

.eduedge-upload-drop.has-file {
	border-color: var(--edge-primary, #1f6feb);
	background: var(--edge-primary-soft, #eff6ff);
}

.eduedge-upload-drop input {
	position: absolute;
	width: 1px;
	height: 1px;
	opacity: 0;
}

.eduedge-upload-actions {
	justify-content: flex-end;
	margin-top: 0.8rem;
}

.eduedge-preview-summary {
	display: grid;
	grid-template-columns: repeat(3, minmax(8rem, 1fr));
	gap: 0.75rem;
	margin-top: 1rem;
}

.eduedge-preview-summary div {
	display: grid;
	gap: 0.25rem;
	padding: 0.9rem;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-md, 0.7rem);
}

.eduedge-preview-summary span {
	color: var(--edge-text-muted, #64748b);
	font-size: 0.82rem;
}

.eduedge-preview-summary strong {
	font-size: 1.35rem;
}

.eduedge-preview-table-wrap {
	margin-top: 1rem;
	overflow: auto;
	border: 1px solid var(--edge-border, #e2e8f0);
	border-radius: var(--edge-radius-md, 0.7rem);
}

.eduedge-preview-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.84rem;
}

.eduedge-preview-table th,
.eduedge-preview-table td {
	padding: 0.7rem;
	border-bottom: 1px solid var(--edge-border, #e2e8f0);
	text-align: left;
	vertical-align: top;
}

.eduedge-preview-table th {
	background: var(--edge-surface-subtle, #f8fafc);
	white-space: nowrap;
}

.eduedge-preview-table tr.invalid {
	background: rgba(220, 38, 38, 0.04);
}

.eduedge-valid-row {
	color: var(--edge-success, #15803d);
	font-weight: 700;
}

.eduedge-invalid-row {
	color: var(--edge-danger, #dc2626);
}

.eduedge-batch-error,
.eduedge-batch-success {
	display: grid;
	gap: 0.25rem;
	margin-top: 1rem;
	padding: 0.9rem;
	border-radius: var(--edge-radius-md, 0.7rem);
}

.eduedge-batch-error {
	border: 1px solid rgba(220, 38, 38, 0.25);
	background: rgba(220, 38, 38, 0.06);
	color: var(--edge-danger, #b91c1c);
}

.eduedge-batch-success {
	border: 1px solid rgba(21, 128, 61, 0.25);
	background: rgba(21, 128, 61, 0.06);
	color: var(--edge-success, #166534);
}

@media (max-width: 760px) {
	.eduedge-batch-panel__heading,
	.eduedge-batch-workspace__heading,
	.eduedge-question-card__heading,
	.eduedge-card-answers__heading,
	.eduedge-card-empty {
		align-items: stretch;
		flex-direction: column;
	}

	.eduedge-card-answer-row {
		grid-template-columns: auto minmax(0, 1fr);
	}

	.eduedge-answer-correct,
	.eduedge-answer-controls {
		grid-column: 2;
	}

	.eduedge-preview-summary {
		grid-template-columns: 1fr;
	}
}
</style>
