<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="scopeContextLabel"
		branch-name="Template Builder"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-exam-template-builder"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="CBT Exam Design"
					:title="builderTitle"
					:subtitle="builderSubtitle"
					action-label="Back to Exam Templates"
					@action="openRoute('/app/eduedge-exam-templates')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading Template Builder..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Template Builder could not load"
				:message="error"
				action-label="Try again"
				@retry="loadTemplate"
			/>
			<template v-else>
				<section class="eduedge-template-summary">
					<div>
						<p class="edge-eyebrow">Template governance</p>
						<strong>{{ form.template_code || 'Unsaved template' }}</strong>
						<span>
							{{ form.exam_purpose }} · {{ form.template_reuse_scope }} · {{ form.subject_applicability }} · Version {{ form.version_number || 1 }}
						</span>
					</div>
					<EdgeStatusBadge :label="form.status || 'Draft'" :status="form.status || 'Draft'" :tone="statusTone(form.status)" />
				</section>

				<section class="eduedge-template-builder-panel">
					<div class="eduedge-template-panel-heading">
						<div>
							<p class="edge-eyebrow">Identity and reuse</p>
							<h2>Reusable template identity</h2>
							<p>Choose where the design can be reused and whether it applies to any Subject or only one Subject.</p>
						</div>
					</div>

					<div class="eduedge-template-grid">
						<label class="eduedge-template-field eduedge-template-field--wide">
							<span>Template Title <b>*</b></span>
							<input
								v-model.trim="form.template_title"
								class="form-control"
								:disabled="isReadOnly"
								placeholder="e.g. Secondary School Midterm CBT Blueprint"
							/>
						</label>

						<label class="eduedge-template-field">
							<span>Template Code <b>*</b></span>
							<input v-model.trim="form.template_code" class="form-control" :disabled="isReadOnly || Boolean(form.name)" placeholder="e.g. MIDTERM-CBT" />
							<small v-if="form.name">The code is fixed after the first save.</small>
						</label>

						<label class="eduedge-template-field">
							<span>Examination Scope <b>*</b></span>
							<select v-model="form.exam_scope" class="form-control" :disabled="isReadOnly" @change="examScopeChanged">
								<option v-for="option in context.scope_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label v-if="isSchoolExam" class="eduedge-template-field">
							<span>Template Reuse Scope <b>*</b></span>
							<select v-model="form.template_reuse_scope" class="form-control" :disabled="isReadOnly" @change="reuseScopeChanged">
								<option v-for="option in context.reuse_scope_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
							<small>{{ reuseScopeGuidance }}</small>
						</label>

						<label v-if="isSchoolExam" class="eduedge-template-field">
							<span>Company <b>*</b></span>
							<select v-model="form.company" class="form-control" :disabled="isReadOnly" @change="companyChanged">
								<option value="">Select Company</option>
								<option v-for="option in context.company_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label v-if="requiresInstitution" class="eduedge-template-field">
							<span>Institution <b>*</b></span>
							<select v-model="form.institution" class="form-control" :disabled="isReadOnly" @change="institutionChanged">
								<option value="">Select Institution</option>
								<option v-for="option in context.institution_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label v-if="requiresBranch" class="eduedge-template-field">
							<span>School Branch / Campus <b>*</b></span>
							<select v-model="form.school_branch" class="form-control" :disabled="isReadOnly" @change="branchChanged">
								<option value="">Select Branch</option>
								<option v-for="branch in context.allowed_branches" :key="branch.value" :value="branch.value">{{ branch.label }}</option>
							</select>
						</label>

						<label class="eduedge-template-field">
							<span>Exam Purpose <b>*</b></span>
							<select v-model="form.exam_purpose" class="form-control" :disabled="isReadOnly" @change="identityChanged">
								<option v-for="option in context.exam_purpose_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<label class="eduedge-template-field">
							<span>Template Content Mode <b>*</b></span>
							<select v-model="form.template_mode" class="form-control" :disabled="isReadOnly" @change="templateModeChanged">
								<option v-for="option in context.template_mode_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
							<small>{{ templateModeGuidance }}</small>
						</label>

						<label class="eduedge-template-field">
							<span>Subject Applicability <b>*</b></span>
							<select v-model="form.subject_applicability" class="form-control" :disabled="isReadOnly" @change="subjectApplicabilityChanged">
								<option v-for="option in context.subject_applicability_options" :key="option.value" :value="option.value">{{ option.label }}</option>
							</select>
						</label>

						<div v-if="isSpecificSubject" class="eduedge-template-field">
							<span>Subject / Course <b>*</b></span>
							<EdgeLinkField
								:model-value="form.course"
								:selected-label="labels.course"
								:searcher="(query) => searchOption('course', query)"
								placeholder="Search Subject or Course"
								:allow-clear="true"
								:open-on-focus="true"
								:disabled="isReadOnly"
								@select="(option) => selectLink('course', option, ['questions', 'supersedes_template'])"
								@clear="() => clearLink('course', ['questions', 'supersedes_template'])"
							/>
						</div>

						<label class="eduedge-template-field">
							<span>Exam Body / Source</span>
							<select v-model="form.exam_body" class="form-control" :disabled="isReadOnly" @change="identityChanged">
								<option v-for="body in context.exam_bodies" :key="body" :value="body">{{ body }}</option>
							</select>
						</label>

						<div class="eduedge-template-field">
							<span>Previous Template Version</span>
							<EdgeLinkField
								:model-value="form.supersedes_template"
								:selected-label="labels.supersedes_template"
								:searcher="(query) => searchOption('supersedes_template', query)"
								placeholder="Approved or Retired version"
								:allow-clear="true"
								:open-on-focus="true"
								:disabled="isReadOnly"
								@select="(option) => selectLink('supersedes_template', option)"
								@clear="() => clearLink('supersedes_template')"
							/>
						</div>
					</div>

					<div class="eduedge-template-reuse-note">
						<strong>{{ reuseExampleTitle }}</strong>
						<p>{{ reuseExampleText }}</p>
					</div>
				</section>

				<section v-if="isSchoolExam" class="eduedge-template-builder-panel">
					<div class="eduedge-template-panel-heading">
						<div>
							<p class="edge-eyebrow">Optional defaults</p>
							<h2>Academic defaults</h2>
							<p>These fields are optional. The actual exam schedule selects the Academic Year, Term, Programme and Class for each sitting.</p>
						</div>
					</div>
					<div class="eduedge-template-grid">
						<div v-for="field in academicLinkFields" :key="field.name" class="eduedge-template-field">
							<span>{{ field.label }}</span>
							<EdgeLinkField
								:model-value="form[field.name]"
								:selected-label="labels[field.name]"
								:searcher="(query) => searchOption(field.name, query)"
								:placeholder="`Search ${field.label}`"
								:allow-clear="true"
								:open-on-focus="true"
								:disabled="isReadOnly"
								@select="(option) => selectAcademicLink(field.name, option)"
								@clear="() => clearAcademicLink(field.name)"
							/>
						</div>
					</div>
				</section>

				<section class="eduedge-template-builder-panel">
					<div class="eduedge-template-panel-heading">
						<div>
							<p class="edge-eyebrow">Candidate control</p>
							<h2>Timing and examination policies</h2>
							<p>These reusable rules are snapshotted into each exam schedule so later template edits cannot change an active sitting.</p>
						</div>
					</div>
					<div class="eduedge-template-grid">
						<label class="eduedge-template-field"><span>Duration (Minutes) <b>*</b></span><input v-model.number="form.duration_minutes" type="number" min="1" class="form-control" :disabled="isReadOnly" /></label>
						<label class="eduedge-template-field"><span>Maximum Attempts <b>*</b></span><input v-model.number="form.maximum_attempts" type="number" min="1" class="form-control" :disabled="isReadOnly" /></label>
						<label class="eduedge-template-field"><span>Pass Percentage <b>*</b></span><input v-model.number="form.pass_percentage" type="number" min="0" max="100" class="form-control" :disabled="isReadOnly" /></label>
						<label class="eduedge-template-field"><span>Question Navigation</span><select v-model="form.navigation_policy" class="form-control" :disabled="isReadOnly"><option v-for="value in context.navigation_policies" :key="value" :value="value">{{ value }}</option></select></label>
						<label class="eduedge-template-field"><span>Marking Policy</span><select v-model="form.marking_policy" class="form-control" :disabled="isReadOnly"><option v-for="value in context.marking_policies" :key="value" :value="value">{{ value }}</option></select></label>
						<label class="eduedge-template-field"><span>Result Release Policy</span><select v-model="form.result_release_policy" class="form-control" :disabled="isReadOnly"><option v-for="value in context.result_release_policies" :key="value" :value="value">{{ value }}</option></select></label>
						<label class="eduedge-template-field"><span>Device Change Policy</span><select v-model="form.device_change_policy" class="form-control" :disabled="isReadOnly"><option v-for="value in context.device_change_policies" :key="value" :value="value">{{ value }}</option></select></label>
						<label class="eduedge-template-field"><span>Attempt Review Policy</span><select v-model="form.attempt_review_policy" class="form-control" :disabled="isReadOnly"><option v-for="value in context.attempt_review_policies" :key="value" :value="value">{{ value }}</option></select></label>
						<div class="eduedge-template-field">
							<span>Default Examination Centre</span>
							<EdgeLinkField
								:model-value="form.default_examination_centre"
								:selected-label="labels.default_examination_centre"
								:searcher="(query) => searchOption('default_examination_centre', query)"
								placeholder="Search active centre"
								:allow-clear="true"
								:open-on-focus="true"
								:disabled="isReadOnly"
								@select="(option) => selectLink('default_examination_centre', option)"
								@clear="() => clearLink('default_examination_centre')"
							/>
						</div>
					</div>

					<div class="eduedge-template-switches">
						<label><input v-model="form.auto_submit_on_timeout" type="checkbox" true-value="1" false-value="0" :disabled="isReadOnly" /><span>Auto-submit on Timeout</span></label>
						<label><input v-model="form.allow_resume" type="checkbox" true-value="1" false-value="0" :disabled="isReadOnly" /><span>Allow Resume</span></label>
						<label><input v-model="form.randomise_questions" type="checkbox" true-value="1" false-value="0" :disabled="isReadOnly" /><span>Randomise Question Order</span></label>
						<label><input v-model="form.randomise_options" type="checkbox" true-value="1" false-value="0" :disabled="isReadOnly" /><span>Randomise Objective Answer Options</span></label>
					</div>
				</section>

				<section v-if="isBlueprint" class="eduedge-template-builder-panel eduedge-template-blueprint-panel">
					<div class="eduedge-template-panel-heading">
						<div>
							<p class="edge-eyebrow">Reusable blueprint</p>
							<h2>No fixed questions required</h2>
							<p>The actual exam schedule or paper preparation flow will select the Branch, Subject and approved questions while inheriting this template’s policies.</p>
						</div>
						<EdgeStatusBadge label="Reusable" status="Reusable" tone="success" />
					</div>
				</section>

				<section v-else class="eduedge-template-builder-panel">
					<div class="eduedge-template-panel-heading">
						<div>
							<p class="edge-eyebrow">Fixed approved paper</p>
							<h2>Template questions</h2>
							<p>Only Approved questions matching this Branch and Specific Subject are available.</p>
						</div>
						<div class="eduedge-question-total"><strong>{{ localQuestionCount }}</strong><span>questions</span><strong>{{ localTotalMarks }}</strong><span>marks</span></div>
					</div>

					<div v-if="!isReadOnly" class="eduedge-template-question-search">
						<input
							v-model.trim="questionQuery"
							class="form-control"
							placeholder="Search approved question code, topic or question text"
							:disabled="!canSearchQuestions"
							@focus="searchQuestions"
							@input="scheduleQuestionSearch"
						/>
						<div v-if="questionSuggestions.length" class="eduedge-template-question-suggestions">
							<button v-for="option in questionSuggestions" :key="option.value" type="button" @click="addQuestion(option)">
								<strong>{{ option.label }}</strong><span>{{ option.description || 'Approved question' }}</span><small>{{ option.mark || 0 }} marks</small>
							</button>
						</div>
					</div>

					<EdgeEmptyState v-if="!form.questions.length" title="No questions added" description="Select a Branch and Specific Subject, then add approved questions." />
					<div v-else class="eduedge-template-question-list">
						<div v-for="(row, index) in form.questions" :key="`${row.question}-${index}`" class="eduedge-template-question-row">
							<div class="eduedge-template-order">{{ index + 1 }}</div>
							<div><strong>{{ row.question_label || row.question }}</strong><span>{{ row.topic || row.question_type || 'Approved question' }}</span></div>
							<input v-model.trim="row.section_label" class="form-control" placeholder="Optional section" :disabled="isReadOnly" />
							<div class="eduedge-template-marks"><strong>{{ row.mark || 0 }}</strong><span>marks</span><small v-if="row.negative_mark">-{{ row.negative_mark }}</small></div>
							<div v-if="!isReadOnly" class="eduedge-template-row-actions">
								<button type="button" :disabled="index === 0" @click="moveQuestion(index, -1)">↑</button>
								<button type="button" :disabled="index === form.questions.length - 1" @click="moveQuestion(index, 1)">↓</button>
								<button type="button" @click="removeQuestion(index)">×</button>
							</div>
						</div>
					</div>
				</section>

				<section class="eduedge-template-builder-panel">
					<div class="eduedge-template-panel-heading">
						<div><p class="edge-eyebrow">Candidate experience and audit</p><h2>Instructions and notes</h2></div>
					</div>
					<label class="eduedge-template-field eduedge-template-field--wide"><span>Instructions Shown Before the Exam</span><textarea v-model="form.candidate_instructions" class="form-control" rows="6" :disabled="isReadOnly"></textarea></label>
					<label class="eduedge-template-field eduedge-template-field--wide"><span>Internal Notes</span><textarea v-model="form.notes" class="form-control" rows="3" :disabled="isReadOnly"></textarea></label>
					<p v-if="form.reviewed_by" class="eduedge-template-audit">Approved by {{ form.reviewed_by }}<template v-if="form.reviewed_on"> on {{ form.reviewed_on }}</template>.</p>
				</section>

				<div v-if="saveError" class="eduedge-template-error" role="alert"><strong>Check the template before continuing</strong><div>{{ saveError }}</div></div>

				<EdgeActionBar :label="actionGuidance">
					<template #actions>
						<button type="button" class="edge-button" :disabled="working" @click="openRoute('/app/eduedge-exam-templates')">Cancel</button>
						<button v-if="context.permissions.can_open_technical_record && form.name" type="button" class="edge-button" :disabled="working" @click="openTechnicalRecord">Open Technical Record</button>
						<button v-if="context.permissions.can_create_version" type="button" class="edge-button" :disabled="working" @click="createVersion">Create New Version</button>
						<button v-if="context.permissions.can_write" type="button" class="edge-button" :disabled="working" @click="saveDraft">{{ working ? 'Saving...' : 'Save Draft' }}</button>
						<button v-if="actionAllowed('submit_for_review')" type="button" class="edge-button edge-button--primary" :disabled="working" @click="saveAndAction('submit_for_review')">Send for Review</button>
						<button v-if="actionAllowed('return_to_draft')" type="button" class="edge-button" :disabled="working" @click="confirmAction('return_to_draft')">Return to Draft</button>
						<button v-if="actionAllowed('approve')" type="button" class="edge-button edge-button--primary" :disabled="working" @click="confirmAction('approve')">Approve Template</button>
						<button v-if="actionAllowed('retire')" type="button" class="edge-button" :disabled="working" @click="confirmAction('retire')">Retire Template</button>
					</template>
				</EdgeActionBar>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const SCHOOL_EXAM = "School Examination";
const PUBLIC_EXAM = "EduEdge Public Examination";
const REUSE_UNIVERSAL = "Universal";
const REUSE_INSTITUTION = "Institution-wide";
const REUSE_BRANCH = "Branch-wide";
const SUBJECT_ANY = "Any Subject";
const SUBJECT_SPECIFIC = "Specific Subject";
const MODE_BLUEPRINT = "Policy Blueprint";
const MODE_FIXED = "Fixed Question Set";

function blankTemplate() {
	return {
		name: null,
		template_title: "",
		template_code: "",
		exam_scope: SCHOOL_EXAM,
		template_reuse_scope: REUSE_UNIVERSAL,
		company: "",
		institution: "",
		school_branch: "",
		exam_purpose: "Other",
		template_mode: MODE_BLUEPRINT,
		subject_applicability: SUBJECT_ANY,
		course: "",
		version_number: 1,
		supersedes_template: "",
		academic_year: "",
		academic_term: "",
		program: "",
		student_group: "",
		assessment_group: "",
		exam_body: "School Internal",
		default_examination_centre: "",
		duration_minutes: 60,
		maximum_attempts: 1,
		pass_percentage: 50,
		navigation_policy: "Free Navigation",
		auto_submit_on_timeout: 1,
		allow_resume: 1,
		randomise_questions: 1,
		randomise_options: 1,
		marking_policy: "Use Question Marks",
		result_release_policy: "Manual Approval",
		device_change_policy: "Invigilator Approval Required",
		attempt_review_policy: "Review Flagged Attempts Only",
		questions: [],
		question_count: 0,
		total_marks: 0,
		total_negative_marks: 0,
		candidate_instructions: "",
		status: "Draft",
		reviewed_by: "",
		reviewed_on: null,
		notes: "",
		modified: "",
	};
}

export default {
	name: "EduEdgeExamTemplateBuilder",
	props: { templateName: { type: String, default: null } },
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			working: false,
			error: "",
			saveError: "",
			currentTemplateName: this.templateName || null,
			form: blankTemplate(),
			context: {
				company_options: [],
				institution_options: [],
				allowed_branches: [],
				scope_options: [],
				reuse_scope_options: [],
				subject_applicability_options: [],
				template_mode_options: [],
				exam_purpose_options: [],
				exam_bodies: [],
				navigation_policies: [],
				marking_policies: [],
				result_release_policies: [],
				device_change_policies: [],
				attempt_review_policies: [],
				permissions: {},
				actions: [],
				user: {},
			},
			labels: {
				course: "",
				supersedes_template: "",
				academic_year: "",
				academic_term: "",
				program: "",
				student_group: "",
				assessment_group: "",
				default_examination_centre: "",
			},
			questionQuery: "",
			questionSuggestions: [],
			questionTimer: null,
		};
	},
	computed: {
		isSchoolExam() { return this.form.exam_scope === SCHOOL_EXAM; },
		isBlueprint() { return this.form.template_mode === MODE_BLUEPRINT; },
		isFixedSet() { return this.form.template_mode === MODE_FIXED; },
		isSpecificSubject() { return this.form.subject_applicability === SUBJECT_SPECIFIC; },
		requiresInstitution() { return this.isSchoolExam && [REUSE_INSTITUTION, REUSE_BRANCH].includes(this.form.template_reuse_scope); },
		requiresBranch() { return this.isSchoolExam && this.form.template_reuse_scope === REUSE_BRANCH; },
		isReadOnly() { return !this.context.permissions?.can_write; },
		builderTitle() { return this.form.name ? this.form.template_title || this.form.template_code : "Create Exam Template"; },
		builderSubtitle() { return this.form.name ? `${this.form.exam_scope} · ${this.form.status}` : "Create one reusable design for many exam sittings."; },
		scopeContextLabel() {
			if (!this.isSchoolExam) return "EduEdge Public Examination";
			if (this.form.template_reuse_scope === REUSE_BRANCH) return this.context.allowed_branches.find((row) => row.value === this.form.school_branch)?.label || "Branch-wide Template";
			if (this.form.template_reuse_scope === REUSE_INSTITUTION) return this.context.institution_options.find((row) => row.value === this.form.institution)?.label || "Institution-wide Template";
			return this.form.company || "Universal Template";
		},
		reuseScopeGuidance() {
			if (this.form.template_reuse_scope === REUSE_UNIVERSAL) return "Reusable across all permitted Institutions and Branches in this Company.";
			if (this.form.template_reuse_scope === REUSE_INSTITUTION) return "Reusable across all permitted Branches in the selected Institution.";
			return "Reusable only in the selected Branch. Required for school Fixed Question Sets.";
		},
		templateModeGuidance() {
			return this.isBlueprint
				? "Stores reusable exam rules without fixed questions."
				: "Stores one approved Subject paper with fixed questions.";
		},
		reuseExampleTitle() {
			if (this.form.exam_purpose === "Mock Examination") return "Example: one Mock Examination blueprint";
			if (this.form.exam_purpose === "Midterm Examination") return "Example: one Midterm Examination blueprint";
			return `Example: one ${this.form.exam_purpose || 'exam'} blueprint`;
		},
		reuseExampleText() {
			if (this.form.subject_applicability === SUBJECT_ANY) {
				return "The same approved template can be selected for Mathematics, English, Science or another Subject. Each exam schedule supplies the actual Subject, Branch, class and approved questions.";
			}
			return `The same approved ${this.labels.course || this.form.course || 'Subject'} template can be reused for multiple permitted sittings without recreating its timing and control policies.`;
		},
		academicLinkFields() {
			return [
				{ name: "academic_year", label: "Academic Year" },
				{ name: "academic_term", label: "Academic Term" },
				{ name: "program", label: "Programme" },
				{ name: "student_group", label: "Student Group / Class" },
				{ name: "assessment_group", label: "Assessment Group" },
			];
		},
		localQuestionCount() { return this.form.questions?.length || 0; },
		localTotalMarks() { return (this.form.questions || []).reduce((total, row) => total + Number(row.mark || 0), 0); },
		canSearchQuestions() {
			if (!this.isFixedSet || !this.isSpecificSubject || !this.form.course) return false;
			if (this.isSchoolExam) return this.form.template_reuse_scope === REUSE_BRANCH && Boolean(this.form.school_branch);
			return true;
		},
		actionGuidance() {
			if (this.form.status === "Draft") {
				return this.isBlueprint
					? "Save the reusable policy blueprint, then send it for review. No fixed questions are required."
					: "Add approved questions, save the fixed set, then send it for review.";
			}
			if (this.form.status === "Under Review") return "Template content is locked during review. Return it to Draft for changes or approve it for scheduling.";
			if (this.form.status === "Approved") return "Approved templates are immutable. Create a new version for changes or retire this version.";
			return "Retired templates remain available for audit and version history.";
		},
	},
	mounted() { this.loadTemplate(); },
	beforeUnmount() { if (this.questionTimer) clearTimeout(this.questionTimer); },
	methods: {
		openRoute: openEduEdgeRoute,
		applyContext(state) {
			this.context = state || this.context;
			this.form = { ...blankTemplate(), ...(state?.template || {}) };
			this.currentTemplateName = this.form.name || null;
			for (const key of Object.keys(this.labels)) this.labels[key] = this.form[key] || "";
			this.questionSuggestions = [];
			this.questionQuery = "";
			this.updateUrl();
		},
		async loadTemplate() {
			this.loading = true;
			this.error = "";
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.exam_templates.get_template_builder_context", { template: this.currentTemplateName || undefined });
				this.applyContext(response.message || {});
			} catch (error) {
				this.error = error?.message || "Template Builder could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		updateUrl() {
			if (!this.form.name || !window.history?.replaceState) return;
			const url = new URL(window.location.href);
			url.searchParams.set("template", this.form.name);
			window.history.replaceState({}, "", url.toString());
		},
		searchOption(fieldname, query) {
			return frappe.call("eduedge.api.exam_templates.search_template_options", {
				fieldname,
				txt: query || "",
				values: JSON.stringify(this.form),
			}).then((response) => response.message || []);
		},
		selectLink(fieldname, option, clear = []) {
			this.form[fieldname] = option?.value || "";
			this.labels[fieldname] = option?.label || this.form[fieldname];
			for (const key of clear) this.clearField(key);
		},
		clearLink(fieldname, clear = []) {
			this.form[fieldname] = "";
			this.labels[fieldname] = "";
			for (const key of clear) this.clearField(key);
		},
		clearField(fieldname) {
			if (fieldname === "questions") {
				this.form.questions = [];
				this.questionSuggestions = [];
				return;
			}
			this.form[fieldname] = "";
			if (Object.prototype.hasOwnProperty.call(this.labels, fieldname)) this.labels[fieldname] = "";
		},
		clearIdentityDependencies() {
			for (const key of ["supersedes_template", "default_examination_centre", "questions"]) this.clearField(key);
		},
		examScopeChanged() {
			this.clearIdentityDependencies();
			if (this.form.exam_scope === PUBLIC_EXAM) {
				this.form.template_reuse_scope = REUSE_UNIVERSAL;
				for (const key of ["company", "institution", "school_branch", "academic_year", "academic_term", "program", "student_group", "assessment_group"]) this.clearField(key);
			} else {
				this.form.template_reuse_scope = REUSE_UNIVERSAL;
				this.form.company = this.context.company_options?.[0]?.value || "";
			}
		},
		reuseScopeChanged() {
			this.clearIdentityDependencies();
			if (this.form.template_reuse_scope === REUSE_UNIVERSAL) {
				this.clearField("institution");
				this.clearField("school_branch");
			} else if (this.form.template_reuse_scope === REUSE_INSTITUTION) {
				this.clearField("school_branch");
			}
			if (this.isFixedSet && this.isSchoolExam && this.form.template_reuse_scope !== REUSE_BRANCH) {
				this.form.template_mode = MODE_BLUEPRINT;
			}
		},
		companyChanged() {
			this.clearField("institution");
			this.clearField("school_branch");
			this.clearField("course");
			this.clearIdentityDependencies();
			this.refreshBuilderOptions();
		},
		institutionChanged() {
			this.clearField("school_branch");
			this.clearField("course");
			this.clearIdentityDependencies();
			this.refreshBuilderOptions();
		},
		branchChanged() {
			this.clearField("course");
			this.clearIdentityDependencies();
		},
		identityChanged() { this.clearField("supersedes_template"); },
		templateModeChanged() {
			this.clearField("supersedes_template");
			if (this.form.template_mode === MODE_BLUEPRINT) {
				this.clearField("questions");
				return;
			}
			this.form.subject_applicability = SUBJECT_SPECIFIC;
			if (this.isSchoolExam) this.form.template_reuse_scope = REUSE_BRANCH;
		},
		subjectApplicabilityChanged() {
			this.clearField("supersedes_template");
			this.clearField("questions");
			if (this.form.subject_applicability === SUBJECT_ANY) {
				this.clearField("course");
				this.form.template_mode = MODE_BLUEPRINT;
			}
		},
		async refreshBuilderOptions() {
			if (!this.form.name) return;
			try {
				const response = await frappe.call("eduedge.api.exam_templates.get_template_builder_context", { template: this.form.name });
				const state = response.message || {};
				this.context = { ...this.context, ...state, template: undefined };
			} catch (_error) {
				// Save-time validation remains authoritative when option refresh is unavailable.
			}
		},
		selectAcademicLink(fieldname, option) {
			this.selectLink(fieldname, option);
			if (fieldname === "academic_year") {
				this.clearField("academic_term");
				this.clearField("student_group");
			}
			if (["academic_term", "program"].includes(fieldname)) this.clearField("student_group");
		},
		clearAcademicLink(fieldname) {
			this.clearField(fieldname);
			if (fieldname === "academic_year") this.clearField("academic_term");
			if (["academic_year", "academic_term", "program"].includes(fieldname)) this.clearField("student_group");
		},
		scheduleQuestionSearch() {
			if (this.questionTimer) clearTimeout(this.questionTimer);
			this.questionTimer = setTimeout(this.searchQuestions, 250);
		},
		async searchQuestions() {
			if (!this.canSearchQuestions || this.isReadOnly) {
				this.questionSuggestions = [];
				return;
			}
			try {
				const options = await this.searchOption("question", this.questionQuery);
				const selected = new Set((this.form.questions || []).map((row) => row.question));
				this.questionSuggestions = options.filter((row) => !selected.has(row.value));
			} catch (error) {
				this.saveError = error?.message || "Approved questions could not be loaded.";
			}
		},
		addQuestion(option) {
			if (!option?.value || (this.form.questions || []).some((row) => row.question === option.value)) return;
			this.form.questions.push({
				question: option.value,
				question_label: option.label || option.value,
				display_order: this.form.questions.length + 1,
				section_label: "",
				question_type: option.question_type || "",
				topic: option.topic || "",
				mark: Number(option.mark || 0),
				negative_mark: Number(option.negative_mark || 0),
			});
			this.questionSuggestions = this.questionSuggestions.filter((row) => row.value !== option.value);
		},
		removeQuestion(index) { this.form.questions.splice(index, 1); this.reindexQuestions(); },
		moveQuestion(index, direction) {
			const target = index + direction;
			if (target < 0 || target >= this.form.questions.length) return;
			const rows = [...this.form.questions];
			[rows[index], rows[target]] = [rows[target], rows[index]];
			this.form.questions = rows;
			this.reindexQuestions();
		},
		reindexQuestions() { this.form.questions = this.form.questions.map((row, index) => ({ ...row, display_order: index + 1 })); },
		validateForm({ forReview = false } = {}) {
			const errors = [];
			if (!this.form.template_title?.trim()) errors.push("Template Title is required.");
			if (!this.form.template_code?.trim()) errors.push("Template Code is required.");
			if (!this.form.exam_purpose) errors.push("Exam Purpose is required.");
			if (this.isSchoolExam && !this.form.company) errors.push("Company is required.");
			if (this.requiresInstitution && !this.form.institution) errors.push("Institution is required.");
			if (this.requiresBranch && !this.form.school_branch) errors.push("School Branch / Campus is required.");
			if (this.isSpecificSubject && !this.form.course) errors.push("Subject / Course is required.");
			if (this.isFixedSet && this.form.subject_applicability !== SUBJECT_SPECIFIC) errors.push("A Fixed Question Set requires a Specific Subject.");
			if (this.isFixedSet && this.isSchoolExam && this.form.template_reuse_scope !== REUSE_BRANCH) errors.push("A school Fixed Question Set must be Branch-wide.");
			if (forReview && this.isFixedSet && !this.form.questions.length) errors.push("Add at least one approved question before review.");
			if (Number(this.form.duration_minutes || 0) < 1) errors.push("Duration must be greater than zero.");
			if (Number(this.form.maximum_attempts || 0) < 1) errors.push("Maximum Attempts must be at least one.");
			return errors;
		},
		async saveDraft({ silent = false, forReview = false } = {}) {
			if (this.working || !this.context.permissions?.can_write) return false;
			const errors = this.validateForm({ forReview });
			if (errors.length) {
				this.saveError = errors.join(" ");
				return false;
			}
			this.working = true;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.exam_templates.save_template", { payload: JSON.stringify(this.form) });
				this.applyContext(response.message || {});
				if (!silent) frappe.show_alert({ message: __("Template saved successfully."), indicator: "green" }, 5);
				return true;
			} catch (error) {
				this.saveError = error?.message || "The template could not be saved.";
				return false;
			} finally {
				this.working = false;
			}
		},
		actionByName(action) { return (this.context.actions || []).find((row) => row.action === action) || null; },
		actionAllowed(action) { return Boolean(this.actionByName(action)?.allowed); },
		async saveAndAction(action) {
			const saved = await this.saveDraft({ silent: true, forReview: action === "submit_for_review" });
			if (!saved) return;
			await this.executeAction(action);
		},
		confirmAction(action) {
			const state = this.actionByName(action);
			if (!state?.allowed) {
				this.saveError = state?.reason || "This action is not available.";
				return;
			}
			frappe.confirm(__(`${state.label}? This will change the Template Status.`), () => this.executeAction(action));
		},
		async executeAction(action) {
			if (this.working || !this.form.name) return;
			this.working = true;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.exam_templates.perform_template_action", {
					template: this.form.name,
					action,
					expected_modified: this.form.modified || undefined,
				});
				const actionLabel = this.actionByName(action)?.label || __("Template action completed.");
				this.applyContext(response.message || {});
				frappe.show_alert({ message: actionLabel, indicator: "green" }, 5);
			} catch (error) {
				this.saveError = error?.message || "The Template action could not be completed.";
			} finally {
				this.working = false;
			}
		},
		async createVersion() {
			if (this.working || !this.form.name) return;
			this.working = true;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.exam_templates.create_template_version", { template: this.form.name });
				this.applyContext(response.message || {});
				frappe.show_alert({ message: __("New Template version created."), indicator: "green" }, 5);
			} catch (error) {
				this.saveError = error?.message || "A new Template version could not be created.";
			} finally {
				this.working = false;
			}
		},
		openTechnicalRecord() {
			if (this.form.name) window.open(`/app/eduedge-cbt-exam-template/${encodeURIComponent(this.form.name)}`, "_blank", "noopener,noreferrer");
		},
		statusTone(status) { return ({ Draft: "neutral", "Under Review": "warning", Approved: "success", Retired: "danger" })[status] || "neutral"; },
	},
};
</script>

<style scoped>
.eduedge-template-summary { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 1rem; margin-bottom: 1rem; border: 1px solid var(--edge-border, #e2e8f0); border-radius: 1rem; background: var(--edge-surface, #fff); }
.eduedge-template-summary > div { display: grid; gap: .2rem; }
.eduedge-template-summary p, .eduedge-template-summary span { margin: 0; color: var(--edge-text-muted, #64748b); }
.eduedge-template-builder-panel { border: 1px solid var(--edge-border, #e2e8f0); border-radius: 1rem; background: var(--edge-surface, #fff); padding: 1rem; margin-bottom: 1rem; }
.eduedge-template-blueprint-panel { background: var(--edge-surface-muted, #f8fafc); }
.eduedge-template-panel-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1rem; }
.eduedge-template-panel-heading h2, .eduedge-template-panel-heading p { margin: 0; }
.eduedge-template-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: .9rem; }
.eduedge-template-field { display: grid; gap: .35rem; min-width: 0; }
.eduedge-template-field > span { font-size: .8rem; font-weight: 700; color: var(--edge-text-muted, #64748b); }
.eduedge-template-field--wide { grid-column: 1 / -1; margin-bottom: .8rem; }
.eduedge-template-field small { color: var(--edge-text-muted, #64748b); }
.eduedge-template-reuse-note { margin-top: 1rem; padding: .85rem 1rem; border: 1px solid var(--edge-border, #e2e8f0); border-radius: .75rem; background: var(--edge-surface-muted, #f8fafc); }
.eduedge-template-reuse-note p { margin: .25rem 0 0; color: var(--edge-text-muted, #64748b); }
.eduedge-template-switches { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: .7rem; margin-top: 1rem; }
.eduedge-template-switches label { display: flex; gap: .55rem; align-items: center; padding: .7rem; border: 1px solid var(--edge-border, #e2e8f0); border-radius: .65rem; }
.eduedge-question-total { display: grid; grid-template-columns: auto auto; gap: 0 .35rem; align-items: baseline; text-align: right; }
.eduedge-question-total strong { font-size: 1.1rem; }
.eduedge-question-total span { color: var(--edge-text-muted, #64748b); font-size: .75rem; }
.eduedge-template-question-search { position: relative; margin-bottom: 1rem; }
.eduedge-template-question-suggestions { position: absolute; z-index: 20; left: 0; right: 0; top: calc(100% + .25rem); max-height: 18rem; overflow: auto; background: var(--edge-surface, #fff); border: 1px solid var(--edge-border, #e2e8f0); border-radius: .75rem; box-shadow: 0 12px 30px rgba(15, 23, 42, .12); }
.eduedge-template-question-suggestions button { width: 100%; border: 0; border-top: 1px solid var(--edge-border, #e2e8f0); background: transparent; padding: .75rem; text-align: left; display: grid; grid-template-columns: 1fr auto; gap: .15rem .7rem; }
.eduedge-template-question-suggestions button:hover { background: var(--edge-surface-muted, #f8fafc); }
.eduedge-template-question-suggestions span { color: var(--edge-text-muted, #64748b); }
.eduedge-template-question-suggestions small { grid-row: 1 / 3; grid-column: 2; align-self: center; }
.eduedge-template-question-list { display: grid; gap: .55rem; }
.eduedge-template-question-row { display: grid; grid-template-columns: 2rem minmax(14rem, 2fr) minmax(10rem, 1fr) 5rem auto; gap: .7rem; align-items: center; padding: .7rem; border: 1px solid var(--edge-border, #e2e8f0); border-radius: .7rem; }
.eduedge-template-order { width: 2rem; height: 2rem; border-radius: 999px; display: grid; place-items: center; background: var(--edge-surface-muted, #f8fafc); font-weight: 700; }
.eduedge-template-question-row > div:nth-child(2), .eduedge-template-marks { display: grid; gap: .12rem; }
.eduedge-template-question-row span, .eduedge-template-question-row small { color: var(--edge-text-muted, #64748b); }
.eduedge-template-row-actions { display: flex; gap: .25rem; }
.eduedge-template-row-actions button { border: 1px solid var(--edge-border, #e2e8f0); background: transparent; border-radius: .4rem; min-width: 2rem; height: 2rem; }
.eduedge-template-audit { padding: .75rem; background: var(--edge-surface-muted, #f8fafc); border-radius: .65rem; }
.eduedge-template-error { padding: .85rem 1rem; margin-bottom: 1rem; border: 1px solid #fecaca; background: #fef2f2; border-radius: .75rem; color: #991b1b; }
@media (max-width: 900px) { .eduedge-template-question-row { grid-template-columns: 2rem 1fr; } .eduedge-template-question-row > *:not(.eduedge-template-order) { grid-column: 2; } }
</style>
