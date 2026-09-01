<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || 'My Profile'"
		:user-name="profile.full_name || profile.email || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-my-profile"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Account"
					title="My Profile"
					subtitle="Keep your EduEdge contact details current. Login email, roles, and official HR records remain separately governed."
				/>
			</template>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading your profile..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !loaded"
				title="Profile could not load"
				:message="error"
				action-label="Try again"
				@retry="load"
			/>
			<div v-else class="eduedge-profile-layout">
				<section class="eduedge-profile-panel eduedge-profile-summary">
					<div class="eduedge-profile-photo">
						<img v-if="profile.user_image" :src="profile.user_image" :alt="profile.full_name || 'Profile photo'" />
						<span v-else>{{ initials }}</span>
					</div>
					<h2>{{ profile.full_name || profile.email }}</h2>
					<p>{{ educationProfile.professional_title || primaryEmployment.designation || "EduEdge User" }}</p>
					<EdgeStatusBadge
						:label="`${data.completeness.percent || 0}% complete`"
						status="profile"
						:tone="data.completeness.percent >= 80 ? 'success' : 'warning'"
					/>
					<div v-if="canEdit" class="eduedge-profile-actions">
						<button type="button" class="edge-button edge-button--primary" @click="uploadPhoto">
							Upload passport photo
						</button>
						<button
							v-if="profile.user_image"
							type="button"
							class="edge-button"
							:disabled="savingPhoto"
							@click="removePhoto"
						>
							Remove photo
						</button>
					</div>
					<small v-if="canEdit" class="text-muted">Your account photo is uploaded as a private file and is shown only through authenticated EduEdge access.</small>
					<div class="eduedge-profile-readonly">
						<span><small>Login email</small><strong>{{ profile.email }}</strong></span>
						<span><small>Active Institution</small><strong>{{ activeContext.institution_name || "Not selected" }}</strong></span>
						<span><small>Active Branch</small><strong>{{ activeContext.branch_name || "Not selected" }}</strong></span>
					</div>
				</section>

				<section class="eduedge-profile-panel">
					<div class="eduedge-profile-heading">
						<div>
							<p class="edge-eyebrow">Personal and contact information</p>
							<h2>Profile details</h2>
						</div>
						<button
							type="button"
							class="edge-button edge-button--primary"
							:disabled="!canEdit || saving"
							@click="save"
						>
							{{ saving ? "Saving..." : "Save profile" }}
						</button>
					</div>

					<EdgeEmptyState
						v-if="!canEdit"
						title="Read-only profile"
						description="Your current account permissions do not allow both User and EduEdge Profile updates. An administrator can correct the account setup."
					/>

					<div class="eduedge-profile-grid">
						<label><span>First name</span><input v-model.trim="profile.first_name" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Middle name</span><input v-model.trim="profile.middle_name" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Last name</span><input v-model.trim="profile.last_name" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Preferred display name</span><input v-model.trim="educationProfile.preferred_name" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Professional title</span><input v-model.trim="educationProfile.professional_title" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Phone</span><input v-model.trim="profile.phone" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Mobile number</span><input v-model.trim="profile.mobile_no" class="form-control" :disabled="!canEdit" /></label>
						<label><span>WhatsApp number</span><input v-model.trim="educationProfile.whatsapp_number" class="form-control" :disabled="!canEdit" /></label>
						<label>
							<span>Preferred communication</span>
							<select v-model="educationProfile.preferred_communication" class="form-control" :disabled="!canEdit">
								<option value="">Not specified</option>
								<option>Email</option><option>SMS</option><option>WhatsApp</option><option>Phone</option>
							</select>
						</label>
						<label><span>Location</span><input v-model.trim="profile.location" class="form-control" :disabled="!canEdit" /></label>
					</div>

					<h3>Contact address</h3>
					<div class="eduedge-profile-grid">
						<label class="eduedge-profile-wide"><span>Address line 1</span><input v-model.trim="educationProfile.address_line_1" class="form-control" :disabled="!canEdit" /></label>
						<label class="eduedge-profile-wide"><span>Address line 2</span><input v-model.trim="educationProfile.address_line_2" class="form-control" :disabled="!canEdit" /></label>
						<label><span>City / town</span><input v-model.trim="educationProfile.city" class="form-control" :disabled="!canEdit" /></label>
						<label><span>State / province</span><input v-model.trim="educationProfile.state" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Postal code</span><input v-model.trim="educationProfile.postal_code" class="form-control" :disabled="!canEdit" /></label>
						<label>
							<span>Country</span>
							<input
								v-model.trim="educationProfile.country"
								list="eduedge-profile-countries"
								class="form-control"
								:disabled="!canEdit"
								@input="queueCountrySearch(educationProfile.country)"
							/>
						</label>
					</div>
					<datalist id="eduedge-profile-countries">
						<option v-for="country in countries" :key="country.value" :value="country.value">{{ country.label }}</option>
					</datalist>

					<h3>Emergency contact</h3>
					<div class="eduedge-profile-grid">
						<label><span>Contact name</span><input v-model.trim="educationProfile.emergency_contact_name" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Relationship</span><input v-model.trim="educationProfile.emergency_contact_relationship" class="form-control" :disabled="!canEdit" /></label>
						<label><span>Contact phone</span><input v-model.trim="educationProfile.emergency_contact_phone" class="form-control" :disabled="!canEdit" /></label>
					</div>

					<label class="eduedge-profile-bio">
						<span>Short professional bio</span>
						<textarea v-model.trim="profile.bio" class="form-control" rows="4" :disabled="!canEdit"></textarea>
					</label>
					<p v-if="saveError" class="eduedge-profile-error">{{ saveError }}</p>
				</section>

				<section class="eduedge-profile-panel eduedge-profile-context">
					<div>
						<p class="edge-eyebrow">Official records</p>
						<h2>Employment and teaching context</h2>
					</div>
					<EdgeEmptyState
						v-if="!data.employees.length && !data.instructors.length"
						title="No linked staff record"
						description="A Teacher should be linked through User → active Employee → active Instructor before timetable and attendance ownership can be applied."
					/>
					<article v-for="employee in data.employees" :key="employee.name" class="eduedge-profile-record">
						<strong>{{ employee.employee_name || employee.name }}</strong>
						<span>{{ employee.designation || "No designation" }} · {{ employee.department || "No department" }}</span>
						<small>{{ employee.company || "" }}</small>
					</article>
					<article v-for="instructor in data.instructors" :key="instructor.name" class="eduedge-profile-record">
						<strong>{{ instructor.instructor_name || instructor.name }}</strong>
						<span>Instructor record · {{ instructor.department || "No department" }}</span>
					</article>

					<h3>Roles</h3>
					<div class="eduedge-profile-chips">
						<EdgeStatusBadge v-for="role in data.roles" :key="role" :label="role" :status="role" tone="neutral" />
					</div>

					<h3>Permitted Institutions and Branches</h3>
					<div class="eduedge-profile-record-list">
						<article v-for="institution in allowedInstitutions" :key="institution.name" class="eduedge-profile-record">
							<strong>{{ institution.institution_name || institution.name }}</strong>
							<small>{{ institution.institution_type || institution.company }}</small>
						</article>
						<article v-for="branch in allowedBranches" :key="branch.name" class="eduedge-profile-record">
							<strong>{{ branch.branch_name || branch.name }}</strong>
							<small>{{ branch.institution_name || branch.company }}</small>
						</article>
					</div>
				</section>
			</div>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankProfile = () => ({
	first_name: "", middle_name: "", last_name: "", full_name: "", email: "", user_image: "",
	phone: "", mobile_no: "", location: "", bio: "",
});
const blankEducationProfile = () => ({
	name: "", user: "", preferred_name: "", professional_title: "", whatsapp_number: "",
	preferred_communication: "", address_line_1: "", address_line_2: "", city: "", state: "",
	postal_code: "", country: "", emergency_contact_name: "", emergency_contact_relationship: "",
	emergency_contact_phone: "",
});

export default {
	name: "EduEdgeMyProfile",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			loading: true,
			loaded: false,
			saving: false,
			savingPhoto: false,
			error: "",
			saveError: "",
			countryTimer: null,
			countries: [],
			data: {
				profile: blankProfile(),
				education_profile: blankEducationProfile(),
				employees: [],
				instructors: [],
				roles: [],
				branch_access: { allowed_institutions: [], allowed_branches: [] },
				active_context: {},
				completeness: { percent: 0 },
				permissions: { can_edit_user: false, can_edit_profile: false },
			},
		};
	},
	computed: {
		profile() { return this.data.profile || blankProfile(); },
		educationProfile() { return this.data.education_profile || blankEducationProfile(); },
		activeContext() { return this.data.active_context || {}; },
		canEdit() { return Boolean(this.data.permissions?.can_edit_user && this.data.permissions?.can_edit_profile); },
		allowedInstitutions() { return this.data.branch_access?.allowed_institutions || []; },
		allowedBranches() { return this.data.branch_access?.allowed_branches || []; },
		primaryEmployment() { return this.data.employees?.[0] || {}; },
		initials() {
			const parts = [this.profile.first_name, this.profile.last_name].filter(Boolean);
			return (parts.map((part) => part[0]).join("") || "U").toUpperCase();
		},
	},
	mounted() {
		this.load();
		this.loadCountries("");
	},
	beforeUnmount() {
		if (this.countryTimer) window.clearTimeout(this.countryTimer);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.profiles.get_my_profile");
				this.data = response.message || this.data;
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Your profile could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async save() {
			if (!this.canEdit || !this.profile.first_name) return;
			this.saving = true;
			this.saveError = "";
			try {
				const response = await frappe.call("eduedge.api.profiles.save_my_profile", {
					profile: JSON.stringify({ user: this.profile, education_profile: this.educationProfile }),
				});
				this.data = response.message || this.data;
				frappe.show_alert({ message: __("Profile updated"), indicator: "green" });
			} catch (error) {
				this.saveError = error?.message || "Profile could not be saved.";
			} finally {
				this.saving = false;
			}
		},
		uploadPhoto() {
			if (!this.canEdit || !frappe.ui?.FileUploader) return;
			new frappe.ui.FileUploader({
				doctype: "User",
				docname: frappe.session.user,
				fieldname: "user_image",
				allow_multiple: false,
				is_private: 1,
				restrictions: { allowed_file_types: ["image/*"], max_file_size: 2 * 1024 * 1024 },
				on_success: async (file) => {
					this.savingPhoto = true;
					try {
						const response = await frappe.call("eduedge.api.profiles.set_my_profile_photo", {
							file_url: file.file_url,
						});
						this.data = response.message || this.data;
						frappe.show_alert({ message: __("Profile photo updated"), indicator: "green" });
					} catch (error) {
						this.saveError = error?.message || "Profile photo could not be updated.";
					} finally {
						this.savingPhoto = false;
					}
				},
			});
		},
		async removePhoto() {
			this.savingPhoto = true;
			try {
				const response = await frappe.call("eduedge.api.profiles.set_my_profile_photo", { file_url: "" });
				this.data = response.message || this.data;
			} catch (error) {
				this.saveError = error?.message || "Profile photo could not be removed.";
			} finally {
				this.savingPhoto = false;
			}
		},
		queueCountrySearch(value) {
			if (this.countryTimer) window.clearTimeout(this.countryTimer);
			this.countryTimer = window.setTimeout(() => this.loadCountries(value), 250);
		},
		async loadCountries(value) {
			try {
				const response = await frappe.call("eduedge.api.profiles.search_countries", { txt: value || "" });
				this.countries = response.message || [];
			} catch (_error) {
				this.countries = [];
			}
		},
	},
};
</script>

<style scoped>
.eduedge-profile-layout { display:grid; grid-template-columns:minmax(15rem,.65fr) minmax(0,1.5fr); gap:1rem; }
.eduedge-profile-panel { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-profile-summary { text-align:center; }
.eduedge-profile-photo { width:8rem; height:8rem; margin:auto; border-radius:50%; overflow:hidden; display:grid; place-items:center; background:var(--control-bg); border:1px solid var(--border-color); font-size:2.5rem; font-weight:700; }
.eduedge-profile-photo img { width:100%; height:100%; object-fit:cover; }
.eduedge-profile-actions,.eduedge-profile-heading,.eduedge-profile-chips { display:flex; gap:.5rem; flex-wrap:wrap; align-items:center; }
.eduedge-profile-heading { justify-content:space-between; }
.eduedge-profile-heading h2,.eduedge-profile-summary h2,.eduedge-profile-context h2,.eduedge-profile-panel h3 { margin:0; }
.eduedge-profile-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }
.eduedge-profile-grid label,.eduedge-profile-bio { display:grid; gap:.35rem; font-weight:600; }
.eduedge-profile-wide { grid-column:1/-1; }
.eduedge-profile-readonly,.eduedge-profile-record-list { display:grid; gap:.6rem; }
.eduedge-profile-readonly span,.eduedge-profile-record { display:grid; gap:.15rem; padding:.7rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); text-align:left; }
.eduedge-profile-readonly small,.eduedge-profile-record small,.eduedge-profile-record span { color:var(--text-muted); }
.eduedge-profile-error { color:var(--red-600,#b42318); margin:0; }
.eduedge-profile-context { grid-column:1/-1; }
@media (max-width:900px) { .eduedge-profile-layout { grid-template-columns:1fr; } .eduedge-profile-context { grid-column:auto; } }
@media (max-width:650px) { .eduedge-profile-grid { grid-template-columns:1fr; } .eduedge-profile-wide { grid-column:auto; } .eduedge-profile-heading { align-items:stretch; flex-direction:column; } }
</style>
