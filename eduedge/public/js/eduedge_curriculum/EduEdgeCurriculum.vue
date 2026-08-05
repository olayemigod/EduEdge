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
				<EdgeFilterBar :title="`${courseSingular} context`">
					<div class="curriculum-filters">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="branchChanged">
								<option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option>
							</select>
						</label>
						<label>
							<span>Search {{ coursePlural }}</span>
							<input v-model.trim="filters.search" class="form-control" :placeholder="`Search ${coursePlural.toLowerCase()}`" @keyup.enter="load(true)" />
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="clearSearch">Clear</button>
						<button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Apply</button>
					</template>
				</EdgeFilterBar>

				<EdgeActionBar
					v-if="data.permissions?.is_assigned_teacher"
					:label="`Teacher access is limited to ${coursePlural.toLowerCase()} covered by your active Instructor Assignments for this Branch. ${courseSingular} identity remains controlled by academic management.`"
				/>
				<p v-if="error" class="curriculum-error">{{ error }}</p>

				<section class="curriculum-layout">
					<article class="curriculum-panel curriculum-register">
						<div class="curriculum-heading">
							<div><p class="edge-eyebrow">Curriculum register</p><h2>{{ coursePlural }}</h2></div>
							<button v-if="canCreateCourse" type="button" class="edge-button" @click="newCourse">New {{ courseSingular }}</button>
						</div>
						<EdgeLoadingState v-if="loading" :message="`Refreshing ${coursePlural.toLowerCase()}...`" />
						<EdgeEmptyState
							v-else-if="!data.courses.length"
							:title="`No ${coursePlural.toLowerCase()} available`"
							:description="data.permissions?.is_assigned_teacher ? `No active Instructor Assignment currently grants you a ${courseSingular.toLowerCase()} in this Branch.` : `Create the first ${courseSingular.toLowerCase()} for this Institution.`"
						/>
						<div v-else class="curriculum-list">
							<button
								v-for="row in data.courses"
								:key="row.name"
								type="button"
								class="curriculum-card"
								:class="{ 'is-selected': courseDraft.name === row.name }"
								@click="editCourse(row.name)"
							>
								<span><strong>{{ row.course_name || row.name }}</strong><small>{{ row.department || 'No Department / School Section' }}</small></span>
								<EdgeStatusBadge :label="row.can_manage ? 'Manage' : 'View'" :status="row.can_manage ? 'manage' : 'view'" :tone="row.can_manage ? 'success' : 'neutral'" />
							</button>
						</div>
						<div class="curriculum-paging">
							<button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button>
							<span>{{ data.paging.start + (data.courses.length ? 1 : 0) }}–{{ data.paging.start + data.courses.length }}</span>
							<button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button>
						</div>
					</article>

					<article class="curriculum-panel curriculum-editor">
						<div class="curriculum-heading">
							<div><p class="edge-eyebrow">{{ courseDraft.name ? `${courseSingular} workspace` : `New ${courseSingular}` }}</p><h2>{{ courseDraft.course_name || `New ${courseSingular}` }}</h2></div>
							<div class="curriculum-actions">
								<button v-if="courseDraft.name" type="button" class="edge-button" @click="openCourseForm">Open full form</button>
								<button v-if="canManageCourse" type="button" class="edge-button edge-button--primary" :disabled="savingCourse || !courseCanSave" @click="saveCourse">{{ savingCourse ? 'Saving...' : `Save ${courseSingular}` }}</button>
							</div>
						</div>

						<EdgeEmptyState v-if="!courseDraft.name && !canCreateCourse" :title="`Select an assigned ${courseSingular.toLowerCase()}`" :description="`Choose one of your assigned ${coursePlural.toLowerCase()} to manage its description and ${topicPlural.toLowerCase()}.`" />
						<template v-else>
							<div class="curriculum-grid">
								<label>
									<span>{{ courseSingular }} Name *</span>
									<input v-model.trim="courseDraft.course_name" class="form-control" :disabled="!canEditCourseIdentity || Boolean(courseDraft.name)" />
								</label>
								<label>
									<span>Department / School Section</span>
									<select v-model="courseDraft.department" class="form-control" :disabled="!canEditCourseIdentity">
										<option value="">Not assigned</option>
										<option v-for="row in data.departments" :key="row.name" :value="row.name">{{ row.department_name || row.name }}</option>
									</select>
								</label>
								<label class="wide">
									<span>{{ courseSingular }} Description</span>
									<textarea v-model="courseDraft.description" class="form-control" rows="4" :disabled="!canManageCourse" :placeholder="`Describe the learning scope and purpose of this ${courseSingular.toLowerCase()}.`"></textarea>
								</label>
							</div>

							<section v-if="courseDraft.name" class="topic-workspace">
								<div class="curriculum-heading">
									<div><p class="edge-eyebrow">Scheme and learning content</p><h3>{{ topicPlural }}</h3></div>
									<button v-if="canManageCourse && canCreateTopic" type="button" class="edge-button" @click="newTopic">Add {{ topicSingular }}</button>
								</div>
								<EdgeEmptyState v-if="!courseTopics.length" :title="`No ${topicPlural.toLowerCase()} linked`" :description="`Add the first ${topicSingular.toLowerCase()} to this ${courseSingular.toLowerCase()}.`" />
								<div v-else class="topic-list">
									<button v-for="row in courseTopics" :key="row.name" type="button" class="topic-card" :class="{ 'is-selected': topicDraft.name === row.name }" @click="editTopic(row.name)">
										<span><strong>{{ row.topic_name || row.name }}</strong><small>{{ row.description || 'No description' }}</small></span>
									</button>
								</div>

								<div v-if="showTopicEditor" class="topic-editor">
									<div class="curriculum-heading">
										<div><p class="edge-eyebrow">{{ topicDraft.name ? `${topicSingular} details` : `New ${topicSingular}` }}</p><h3>{{ topicDraft.topic_name || `New ${topicSingular}` }}</h3></div>
										<div class="curriculum-actions">
											<button v-if="topicDraft.name" type="button" class="edge-button" @click="openTopicForm">Open full content</button>
											<button type="button" class="edge-button edge-button--primary" :disabled="savingTopic || !topicCanSave" @click="saveTopic">{{ savingTopic ? 'Saving...' : `Save ${topicSingular}` }}</button>
										</div>
									</div>
									<div class="curriculum-grid">
										<label><span>{{ topicSingular }} Name *</span><input v-model.trim="topicDraft.topic_name" class="form-control" :disabled="Boolean(topicDraft.name)" /></label>
										<label class="wide"><span>{{ topicSingular }} Description</span><textarea v-model="topicDraft.description" class="form-control" rows="4" :placeholder="`Describe the learning objectives or coverage for this ${topicSingular.toLowerCase()}.`"></textarea></label>
									</div>
									<small class="text-muted">Use Open full content for structured Topic Content rows and attachments. Existing topic identity is not renamed from this quick workspace.</small>
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

const blankCourse = () => ({ name: "", course_name: "", department: "", description: "", topics: [], can_manage: false, can_edit_identity: false });
const blankTopic = () => ({ name: "", topic_name: "", description: "", eduedge_course: "", can_manage: false });
const blankData = () => ({
	allowed_branches: [], selected_branch: {}, courses: [], course: null, topic: null, departments: [],
	permissions: {}, paging: { start: 0, page_length: 50, has_more: false },
});

export default {
	name: "EduEdgeCurriculum",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS, loading: true, loaded: false, savingCourse: false, savingTopic: false,
			error: "", saveError: "", filters: { branch: "", search: "", start: 0 }, data: blankData(),
			courseDraft: blankCourse(), topicDraft: blankTopic(), showTopicEditor: false,
		};
	},
	computed: {
		courseSingular() { return this.term("course", false, "Course / Subject"); },
		coursePlural() { return this.term("course", true, "Courses / Subjects"); },
		topicSingular() { return this.term("topic", false, "Topic"); },
		topicPlural() { return this.term("topic", true, "Topics"); },
		pageTitle() { return `${this.coursePlural} & ${this.topicPlural}`; },
		pageSubtitle() { return `Manage institution-approved ${this.coursePlural.toLowerCase()} and let assigned teachers maintain the learning ${this.topicPlural.toLowerCase()} for their current academic responsibilities.`; },
		canCreateCourse() { return Boolean(this.data.permissions?.can_create_course); },
		canEditCourseIdentity() { return Boolean(!this.courseDraft.name ? this.canCreateCourse : this.courseDraft.can_edit_identity); },
		canManageCourse() { return Boolean(this.courseDraft.name ? this.courseDraft.can_manage : this.canCreateCourse); },
		canCreateTopic() { return Boolean(this.data.permissions?.can_create_topic); },
		courseCanSave() { return Boolean(this.canManageCourse && this.courseDraft.course_name); },
		topicCanSave() { return Boolean(this.canManageCourse && this.canCreateTopic && this.courseDraft.name && this.topicDraft.topic_name); },
		courseTopics() { return this.courseDraft.topics || []; },
	},
	async mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.filters.branch = params.get("branch") || "";
		await this.load(true, params.get("course") || "", params.get("topic") || "");
	},
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") {
			return frappe.eduedge?.term?.(key, { plural, context: this.data.selected_branch || {}, fallback }) || fallback;
		},
		async load(reset = false, course = "", topic = "") {
			if (reset) this.filters.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.curriculum_management.get_curriculum_page", {
					branch: this.filters.branch || undefined, course: course || undefined, topic: topic || undefined,
					search: this.filters.search || undefined, start: this.filters.start, page_length: this.data.paging.page_length || 50,
				});
				this.data = response.message || blankData();
				this.filters.branch = this.data.selected_branch?.name || this.filters.branch;
				this.loaded = true;
				if (this.data.course) {
					this.courseDraft = { ...blankCourse(), ...this.data.course, topics: this.data.course.topics || [] };
					if (this.data.topic) {
						this.topicDraft = { ...blankTopic(), ...this.data.topic };
						this.showTopicEditor = true;
					} else {
						this.topicDraft = blankTopic(); this.showTopicEditor = false;
					}
				} else if (!this.courseDraft.name) {
					this.courseDraft = blankCourse(); this.topicDraft = blankTopic(); this.showTopicEditor = false;
				}
			} catch (error) { this.error = error?.message || "Curriculum Management could not be loaded."; }
			finally { this.loading = false; }
		},
		async branchChanged() { this.courseDraft = blankCourse(); this.topicDraft = blankTopic(); this.showTopicEditor = false; await this.load(true); },
		clearSearch() { this.filters.search = ""; this.load(true); },
		newCourse() { if (!this.canCreateCourse) return; this.courseDraft = { ...blankCourse(), can_manage: true, can_edit_identity: true }; this.topicDraft = blankTopic(); this.showTopicEditor = false; this.saveError = ""; },
		async editCourse(name) { await this.load(false, name); },
		newTopic() { if (!this.canManageCourse || !this.canCreateTopic) return; this.topicDraft = { ...blankTopic(), eduedge_course: this.courseDraft.name, can_manage: true }; this.showTopicEditor = true; this.saveError = ""; },
		async editTopic(name) { if (!this.courseDraft.name) return; await this.load(false, this.courseDraft.name, name); },
		async saveCourse() {
			if (!this.courseCanSave) return;
			this.savingCourse = true; this.saveError = "";
			try {
				const response = await frappe.call({
					method: "eduedge.api.curriculum_management.save_course", type: "POST",
					args: { payload: JSON.stringify({ ...this.courseDraft, branch: this.filters.branch }) },
				});
				const saved = response.message || {};
				frappe.show_alert({ message: __(`${this.courseSingular} saved`), indicator: "green" });
				await this.load(true, saved.name);
			} catch (error) { this.saveError = error?.message || `${this.courseSingular} could not be saved.`; }
			finally { this.savingCourse = false; }
		},
		async saveTopic() {
			if (!this.topicCanSave) return;
			this.savingTopic = true; this.saveError = "";
			try {
				const response = await frappe.call({
					method: "eduedge.api.curriculum_management.save_topic", type: "POST",
					args: { payload: JSON.stringify({ ...this.topicDraft, branch: this.filters.branch, course: this.courseDraft.name }) },
				});
				const saved = response.message || {};
				frappe.show_alert({ message: __(`${this.topicSingular} saved`), indicator: "green" });
				await this.load(false, this.courseDraft.name, saved.name);
			} catch (error) { this.saveError = error?.message || `${this.topicSingular} could not be saved.`; }
			finally { this.savingTopic = false; }
		},
		openCourseForm() { if (this.courseDraft.name) window.open(`/app/course/${encodeURIComponent(this.courseDraft.name)}`, "_blank", "noopener,noreferrer"); },
		openTopicForm() { if (this.topicDraft.name) window.open(`/app/topic/${encodeURIComponent(this.topicDraft.name)}`, "_blank", "noopener,noreferrer"); },
		previousPage() { this.filters.start = Math.max(0, this.filters.start - this.data.paging.page_length); this.load(); },
		nextPage() { if (this.data.paging.has_more) { this.filters.start += this.data.paging.page_length; this.load(); } },
	},
};
</script>

<style scoped>
.curriculum-filters,.curriculum-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; width:100%; }
.curriculum-filters label,.curriculum-grid label { display:grid; gap:.35rem; font-weight:600; }
.curriculum-layout { display:grid; grid-template-columns:minmax(18rem,.72fr) minmax(0,1.45fr); gap:1rem; margin-top:1rem; }
.curriculum-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.curriculum-heading,.curriculum-actions,.curriculum-paging { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }
.curriculum-heading h2,.curriculum-heading h3 { margin:.2rem 0 0; }
.curriculum-list,.topic-list { display:grid; gap:.65rem; }
.curriculum-card,.topic-card { display:flex; align-items:center; justify-content:space-between; gap:.75rem; width:100%; padding:.75rem; text-align:left; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.curriculum-card:hover,.curriculum-card.is-selected,.topic-card:hover,.topic-card.is-selected { border-color:var(--primary); }
.curriculum-card span,.topic-card span { display:grid; gap:.15rem; min-width:0; }.curriculum-card small,.topic-card small { color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.curriculum-grid .wide { grid-column:1/-1; }.topic-workspace { display:grid; gap:.85rem; padding-top:.85rem; border-top:1px solid var(--border-color); }.topic-editor { display:grid; gap:.75rem; padding:.85rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }
.curriculum-error { color:var(--red-600,#b42318); margin:0; }
@media (max-width:1000px) { .curriculum-layout { grid-template-columns:1fr; } }
@media (max-width:700px) { .curriculum-filters,.curriculum-grid { grid-template-columns:1fr; }.curriculum-grid .wide { grid-column:auto; } }
</style>
