<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="data.selected_branch?.institution_name || ''"
		:branch-name="data.selected_branch?.branch_name || pageTitle"
		:menu-items="menuItems"
		active-route="/app/eduedge-curriculum"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Operations"
					:title="pageTitle"
					:subtitle="pageSubtitle"
					:action-label="canCreateCourse ? `New ${courseSingular}` : ''"
					@action="newCourse"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" :message="`Loading ${pageTitle.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Curriculum could not load" :message="error" action-label="Try again" @retry="load(true)" />
			<template v-else>
				<EdgeFilterBar title="Teaching context">
					<div class="curriculum-filters">
						<label><span>Branch / Campus</span><select v-model="filters.branch" class="form-control" @change="branchChanged"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
						<label><span>Class / Programme Offering</span><select v-model="filters.program_offering" class="form-control" @change="offeringChanged"><option value="">{{ data.permissions?.is_assigned_teacher ? 'Select assigned Class' : 'Institution-wide Subject masters' }}</option><option v-for="row in data.offerings" :key="row.name" :value="row.name">{{ row.offering_title || row.name }} · {{ row.academic_year }}{{ row.academic_term ? ` · ${row.academic_term}` : '' }}</option></select></label>
						<label><span>Class Arm</span><select v-model="filters.student_group" class="form-control" :disabled="!filters.program_offering" @change="groupChanged"><option value="">All Class Arms / Class-wide</option><option v-for="row in data.groups" :key="row.name" :value="row.name">{{ row.eduedge_display_name || row.student_group_name || row.name }}</option></select></label>
						<label><span>Search {{ coursePlural }}</span><input v-model.trim="filters.search" class="form-control" :placeholder="`Search ${coursePlural.toLowerCase()}`" @keyup.enter="load(true)" /></label>
					</div>
					<template #actions><button type="button" class="edge-button" @click="clearSearch">Clear search</button><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Apply</button></template>
				</EdgeFilterBar>

				<EdgeActionBar
					v-if="data.permissions?.is_assigned_teacher"
					:label="filters.program_offering ? `Your access is limited to ${coursePlural.toLowerCase()} assigned to you for this Class${filters.student_group ? ' and Class Arm' : ''}. Institution-wide grading governance remains read-only.` : 'Select an assigned Class before managing curriculum delivery.'"
				/>
				<p v-if="error" class="curriculum-error">{{ error }}</p>

				<section class="curriculum-layout">
					<article class="curriculum-panel curriculum-register">
						<div class="curriculum-heading"><div><p class="edge-eyebrow">{{ filters.program_offering ? 'Class curriculum' : 'Institution curriculum' }}</p><h2>{{ coursePlural }}</h2></div><button v-if="canCreateCourse" type="button" class="edge-button" @click="newCourse">New {{ courseSingular }}</button></div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${coursePlural.toLowerCase()}...`" />
						<EdgeEmptyState v-else-if="!data.courses.length" :title="`No ${coursePlural.toLowerCase()} available`" :description="data.permissions?.is_assigned_teacher ? `No active Teacher Assignment grants you a ${courseSingular.toLowerCase()} in the selected Class context.` : filters.program_offering ? `No ${coursePlural.toLowerCase()} are configured in this Class / Programme.` : `Create the first Institution-wide ${courseSingular.toLowerCase()}.`" />
						<div v-else class="curriculum-list">
							<button v-for="row in data.courses" :key="row.name" type="button" class="curriculum-card" :class="{ 'is-selected': courseDraft.name === row.name }" @click="editCourse(row.name)">
								<span><strong>{{ row.course_name || row.name }}</strong><small>{{ row.department || 'No Department / School Section' }}{{ row.default_grading_scale ? ` · ${row.default_grading_scale}` : '' }}</small></span>
								<EdgeStatusBadge :label="row.assignments?.length ? 'Assigned' : 'Institution Master'" :status="row.assignments?.length ? 'assigned' : 'master'" :tone="row.assignments?.length ? 'success' : 'neutral'" />
							</button>
						</div>
						<div class="curriculum-paging"><button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.courses.length ? 1 : 0) }}–{{ data.paging.start + data.courses.length }}</span><button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button></div>
					</article>

					<article class="curriculum-panel curriculum-editor">
						<div class="curriculum-heading">
							<div><p class="edge-eyebrow">{{ courseDraft.name ? `${courseSingular} workspace` : `New ${courseSingular}` }}</p><h2>{{ courseDraft.course_name || `New ${courseSingular}` }}</h2></div>
							<div class="curriculum-actions"><button v-if="courseDraft.name" type="button" class="edge-button" @click="openCourseForm">Open full form</button><button v-if="canManageCourseMaster" type="button" class="edge-button edge-button--primary" :disabled="savingCourse || !courseCanSave" @click="saveCourse">{{ savingCourse ? 'Saving...' : `Save ${courseSingular}` }}</button></div>
						</div>

						<EdgeEmptyState v-if="!courseDraft.name && !canCreateCourse" :title="`Select an assigned ${courseSingular.toLowerCase()}`" :description="`Choose a Class, then select one of your assigned ${coursePlural.toLowerCase()} to manage its scoped ${topicPlural.toLowerCase()}, CBT content and assessment work.`" />
						<template v-else>
							<section class="curriculum-section">
								<div class="curriculum-heading"><div><p class="edge-eyebrow">Institution-wide master</p><h3>{{ courseSingular }} identity</h3></div><EdgeStatusBadge label="Institution-wide" status="institution" tone="neutral" /></div>
								<div class="curriculum-grid">
									<label><span>{{ courseSingular }} Name *</span><input v-model.trim="courseDraft.course_name" class="form-control" :disabled="!canManageCourseMaster || Boolean(courseDraft.name)" /></label>
									<label><span>Department / School Section</span><select v-model="courseDraft.department" class="form-control" :disabled="!canManageCourseMaster"><option value="">Not assigned</option><option v-for="row in data.departments" :key="row.name" :value="row.name">{{ row.department_name || row.name }}</option></select></label>
									<label class="wide"><span>{{ courseSingular }} Description</span><textarea v-model="courseDraft.description" class="form-control" rows="4" :disabled="!canManageCourseMaster" :placeholder="`Institution-wide purpose and scope of this ${courseSingular.toLowerCase()}.`"></textarea></label>
								</div>
							</section>

							<section class="curriculum-section assessment-governance">
								<div class="curriculum-heading"><div><p class="edge-eyebrow">Native Education configuration</p><h3>Assessment & Grading</h3><small>These values are stored on the native {{ courseSingular }} record and apply Institution-wide.</small></div><EdgeStatusBadge :label="canManageCourseMaster ? 'Manager controlled' : 'Read only'" status="grading" :tone="canManageCourseMaster ? 'success' : 'neutral'" /></div>
								<label><span>Default Grading Scale</span><select v-model="courseDraft.default_grading_scale" class="form-control" :disabled="!canManageCourseMaster"><option value="">No default grading scale</option><option v-for="row in data.grading_scales" :key="row.name" :value="row.name">{{ row.grading_scale_name || row.name }}</option></select></label>
								<div class="curriculum-heading"><strong>Assessment Criteria</strong><div class="curriculum-actions"><span :class="{ 'weight-invalid': assessmentTotal && assessmentTotal !== 100 }">Total: {{ assessmentTotal }}%</span><button v-if="canManageCourseMaster" type="button" class="edge-button" @click="addAssessmentCriterion">Add Criterion</button></div></div>
								<EdgeEmptyState v-if="!courseDraft.assessment_criteria.length" title="No assessment criteria configured" description="Add criteria such as Continuous Assessment and Examination, with weightage totalling 100%." />
								<div v-else class="assessment-list"><div v-for="(row,index) in courseDraft.assessment_criteria" :key="`${row.assessment_criteria}-${index}`" class="assessment-row"><select v-model="row.assessment_criteria" class="form-control" :disabled="!canManageCourseMaster"><option value="">Select Assessment Criteria</option><option v-for="option in data.assessment_criteria_options" :key="option.name" :value="option.name">{{ option.assessment_criteria || option.name }}{{ option.assessment_criteria_group ? ` · ${option.assessment_criteria_group}` : '' }}</option></select><div class="weight-field"><input v-model.number="row.weightage" type="number" min="0" max="100" class="form-control" :disabled="!canManageCourseMaster" /><span>%</span></div><button v-if="canManageCourseMaster" type="button" class="edge-button" @click="removeAssessmentCriterion(index)">Remove</button></div></div>
							</section>

							<section v-if="courseDraft.name" class="curriculum-section topic-workspace">
								<div class="curriculum-heading"><div><p class="edge-eyebrow">{{ filters.student_group ? 'Class Arm delivery' : filters.program_offering ? 'Class delivery' : 'Institution curriculum' }}</p><h3>{{ topicPlural }}</h3><small>Institution Topics remain reusable; teachers create and edit only Topics scoped to their assigned Class or Class Arm.</small></div><button v-if="canAddTopic" type="button" class="edge-button" @click="newTopic">Add {{ topicSingular }}</button></div>
								<EdgeEmptyState v-if="!courseTopics.length" :title="`No ${topicPlural.toLowerCase()} visible in this context`" :description="filters.program_offering ? `Add the first ${topicSingular.toLowerCase()} for this Class context.` : `Add an Institution-wide ${topicSingular.toLowerCase()} or select a Class.`" />
								<div v-else class="topic-list"><button v-for="row in courseTopics" :key="row.name" type="button" class="topic-card" :class="{ 'is-selected': topicDraft.name === row.name }" @click="editTopic(row.name)"><span><strong>{{ row.topic_name || row.name }}</strong><small>{{ row.description || 'No description' }}</small></span><div class="curriculum-actions"><EdgeStatusBadge :label="row.scope || row.eduedge_topic_scope || 'Institution-wide'" :status="row.scope || 'topic'" :tone="row.can_manage ? 'success' : 'neutral'" /><span>{{ row.can_manage ? 'Manage' : 'View' }}</span></div></button></div>
								<div v-if="showTopicEditor" class="topic-editor">
									<div class="curriculum-heading"><div><p class="edge-eyebrow">{{ topicDraft.name ? `${topicSingular} details` : `New ${topicSingular}` }}</p><h3>{{ topicDraft.topic_name || `New ${topicSingular}` }}</h3></div><div class="curriculum-actions"><button v-if="topicDraft.name" type="button" class="edge-button" @click="openTopicForm">Open full content</button><button v-if="topicDraft.can_manage !== false" type="button" class="edge-button edge-button--primary" :disabled="savingTopic || !topicCanSave" @click="saveTopic">{{ savingTopic ? 'Saving...' : `Save ${topicSingular}` }}</button></div></div>
									<div class="curriculum-grid">
										<label><span>{{ topicSingular }} Name *</span><input v-model.trim="topicDraft.topic_name" class="form-control" :disabled="Boolean(topicDraft.name) || topicDraft.can_manage === false" /></label>
										<label><span>Teaching Scope *</span><select v-model="topicDraft.scope" class="form-control" :disabled="Boolean(topicDraft.name) || topicDraft.can_manage === false || data.permissions?.is_assigned_teacher" @change="topicScopeChanged"><option v-for="scope in data.topic_scopes" :key="scope" :value="scope">{{ scope }}</option></select></label>
										<label v-if="topicDraft.scope !== 'Institution-wide'"><span>Class / Programme Offering</span><select v-model="topicDraft.eduedge_program_offering" class="form-control" :disabled="Boolean(topicDraft.name) || data.permissions?.is_assigned_teacher"><option v-for="row in data.offerings" :key="row.name" :value="row.name">{{ row.offering_title || row.name }}</option></select></label>
										<label v-if="topicDraft.scope === 'Class Arm'"><span>Class Arm</span><select v-model="topicDraft.eduedge_student_group" class="form-control" :disabled="Boolean(topicDraft.name) || data.permissions?.is_assigned_teacher"><option value="">Select Class Arm</option><option v-for="row in data.groups" :key="row.name" :value="row.name">{{ row.eduedge_display_name || row.student_group_name || row.name }}</option></select></label>
										<label class="wide"><span>{{ topicSingular }} Description</span><textarea v-model="topicDraft.description" class="form-control" rows="4" :disabled="topicDraft.can_manage === false" :placeholder="`Learning objectives or coverage for this ${topicSingular.toLowerCase()}.`"></textarea></label>
									</div>
									<small class="text-muted">Use Open full content for structured Topic Content rows and attachments. A saved Topic cannot be moved to another Subject, Class, or Class Arm by an assigned teacher.</small>
								</div>
							</section>
						</template>
						<p v-if="saveError" class="curriculum-error">{{ saveError }}</p>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankCourse = () => ({ name: "", course_name: "", department: "", description: "", default_grading_scale: "", assessment_criteria: [], topics: [], assignments: [], can_manage_master: false });
const blankTopic = () => ({ name: "", topic_name: "", description: "", scope: "Institution-wide", eduedge_course: "", eduedge_program_offering: "", eduedge_student_group: "", can_manage: true });
const blankData = () => ({ allowed_branches: [], selected_branch: {}, offerings: [], selected_offering: null, groups: [], selected_group: null, courses: [], course: null, topic: null, departments: [], grading_scales: [], assessment_criteria_options: [], topic_scopes: [], permissions: {}, paging: { start: 0, page_length: 50, has_more: false } });

export default {
	name: "EduEdgeCurriculum",
	data() { return { menuItems: EDUEDGE_MENU_ITEMS, loading: true, loaded: false, savingCourse: false, savingTopic: false, error: "", saveError: "", filters: { branch: "", program_offering: "", student_group: "", search: "", start: 0 }, data: blankData(), courseDraft: blankCourse(), topicDraft: blankTopic(), showTopicEditor: false }; },
	computed: {
		courseSingular() { return this.term("course", false, "Subject / Course"); }, coursePlural() { return this.term("course", true, "Subjects / Courses"); },
		topicSingular() { return this.term("topic", false, "Topic"); }, topicPlural() { return this.term("topic", true, "Topics"); },
		pageTitle() { return `${this.coursePlural} & ${this.topicPlural}`; },
		pageSubtitle() { return `Manage Institution-wide ${this.coursePlural.toLowerCase()} and class-aware ${this.topicPlural.toLowerCase()}, grading and teaching responsibility.`; },
		canCreateCourse() { return Boolean(this.data.permissions?.can_create_course && !this.filters.program_offering); },
		canManageCourseMaster() { return Boolean(this.data.permissions?.is_manager && (this.courseDraft.name ? this.data.permissions?.can_write_course : this.canCreateCourse)); },
		canAddTopic() { return Boolean(this.courseDraft.name && this.data.permissions?.can_create_topic && (this.data.permissions?.is_manager || (this.filters.program_offering && this.courseDraft.assignments?.length))); },
		courseCanSave() { return Boolean(this.canManageCourseMaster && this.courseDraft.course_name && (!this.courseDraft.assessment_criteria.length || this.assessmentTotal === 100)); },
		topicCanSave() { if (!this.topicDraft.topic_name || this.topicDraft.can_manage === false) return false; if (this.topicDraft.scope === "Institution-wide") return Boolean(this.data.permissions?.is_manager); if (!this.topicDraft.eduedge_program_offering) return false; if (this.topicDraft.scope === "Class Arm" && !this.topicDraft.eduedge_student_group) return false; return true; },
		courseTopics() { return this.courseDraft.topics || []; },
		assessmentTotal() { return Math.round((this.courseDraft.assessment_criteria || []).reduce((sum,row) => sum + Number(row.weightage || 0), 0) * 1000) / 1000; },
	},
	async mounted() { const params = new URLSearchParams(window.location.search || ""); this.filters.branch = params.get("branch") || ""; this.filters.program_offering = params.get("offering") || params.get("program_offering") || ""; this.filters.student_group = params.get("student_group") || ""; await this.load(true, params.get("course") || "", params.get("topic") || ""); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.data.selected_branch || {}, fallback }) || fallback; },
		async load(reset = false, course = "", topic = "") {
			if (reset) this.filters.start = 0; this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.curriculum_management.get_curriculum_page", { branch: this.filters.branch || undefined, program_offering: this.filters.program_offering || undefined, student_group: this.filters.student_group || undefined, course: course || undefined, topic: topic || undefined, search: this.filters.search || undefined, start: this.filters.start, page_length: this.data.paging.page_length || 50 });
				this.data = response.message || blankData(); this.filters.branch = this.data.selected_branch?.name || this.filters.branch; this.loaded = true;
				if (this.data.course) { this.courseDraft = { ...blankCourse(), ...this.data.course, assessment_criteria: (this.data.course.assessment_criteria || []).map((row) => ({ ...row })), topics: this.data.course.topics || [], assignments: this.data.course.assignments || [] }; if (this.data.topic) { this.topicDraft = this.normaliseTopic(this.data.topic); this.showTopicEditor = true; } else { this.topicDraft = blankTopic(); this.showTopicEditor = false; } }
				else if (!this.courseDraft.name) this.courseDraft = blankCourse();
			} catch (error) { this.error = error?.message || "Curriculum could not be loaded."; }
			finally { this.loading = false; }
		},
		normaliseTopic(row) { return { ...blankTopic(), ...row, scope: row.scope || row.eduedge_topic_scope || "Institution-wide", eduedge_program_offering: row.eduedge_program_offering || "", eduedge_student_group: row.eduedge_student_group || "" }; },
		async branchChanged() { this.filters.program_offering = ""; this.filters.student_group = ""; this.courseDraft = blankCourse(); this.topicDraft = blankTopic(); this.showTopicEditor = false; await this.load(true); },
		async offeringChanged() { this.filters.student_group = ""; this.courseDraft = blankCourse(); this.topicDraft = blankTopic(); this.showTopicEditor = false; await this.load(true); },
		async groupChanged() { this.courseDraft = blankCourse(); this.topicDraft = blankTopic(); this.showTopicEditor = false; await this.load(true); },
		async clearSearch() { this.filters.search = ""; await this.load(true); },
		newCourse() { this.courseDraft = blankCourse(); this.topicDraft = blankTopic(); this.showTopicEditor = false; this.saveError = ""; },
		editCourse(name) { this.load(false, name); },
		addAssessmentCriterion() { this.courseDraft.assessment_criteria.push({ assessment_criteria: "", weightage: 0 }); },
		removeAssessmentCriterion(index) { this.courseDraft.assessment_criteria.splice(index, 1); },
		async saveCourse() { if (!this.courseCanSave) return; this.savingCourse = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.curriculum_management.save_course", type: "POST", args: { payload: JSON.stringify({ ...this.courseDraft, branch: this.filters.branch, program_offering: this.filters.program_offering, student_group: this.filters.student_group }) } }); const saved = response.message || {}; frappe.show_alert({ message: __(`${this.courseSingular} saved`), indicator: "green" }); await this.load(true, saved.name); } catch (error) { this.saveError = error?.message || `${this.courseSingular} could not be saved.`; } finally { this.savingCourse = false; } },
		newTopic() { let scope = "Institution-wide"; if (this.filters.student_group) scope = "Class Arm"; else if (this.filters.program_offering) scope = "Class / Programme Offering"; if (!this.data.topic_scopes.includes(scope)) scope = this.data.topic_scopes[0] || scope; this.topicDraft = { ...blankTopic(), scope, eduedge_course: this.courseDraft.name, eduedge_program_offering: scope === "Institution-wide" ? "" : this.filters.program_offering, eduedge_student_group: scope === "Class Arm" ? this.filters.student_group : "", can_manage: true }; this.showTopicEditor = true; this.saveError = ""; },
		editTopic(name) { this.load(false, this.courseDraft.name, name); },
		topicScopeChanged() { if (this.topicDraft.scope === "Institution-wide") { this.topicDraft.eduedge_program_offering = ""; this.topicDraft.eduedge_student_group = ""; } else { this.topicDraft.eduedge_program_offering = this.topicDraft.eduedge_program_offering || this.filters.program_offering; if (this.topicDraft.scope === "Class Arm") this.topicDraft.eduedge_student_group = this.topicDraft.eduedge_student_group || this.filters.student_group; else this.topicDraft.eduedge_student_group = ""; } },
		async saveTopic() { if (!this.topicCanSave) return; this.savingTopic = true; this.saveError = ""; try { const response = await frappe.call({ method: "eduedge.api.curriculum_management.save_topic", type: "POST", args: { payload: JSON.stringify({ ...this.topicDraft, branch: this.filters.branch, course: this.courseDraft.name, program_offering: this.topicDraft.eduedge_program_offering, student_group: this.topicDraft.eduedge_student_group }) } }); const saved = response.message || {}; frappe.show_alert({ message: __(`${this.topicSingular} saved`), indicator: "green" }); await this.load(false, this.courseDraft.name, saved.name); } catch (error) { this.saveError = error?.message || `${this.topicSingular} could not be saved.`; } finally { this.savingTopic = false; } },
		openCourseForm() { if (this.courseDraft.name) window.open(`/app/course/${encodeURIComponent(this.courseDraft.name)}`, "_blank", "noopener,noreferrer"); },
		openTopicForm() { if (this.topicDraft.name) window.open(`/app/topic/${encodeURIComponent(this.topicDraft.name)}`, "_blank", "noopener,noreferrer"); },
		previousPage() { this.filters.start = Math.max(0, this.filters.start - this.data.paging.page_length); this.load(); }, nextPage() { if (this.data.paging.has_more) { this.filters.start += this.data.paging.page_length; this.load(); } },
	},
};
</script>

<style scoped>
.curriculum-filters,.curriculum-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; width:100%; }.curriculum-filters { grid-template-columns:repeat(4,minmax(0,1fr)); }.curriculum-filters label,.curriculum-grid label,.assessment-governance>label { display:grid; gap:.35rem; font-weight:600; }.curriculum-layout { display:grid; grid-template-columns:minmax(18rem,.75fr) minmax(0,1.5fr); gap:1rem; margin-top:1rem; }.curriculum-panel,.curriculum-section { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.curriculum-section { background:var(--control-bg); }.curriculum-heading,.curriculum-actions { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }.curriculum-heading h2,.curriculum-heading h3 { margin:.15rem 0 0; }.curriculum-list,.topic-list,.assessment-list { display:grid; gap:.65rem; }.curriculum-card,.topic-card { display:flex; align-items:center; justify-content:space-between; gap:.75rem; width:100%; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); text-align:left; }.topic-card { background:var(--card-bg); }.curriculum-card:hover,.curriculum-card.is-selected,.topic-card:hover,.topic-card.is-selected { border-color:var(--primary); }.curriculum-card>span,.topic-card>span { display:grid; gap:.15rem; }.curriculum-card small,.topic-card small,.curriculum-heading small { color:var(--text-muted); }.curriculum-grid .wide { grid-column:1/-1; }.assessment-row { display:grid; grid-template-columns:minmax(0,1fr) 8rem auto; gap:.65rem; align-items:center; }.weight-field { display:flex; align-items:center; gap:.35rem; }.weight-invalid { color:var(--red-600,#b42318); font-weight:700; }.topic-editor { display:grid; gap:1rem; padding:1rem; border:1px solid var(--border-color); border-radius:8px; background:var(--card-bg); }.curriculum-paging { display:flex; justify-content:space-between; align-items:center; }.curriculum-error { color:var(--red-600,#b42318); } @media (max-width:1100px) { .curriculum-layout { grid-template-columns:1fr; }.curriculum-filters { grid-template-columns:repeat(2,minmax(0,1fr)); } } @media (max-width:700px) { .curriculum-filters,.curriculum-grid,.assessment-row { grid-template-columns:1fr; }.curriculum-grid .wide { grid-column:auto; }.curriculum-heading,.curriculum-actions { align-items:stretch; flex-direction:column; } }
</style>
