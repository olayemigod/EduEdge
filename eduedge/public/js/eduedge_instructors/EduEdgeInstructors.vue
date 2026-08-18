<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="data.selected_institution_name || 'All Institutions'"
		:branch-name="data.selected_branch?.branch_name || 'Instructor Register'"
		:menu-items="menuItems"
		active-route="/app/eduedge-instructors"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="People Operations"
					title="Instructors"
					subtitle="Maintain Institution-wide Instructor identities, optional home Branches, qualifications and cross-Institution operational assignments."
					:action-label="canCreate ? 'Add Instructor' : ''"
					@action="newInstructor"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Instructors..." :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Instructors could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<EdgeFilterBar title="Instructor filters">
					<div class="people-filters">
						<label>
							<span>Institution</span>
							<select v-model="filters.institution" class="form-control" @change="filterInstitutionChanged">
								<option v-if="data.can_view_all_institutions" :value="data.all_institutions_key">All Institutions</option>
								<option v-for="row in data.allowed_institutions" :key="row.name" :value="row.name">{{ row.institution_name || row.name }}</option>
							</select>
						</label>
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="branchChanged">
								<option value="">All Branches / Campuses</option>
								<option v-for="row in filterBranches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}{{ filters.institution === data.all_institutions_key ? ` · ${row.institution_name || row.institution}` : '' }}</option>
							</select>
						</label>
						<label class="wide"><span>Search</span><input v-model.trim="filters.search" class="form-control" placeholder="Instructor name, ID, email or mobile" @keyup.enter="load(true)" /></label>
					</div>
					<template #actions><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Apply</button></template>
				</EdgeFilterBar>

				<p v-if="error" class="people-error">{{ error }}</p>
				<section class="people-layout">
					<article class="people-panel">
						<div class="people-heading"><div><p class="edge-eyebrow">Institution staff register</p><h2>Instructors</h2></div><button v-if="canCreate" type="button" class="edge-button" @click="newInstructor">Add Instructor</button></div>
						<EdgeLoadingState v-if="loading" message="Refreshing Instructors..." />
						<EdgeEmptyState v-else-if="!data.instructors.length" title="No Instructors found" description="Create an Institution-wide Instructor profile or change the filters." />
						<div v-else class="people-list">
							<button v-for="row in data.instructors" :key="row.name" type="button" class="person-card" :class="{ 'is-selected': draft.name === row.name }" @click="editInstructor(row.name)">
								<div class="avatar"><img v-if="row.image" :src="row.image" :alt="row.instructor_name" /><span v-else>{{ initials(row.instructor_name) }}</span></div>
								<span><strong>{{ row.instructor_name || row.name }}</strong><small>{{ row.institution_name || 'No Home Institution' }} · {{ row.primary_branch_name || 'Institution-wide' }}</small><small>{{ row.department || 'No department' }} · {{ row.eduedge_mobile || row.eduedge_email || row.name }}</small></span>
								<div class="status-stack">
									<EdgeStatusBadge :label="row.status || 'Active'" :status="row.status || 'active'" :tone="row.status === 'Left' ? 'danger' : 'success'" />
									<EdgeStatusBadge v-if="row.identity?.status" :label="row.identity.status" :status="row.identity.status" :tone="identityTone(row.identity)" />
								</div>
							</button>
						</div>
						<div class="paging"><button type="button" class="edge-button" :disabled="data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.instructors.length ? 1 : 0) }}–{{ data.paging.start + data.instructors.length }}</span><button type="button" class="edge-button" :disabled="!data.paging.has_more" @click="nextPage">Next</button></div>
					</article>

					<article class="people-panel editor">
						<div class="people-heading">
							<div><p class="edge-eyebrow">Official Instructor profile</p><h2>{{ draft.name ? draft.instructor_name || draft.name : 'New Instructor' }}</h2></div>
							<div class="actions"><button v-if="draft.name" type="button" class="edge-button" @click="openAssignments">Instructor Assignments</button><button v-if="draft.name" type="button" class="edge-button" @click="openFullForm">Open full form</button><button type="button" class="edge-button edge-button--primary" :disabled="saving || !canSave" @click="save">{{ saving ? 'Saving...' : 'Save Instructor' }}</button></div>
						</div>

						<EdgeActionBar label="Home Institution is the Instructor's administrative home. It does not restrict cross-Institution Branch, Class, Class Arm or Subject assignments." />
						<div v-if="draft.name && draft.identity?.status" class="identity-readiness" :class="`is-${draft.identity.severity || 'warning'}`">
							<div><strong>Teaching identity: {{ draft.identity.status }}</strong><small>{{ draft.identity.message }}</small></div>
							<div class="identity-meta">
								<span>Employee: {{ draft.identity.employee_name || draft.identity.employee || 'Not linked' }}</span>
								<span>User: {{ draft.identity.user_full_name || draft.identity.user || 'No login' }}</span>
							</div>
						</div>
						<div class="profile-summary"><div class="photo"><img v-if="draft.image" :src="draft.image" :alt="draft.instructor_name || 'Instructor photo'" /><span v-else>{{ initials(draft.instructor_name) }}</span></div><div><strong>Instructor photograph</strong><small>Used on staff identity and teaching records.</small></div><button v-if="draft.name && canEdit" type="button" class="edge-button" @click="uploadPhoto">Upload / replace</button></div>

						<div class="people-grid">
							<label><span>Instructor name *</span><input v-model.trim="draft.instructor_name" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Status</span><select v-model="draft.status" class="form-control" :disabled="!canEdit"><option>Active</option><option>Left</option></select></label>
							<label><span>Home Institution *</span><select v-model="draft.eduedge_institution" class="form-control" :disabled="!canEdit" @change="homeInstitutionChanged"><option value="">Select Home Institution</option><option v-for="row in data.allowed_institutions" :key="row.name" :value="row.name">{{ row.institution_name || row.name }}</option></select></label>
							<label><span>Primary Branch / Campus</span><select v-model="draft.eduedge_primary_branch" class="form-control" :disabled="!canEdit || !draft.eduedge_institution"><option value="">Institution-wide / no Primary Branch</option><option v-for="row in profileBranches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select><small>Optional. Other Branches are granted through Instructor Assignments.</small></label>
							<label><span>Department / School Section</span><select v-model="draft.department" class="form-control" :disabled="!canEdit || !draft.eduedge_institution"><option value="">Not assigned</option><option v-for="row in profileDepartments" :key="row.name" :value="row.name">{{ row.department_name || row.name }}</option></select></label>
							<label><span>Linked Employee</span><select v-model="draft.employee" class="form-control" :disabled="!canEdit || optionsLoading || !draft.eduedge_institution"><option value="">No Employee link</option><option v-for="row in data.employees" :key="row.name" :value="row.name">{{ row.employee_name || row.name }}{{ row.user_id ? ` · ${row.user_id}` : ' · no login' }}</option></select><small>Only active Employees from the Home Institution's Company are loaded. Assignment-driven teaching access requires one active User → Employee → Instructor mapping.</small></label>
							<label><span>Gender</span><select v-model="draft.gender" class="form-control" :disabled="!canEdit"><option value="">Not specified</option><option v-for="row in data.genders" :key="row.name" :value="row.name">{{ row.name }}</option></select></label>
							<label><span>Email</span><input v-model.trim="draft.eduedge_email" type="email" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Mobile number</span><input v-model.trim="draft.eduedge_mobile" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Employment type</span><select v-model="draft.eduedge_employment_type" class="form-control" :disabled="!canEdit"><option value="">Not specified</option><option>Full-Time</option><option>Part-Time</option><option>Contract</option><option>Visiting</option><option>Volunteer</option></select></label>
							<label class="wide"><span>Qualification</span><textarea v-model.trim="draft.eduedge_qualification" class="form-control" rows="2" :disabled="!canEdit"></textarea></label>
							<label class="wide"><span>Specialisation</span><textarea v-model.trim="draft.eduedge_specialisation" class="form-control" rows="2" :disabled="!canEdit"></textarea></label>
						</div>

						<template v-if="draft.name">
							<h3>Branch eligibility</h3>
							<EdgeEmptyState v-if="!draft.branch_eligibility?.length" title="Institution-wide profile" description="No Branch eligibility has been assigned yet." />
							<div v-else class="assignment-list"><article v-for="row in draft.branch_eligibility" :key="row.name"><strong>{{ branchLabel(row.school_branch) }}</strong><small>{{ row.is_primary ? 'Primary Branch' : 'Additional Branch' }} · {{ row.enabled ? 'Active' : 'Disabled' }}</small></article></div>
							<h3>Instructor Assignment History</h3>
							<EdgeEmptyState v-if="!draft.assignments?.length" title="No Instructor Assignment" description="Assign this Instructor to one or more Institutions, Branches, Classes, Class Arms and Subjects." />
							<div v-else class="assignment-list"><article v-for="row in draft.assignments" :key="row.name"><strong>{{ row.assignment_title || row.assignment_type }}</strong><small>{{ institutionLabel(row.institution) }} · {{ branchLabel(row.school_branch) }} · {{ row.student_group || row.program_offering }} · {{ row.course || 'Whole class' }} · {{ row.enabled ? 'Enabled' : 'Disabled' }}</small></article></div>
						</template>
						<p v-if="saveError" class="people-error">{{ saveError }}</p>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankInstructor = (institution = "", branch = "") => ({
	name: "", instructor_name: "", employee: "", gender: "", status: "Active", department: "",
	eduedge_institution: institution, eduedge_primary_branch: branch, eduedge_email: "", eduedge_mobile: "",
	eduedge_qualification: "", eduedge_specialisation: "", eduedge_employment_type: "", image: "",
	assignments: [], branch_eligibility: [], identity: null,
});
const blankData = () => ({
	all_institutions_key: "__all__", can_view_all_institutions: false, allowed_institutions: [], allowed_branches: [],
	selected_institution: {}, selected_institution_name: "", selected_branch: {}, filters: {}, instructors: [], instructor: null,
	departments: [], employees: [], genders: [], permissions: {}, paging: { start: 0, page_length: 25, has_more: false },
});

export default {
	name: "EduEdgeInstructors",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS, loading: true, loaded: false, saving: false, optionsLoading: false,
			error: "", saveError: "", filters: { institution: "", branch: "", search: "", start: 0 },
			data: blankData(), draft: blankInstructor(), profileDepartments: [],
		};
	},
	computed: {
		canCreate() { return Boolean(this.data.permissions?.can_create); },
		canEdit() { return this.draft.name ? Boolean(this.data.permissions?.can_write) : this.canCreate; },
		canSave() { return Boolean(this.canEdit && this.draft.instructor_name && this.draft.eduedge_institution); },
		filterBranches() {
			if (!this.filters.institution || this.filters.institution === this.data.all_institutions_key) return this.data.allowed_branches;
			return this.data.allowed_branches.filter((row) => row.institution === this.filters.institution);
		},
		profileBranches() { return this.data.allowed_branches.filter((row) => row.institution === this.draft.eduedge_institution); },
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		initials(value) { return String(value || "I").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); },
		identityTone(identity) { return identity?.severity === "danger" ? "danger" : identity?.severity === "warning" ? "warning" : identity?.severity === "neutral" ? "neutral" : "success"; },
		institutionLabel(name) { return this.data.allowed_institutions.find((row) => row.name === name)?.institution_name || name || "Institution not resolved"; },
		branchLabel(name) { return this.data.allowed_branches.find((row) => row.name === name)?.branch_name || name || "Institution-wide"; },
		async load(reset = false, instructor = "") {
			if (reset) this.filters.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.instructor_profiles.get_instructors_page", {
					institution: this.filters.institution || undefined, branch: this.filters.branch || undefined,
					search: this.filters.search || undefined, instructor: instructor || undefined,
					start: this.filters.start, page_length: this.data.paging.page_length || 25,
				});
				this.data = response.message || blankData();
				this.filters.institution = this.data.filters?.institution || this.filters.institution;
				this.filters.branch = this.data.filters?.branch || "";
				this.loaded = true;
				if (instructor && this.data.instructor) {
					this.draft = { ...blankInstructor(), ...this.data.instructor };
					await this.loadProfileOptions(this.draft.eduedge_institution);
				} else if (!this.draft.name) {
					const home = this.filters.institution === this.data.all_institutions_key ? "" : this.filters.institution;
					this.draft = blankInstructor(home, "");
					this.profileDepartments = this.data.departments || [];
				}
			} catch (error) { this.error = error?.message || "Instructors could not be loaded."; }
			finally { this.loading = false; }
		},
		async loadProfileOptions(institution) {
			this.profileDepartments = [];
			this.data.employees = [];
			if (!institution) return;
			this.optionsLoading = true;
			try {
				const response = await frappe.call("eduedge.api.instructor_profiles.get_instructors_page", { institution, start: 0, page_length: 1 });
				this.profileDepartments = response.message?.departments || [];
				this.data.employees = response.message?.employees || [];
			} catch (error) { this.saveError = error?.message || "Instructor Institution options could not be loaded."; }
			finally { this.optionsLoading = false; }
		},
		async filterInstitutionChanged() {
			this.filters.branch = "";
			this.draft = blankInstructor(this.filters.institution === this.data.all_institutions_key ? "" : this.filters.institution, "");
			await this.load(true);
		},
		branchChanged() { this.draft = blankInstructor(this.filters.institution === this.data.all_institutions_key ? "" : this.filters.institution, ""); this.load(true); },
		async homeInstitutionChanged() {
			if (!this.profileBranches.some((row) => row.name === this.draft.eduedge_primary_branch)) this.draft.eduedge_primary_branch = "";
			this.draft.department = "";
			this.draft.employee = "";
			await this.loadProfileOptions(this.draft.eduedge_institution);
		},
		async newInstructor() {
			const home = this.filters.institution === this.data.all_institutions_key ? "" : this.filters.institution;
			this.draft = blankInstructor(home, ""); this.saveError = "";
			await this.loadProfileOptions(home);
		},
		editInstructor(name) { this.load(false, name); },
		async save() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call({ method: "eduedge.api.instructor_profiles.save_instructor", type: "POST", args: { payload: JSON.stringify(this.draft) } });
				this.draft = { ...blankInstructor(), ...(response.message || {}) };
				frappe.show_alert({ message: __("Instructor saved"), indicator: "green" });
				await this.load(true, this.draft.name);
			} catch (error) { this.saveError = error?.message || "Instructor could not be saved."; }
			finally { this.saving = false; }
		},
		uploadPhoto() {
			if (!this.draft.name || !frappe.ui?.FileUploader) return;
			new frappe.ui.FileUploader({
				doctype: "Instructor", docname: this.draft.name, fieldname: "image", allow_multiple: false, is_private: 1,
				restrictions: { allowed_file_types: ["image/*"], max_file_size: 2 * 1024 * 1024 },
				on_success: async (file) => {
					try {
						const response = await frappe.call("eduedge.api.people_operations.set_instructor_photo", { instructor: this.draft.name, file_url: file.file_url });
						this.draft = { ...this.draft, ...(response.message || {}) };
						frappe.show_alert({ message: __("Instructor photo updated"), indicator: "green" });
					} catch (error) { this.saveError = error?.message || "Instructor photo could not be saved."; }
				},
			});
		},
		openAssignments() {
			const params = new URLSearchParams({ instructor: this.draft.name });
			if (this.draft.eduedge_primary_branch) params.set("branch", this.draft.eduedge_primary_branch);
			window.location.href = `/app/eduedge-instructor-assignments?${params.toString()}`;
		},
		openFullForm() { window.open(`/app/instructor/${encodeURIComponent(this.draft.name)}`, "_blank", "noopener,noreferrer"); },
		previousPage() { this.filters.start = Math.max(0, this.filters.start - this.data.paging.page_length); this.load(); },
		nextPage() { this.filters.start += this.data.paging.page_length; this.load(); },
	},
};
</script>

<style scoped>
.people-filters,.people-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; width:100%; }.people-filters label,.people-grid label { display:grid; gap:.35rem; font-weight:600; }.people-filters .wide,.people-grid .wide { grid-column:1/-1; }.people-layout { display:grid; grid-template-columns:minmax(20rem,.8fr) minmax(0,1.5fr); gap:1rem; margin-top:1rem; }.people-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:12px; background:var(--card-bg); }.people-heading,.actions,.profile-summary { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }.people-heading h2,.people-panel h3 { margin:0; }.people-list,.assignment-list { display:grid; gap:.65rem; }.person-card { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:.75rem; padding:.75rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); text-align:left; }.person-card:hover,.person-card.is-selected { border-color:var(--primary); }.person-card span,.assignment-list article { display:grid; gap:.15rem; }.person-card small,.assignment-list small,.profile-summary small,.people-grid small,.identity-readiness small { color:var(--text-muted); }.status-stack { display:grid; justify-items:end; gap:.3rem; }.identity-readiness { display:grid; gap:.45rem; padding:.8rem 1rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.identity-readiness > div { display:grid; gap:.2rem; }.identity-readiness.is-danger { border-color:var(--red-500,#d92d20); }.identity-readiness.is-warning { border-color:var(--orange-400,#f79009); }.identity-readiness.is-success { border-color:var(--green-500,#12b76a); }.identity-meta { grid-template-columns:repeat(2,minmax(0,1fr)); gap:.5rem !important; font-size:.82rem; color:var(--text-muted); }.avatar,.photo { display:grid; place-items:center; overflow:hidden; border-radius:50%; border:1px solid var(--border-color); background:var(--card-bg); font-weight:700; }.avatar { width:2.8rem; height:2.8rem; }.photo { width:7rem; height:7rem; font-size:2rem; }.avatar img,.photo img { width:100%; height:100%; object-fit:cover; }.profile-summary { justify-content:flex-start; padding:1rem; border-radius:8px; background:var(--control-bg); }.profile-summary > div:nth-child(2) { display:grid; gap:.25rem; flex:1; }.assignment-list article { padding:.7rem; border:1px solid var(--border-color); border-radius:8px; background:var(--control-bg); }.paging { display:flex; justify-content:space-between; align-items:center; }.people-error { color:var(--red-600,#b42318); } @media (max-width:1000px) { .people-layout { grid-template-columns:1fr; } } @media (max-width:680px) { .people-filters,.people-grid,.identity-meta { grid-template-columns:1fr; }.people-filters .wide,.people-grid .wide { grid-column:auto; }.person-card { grid-template-columns:auto 1fr; }.person-card > :last-child { grid-column:1/-1; }.status-stack { justify-items:start; } }
</style>