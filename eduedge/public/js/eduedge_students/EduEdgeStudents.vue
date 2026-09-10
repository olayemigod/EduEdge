<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="data.selected_branch?.institution_name || ''"
		:branch-name="data.selected_branch?.branch_name || studentPlural"
		:menu-items="menuItems"
		active-route="/app/eduedge-students"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="People Operations"
					:title="studentPlural"
					:subtitle="`Maintain official ${studentPlural.toLowerCase()} profiles, approved photographs, guardians and academic context.`"
					:action-label="canCreate ? `Add ${studentSingular}` : ''"
					@action="newStudent"
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" :message="`Loading ${studentPlural.toLowerCase()}...`" :skeleton="true" />
			<EdgeErrorState v-else-if="error && !loaded" title="Students could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<EdgeFilterBar :title="`${studentSingular} filters`">
					<div class="eduedge-people-filters">
						<label><span>Branch / Campus</span><select v-model="filters.branch" class="form-control" @change="branchChanged"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
						<label><span>Search</span><input v-model.trim="filters.search" class="form-control" placeholder="Name, ID, email or mobile" @keyup.enter="load(true)" /></label>
					</div>
					<template #actions><button type="button" class="edge-button edge-button--primary" :disabled="loading" @click="load(true)">Apply</button></template>
				</EdgeFilterBar>

				<p v-if="error" class="eduedge-people-error">{{ error }}</p>
				<section class="eduedge-people-layout">
					<article class="eduedge-people-panel">
						<div class="eduedge-people-heading"><div><p class="edge-eyebrow">Student register</p><h2>{{ studentPlural }}</h2></div><button v-if="canCreate" type="button" class="edge-button" @click="newStudent">Add {{ studentSingular }}</button></div>
						<EdgeLoadingState v-if="loading" message="Refreshing students..." />
						<EdgeEmptyState v-else-if="!data.students.length" :title="`No ${studentPlural.toLowerCase()} found`" :description="canCreate ? `Add the first ${studentSingular.toLowerCase()} or approve an admission application.` : 'Change the filter or contact an administrator.'" />
						<div v-else class="eduedge-people-list">
							<button v-for="row in data.students" :key="row.name" type="button" class="eduedge-person-card" :class="{ 'is-selected': draft.name === row.name }" @click="editStudent(row.name)">
								<div class="eduedge-avatar"><img v-if="row.image" :src="row.image" :alt="row.student_name" /><span v-else>{{ initials(row.student_name) }}</span></div>
								<span><strong>{{ row.student_name || row.name }}</strong><small>{{ row.name }} · {{ row.student_mobile_number || row.student_email_id || 'No contact' }}</small></span>
								<EdgeStatusBadge :label="row.eduedge_photo_status || 'Pending Review'" :status="row.eduedge_photo_status || 'pending'" :tone="row.eduedge_photo_status === 'Approved' ? 'success' : row.eduedge_photo_status === 'Rejected' ? 'danger' : 'warning'" />
							</button>
						</div>
						<div class="eduedge-people-paging"><button type="button" class="edge-button" :disabled="loading || data.paging.start <= 0" @click="previousPage">Previous</button><span>{{ data.paging.start + (data.students.length ? 1 : 0) }}–{{ data.paging.start + data.students.length }}</span><button type="button" class="edge-button" :disabled="loading || !data.paging.has_more" @click="nextPage">Next</button></div>
					</article>

					<article class="eduedge-people-panel eduedge-person-editor">
						<div class="eduedge-people-heading">
							<div><p class="edge-eyebrow">Official student record</p><h2>{{ draft.name ? draft.student_name || draft.name : `New ${studentSingular}` }}</h2></div>
							<div class="eduedge-people-actions">
								<button v-if="draft.name && canReadEnrollments" type="button" class="edge-button" @click="openEnrollments(false)">View Enrollments</button>
								<button v-if="draft.name && canEnroll" type="button" class="edge-button" @click="openEnrollments(true)">Enroll Student</button>
								<button v-if="draft.name" type="button" class="edge-button" @click="openFullForm">Open full form</button>
								<button type="button" class="edge-button edge-button--primary" :disabled="saving || !canSave" @click="save">{{ saving ? 'Saving...' : 'Save student' }}</button>
							</div>
						</div>

						<div class="eduedge-profile-summary">
							<div class="eduedge-profile-photo"><img v-if="draft.image" :src="draft.image" :alt="draft.student_name || 'Student photo'" /><span v-else>{{ initials(draft.student_name || draft.first_name) }}</span></div>
							<div><strong>Official photograph</strong><small>Used on assessment sheets, report cards and identity documents after approval.</small><EdgeStatusBadge :label="draft.eduedge_photo_status || 'Pending Review'" :status="draft.eduedge_photo_status || 'pending'" :tone="draft.eduedge_photo_status === 'Approved' ? 'success' : draft.eduedge_photo_status === 'Rejected' ? 'danger' : 'warning'" /></div>
							<div v-if="canManagePhoto && draft.name" class="eduedge-people-actions"><button type="button" class="edge-button" @click="uploadPhoto">Upload / replace</button><button v-if="draft.image && draft.eduedge_photo_status !== 'Approved'" type="button" class="edge-button edge-button--primary" @click="reviewPhoto('Approved')">Approve</button><button v-if="draft.image && draft.eduedge_photo_status !== 'Rejected'" type="button" class="edge-button" @click="reviewPhoto('Rejected')">Reject</button></div>
							<small v-else-if="!draft.name">Save the Student before uploading the official photograph.</small>
						</div>

						<h3>Identity and contact</h3>
						<div class="eduedge-people-grid">
							<label><span>First name *</span><input v-model.trim="draft.first_name" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Middle name</span><input v-model.trim="draft.middle_name" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Last name</span><input v-model.trim="draft.last_name" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Branch / Campus *</span><select v-model="draft.eduedge_school_branch" class="form-control" :disabled="!canEdit"><option v-for="row in data.allowed_branches" :key="row.name" :value="row.name">{{ row.branch_name || row.name }}</option></select></label>
							<label><span>Joining date</span><input v-model="draft.joining_date" type="date" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Enabled</span><select v-model.number="draft.enabled" class="form-control" :disabled="!canEdit"><option :value="1">Enabled</option><option :value="0">Disabled</option></select></label>
							<label><span>Student email *</span><input v-model.trim="draft.student_email_id" type="email" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Mobile number</span><input v-model.trim="draft.student_mobile_number" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Date of birth</span><input v-model="draft.date_of_birth" type="date" class="form-control" :disabled="!canEdit" /></label>
							<label><span>Gender</span><select v-model="draft.gender" class="form-control" :disabled="!canEdit"><option value="">Not specified</option><option v-for="row in data.options.genders" :key="row.name" :value="row.name">{{ row.name }}</option></select></label>
							<label><span>Blood group</span><select v-model="draft.blood_group" class="form-control" :disabled="!canEdit"><option v-for="value in data.options.blood_groups" :key="value" :value="value">{{ value || 'Not specified' }}</option></select></label>
							<label><span>Nationality</span><input v-model.trim="draft.nationality" class="form-control" :disabled="!canEdit" /></label>
						</div>

						<h3>Address</h3>
						<div class="eduedge-people-grid"><label class="wide"><span>Address line 1</span><input v-model.trim="draft.address_line_1" class="form-control" :disabled="!canEdit" /></label><label class="wide"><span>Address line 2</span><input v-model.trim="draft.address_line_2" class="form-control" :disabled="!canEdit" /></label><label><span>City / Town</span><input v-model.trim="draft.city" class="form-control" :disabled="!canEdit" /></label><label><span>State</span><input v-model.trim="draft.state" class="form-control" :disabled="!canEdit" /></label><label><span>Postal code</span><input v-model.trim="draft.pincode" class="form-control" :disabled="!canEdit" /></label><label><span>Country</span><select v-model="draft.country" class="form-control" :disabled="!canEdit"><option value="">Not specified</option><option v-for="row in data.options.countries" :key="row.name" :value="row.name">{{ row.name }}</option></select></label></div>

						<div class="eduedge-people-heading"><h3>Parents and guardians</h3><button type="button" class="edge-button" :disabled="!canEdit" @click="addGuardian">Add guardian</button></div>
						<EdgeEmptyState v-if="!draft.guardians.length" title="No guardian linked" description="Link at least one parent or guardian where applicable." />
						<div v-else class="eduedge-roster-list"><div v-for="(row,index) in draft.guardians" :key="`${row.guardian}-${index}`" class="eduedge-roster-row"><select v-model="row.guardian" class="form-control" :disabled="!canEdit"><option value="">Select guardian</option><option v-for="guardian in data.guardians" :key="guardian.name" :value="guardian.name">{{ guardian.guardian_name || guardian.name }}</option></select><select v-model="row.relation" class="form-control" :disabled="!canEdit"><option value="">Relationship</option><option>Mother</option><option>Father</option><option>Others</option></select><button type="button" class="edge-button" :disabled="!canEdit" @click="removeGuardian(index)">Remove</button></div></div>

						<template v-if="draft.name">
							<div class="eduedge-people-heading"><h3>Academic context</h3><button v-if="canReadEnrollments" type="button" class="edge-button" @click="openEnrollments(false)">View all Enrollments</button></div>
							<div class="eduedge-context-columns"><section><strong>Submitted enrolments</strong><p v-if="!draft.enrollments?.length" class="text-muted">No submitted enrolment.</p><article v-for="row in draft.enrollments || []" :key="row.name"><span>{{ row.program }} · {{ row.academic_year }}</span><small>{{ row.academic_term || 'Session-wide' }} · {{ row.eduedge_program_offering || row.name }}</small></article></section><section><strong>Active Class Arms</strong><p v-if="!draft.class_arms?.length" class="text-muted">Not assigned to a Class Arm.</p><article v-for="row in draft.class_arms || []" :key="row.name"><span>{{ row.eduedge_display_name || row.student_group_name || row.name }}</span><small>{{ row.program || '' }} · Roll {{ row.group_roll_number || '—' }}</small></article></section></div>
						</template>
						<p v-if="saveError" class="eduedge-people-error">{{ saveError }}</p>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankStudent = (branch = "") => ({ name: "", student_name: "", enabled: 1, first_name: "", middle_name: "", last_name: "", eduedge_school_branch: branch, joining_date: frappe.datetime?.get_today?.() || "", student_email_id: "", student_mobile_number: "", date_of_birth: "", blood_group: "", gender: "", nationality: "", address_line_1: "", address_line_2: "", city: "", state: "", pincode: "", country: "", image: "", eduedge_photo_status: "Pending Review", eduedge_photo_locked: 0, guardians: [], enrollments: [], class_arms: [] });
const blankData = () => ({ allowed_branches: [], selected_branch: {}, students: [], student: null, guardians: [], options: { genders: [], countries: [], blood_groups: [] }, permissions: {}, paging: { start: 0, page_length: 25, has_more: false } });

export default {
	name: "EduEdgeStudents",
	data() { return { menuItems: EDUEDGE_MENU_ITEMS, loading: true, loaded: false, saving: false, error: "", saveError: "", filters: { branch: "", search: "", start: 0 }, data: blankData(), draft: blankStudent() }; },
	computed: {
		studentSingular() { return frappe.eduedge?.term?.("student", { fallback: __("Student") }) || __("Student"); },
		studentPlural() { return frappe.eduedge?.term?.("student", { plural: true, fallback: __("Students") }) || __("Students"); },
		canCreate() { return Boolean(this.data.permissions?.can_create); },
		canEdit() { return this.draft.name ? Boolean(this.data.permissions?.can_write) : this.canCreate; },
		canManagePhoto() { return Boolean(this.data.permissions?.can_manage_photo); },
		enrollmentPermissions() { return frappe.boot?.eduedge_access_manifest?.resources?.program_enrollment || {}; },
		canReadEnrollments() { return Boolean(this.enrollmentPermissions.read); },
		canEnroll() { return Boolean(this.enrollmentPermissions.create); },
		canSave() { return Boolean(this.canEdit && this.draft.first_name && this.draft.eduedge_school_branch && this.draft.student_email_id); },
	},
	async mounted() {
		const params = new URLSearchParams(window.location.search || "");
		this.filters.branch = params.get("branch") || "";
		await this.load(false, params.get("student") || "");
	},
	methods: {
		openRoute: openEduEdgeRoute,
		initials(value) { return String(value || "S").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); },
		async load(reset = false, student = "") {
			if (reset) this.filters.start = 0;
			this.loading = true; this.error = "";
			try {
				const response = await frappe.call("eduedge.api.people_operations.get_students_page", { branch: this.filters.branch || undefined, search: this.filters.search || undefined, student: student || undefined, start: this.filters.start, page_length: this.data.paging.page_length || 25 });
				this.data = response.message || blankData(); this.filters.branch = this.data.selected_branch?.name || this.filters.branch; this.loaded = true;
				if (student && this.data.student) this.draft = { ...blankStudent(this.filters.branch), ...this.data.student, guardians: (this.data.student.guardians || []).map((row) => ({ ...row })) };
				else if (!this.draft.name) this.draft.eduedge_school_branch = this.filters.branch;
			} catch (error) { this.error = error?.message || "Students could not be loaded."; }
			finally { this.loading = false; }
		},
		branchChanged() { this.draft = blankStudent(this.filters.branch); this.load(true); },
		newStudent() { this.draft = blankStudent(this.filters.branch); this.saveError = ""; },
		editStudent(name) { this.load(false, name); },
		addGuardian() { this.draft.guardians.push({ guardian: "", relation: "" }); },
		removeGuardian(index) { this.draft.guardians.splice(index, 1); },
		async save() {
			if (!this.canSave) return;
			this.saving = true; this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.people_operations.save_student", { payload: JSON.stringify(this.draft) });
				this.draft = { ...blankStudent(this.filters.branch), ...(response.message || {}), guardians: (response.message?.guardians || []).map((row) => ({ ...row })) };
				frappe.show_alert({ message: __(`${this.studentSingular} saved`), indicator: "green" }); await this.load(true, this.draft.name);
			} catch (error) { this.saveError = error?.message || `${this.studentSingular} could not be saved.`; }
			finally { this.saving = false; }
		},
		uploadPhoto() {
			if (!this.canManagePhoto || !this.draft.name || !frappe.ui?.FileUploader) return;
			new frappe.ui.FileUploader({ doctype: "Student", docname: this.draft.name, fieldname: "image", allow_multiple: false, is_private: 1, restrictions: { allowed_file_types: ["image/*"], max_file_size: 2 * 1024 * 1024 }, on_success: async (file) => { try { const response = await frappe.call("eduedge.api.people_operations.set_student_photo", { reference_doctype: "Student", reference_name: this.draft.name, file_url: file.file_url }); this.draft = { ...this.draft, ...(response.message || {}) }; frappe.show_alert({ message: __("Photo uploaded for review"), indicator: "green" }); } catch (error) { this.saveError = error?.message || "Photo could not be saved."; } } });
		},
		async reviewPhoto(decision) {
			const note = window.prompt(decision === "Approved" ? "Approval note (optional)" : "Reason for rejection") || "";
			try { const response = await frappe.call("eduedge.api.people_operations.review_student_photo", { reference_doctype: "Student", reference_name: this.draft.name, decision, note }); this.draft = { ...this.draft, ...(response.message || {}) }; frappe.show_alert({ message: __(`Photo ${decision.toLowerCase()}`), indicator: decision === "Approved" ? "green" : "orange" }); await this.load(true, this.draft.name); } catch (error) { this.saveError = error?.message || "Photo review could not be completed."; }
		},
		openEnrollments(createMode = false) {
			if (!this.draft.name) return;
			const params = new URLSearchParams({ student: this.draft.name, branch: this.draft.eduedge_school_branch || this.filters.branch });
			if (createMode) params.set("mode", "create");
			window.location.href = `/app/eduedge-student-enrollments?${params.toString()}`;
		},
		openFullForm() { window.open(`/app/student/${encodeURIComponent(this.draft.name)}`, "_blank", "noopener,noreferrer"); },
		previousPage() { this.filters.start = Math.max(0, this.filters.start - this.data.paging.page_length); this.load(); },
		nextPage() { this.filters.start += this.data.paging.page_length; this.load(); },
	},
};
</script>

<style scoped>
.eduedge-people-filters,.eduedge-people-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; width:100%; }
.eduedge-people-filters label,.eduedge-people-grid label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-people-layout { display:grid; grid-template-columns:minmax(18rem,.75fr) minmax(0,1.55fr); gap:1rem; margin-top:1rem; }
.eduedge-people-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-people-heading,.eduedge-people-actions,.eduedge-profile-summary,.eduedge-roster-row { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; }
.eduedge-people-heading h2,.eduedge-people-panel h3 { margin:0; }
.eduedge-people-list,.eduedge-roster-list,.eduedge-context-columns section { display:grid; gap:.65rem; }
.eduedge-person-card { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:.75rem; padding:.75rem; text-align:left; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-person-card:hover,.eduedge-person-card.is-selected { border-color:var(--primary); }
.eduedge-person-card span,.eduedge-context-columns article { display:grid; gap:.15rem; }
.eduedge-person-card small,.eduedge-context-columns small,.eduedge-profile-summary small { color:var(--text-muted); }
.eduedge-avatar,.eduedge-profile-photo { display:grid; place-items:center; overflow:hidden; border-radius:50%; background:var(--card-bg); border:1px solid var(--border-color); font-weight:700; }
.eduedge-avatar { width:2.8rem; height:2.8rem; }.eduedge-profile-photo { width:7rem; height:7rem; font-size:2rem; flex:0 0 auto; }
.eduedge-avatar img,.eduedge-profile-photo img { width:100%; height:100%; object-fit:cover; }
.eduedge-profile-summary { justify-content:flex-start; padding:1rem; border-radius:var(--edge-radius-md,8px); background:var(--control-bg); }
.eduedge-profile-summary > div:nth-child(2) { display:grid; gap:.35rem; flex:1; }
.eduedge-people-grid .wide { grid-column:1/-1; }
.eduedge-roster-row { display:grid; grid-template-columns:minmax(12rem,1fr) minmax(8rem,.6fr) auto; }
.eduedge-context-columns { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }.eduedge-context-columns section { padding:.75rem; border:1px solid var(--border-color); border-radius:8px; }.eduedge-context-columns article { padding:.55rem; background:var(--control-bg); border-radius:6px; }
.eduedge-people-paging { display:flex; justify-content:space-between; align-items:center; }.eduedge-people-error { color:var(--red-600,#b42318); }
@media (max-width:1000px) { .eduedge-people-layout { grid-template-columns:1fr; } }
@media (max-width:680px) { .eduedge-people-filters,.eduedge-people-grid,.eduedge-context-columns { grid-template-columns:1fr; }.eduedge-people-grid .wide { grid-column:auto; }.eduedge-roster-row { grid-template-columns:1fr; }.eduedge-person-card { grid-template-columns:auto 1fr; }.eduedge-person-card > :last-child { grid-column:1/-1; } }
</style>
