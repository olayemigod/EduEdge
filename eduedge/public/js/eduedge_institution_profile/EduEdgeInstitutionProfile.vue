<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || institution.institution_name || ''"
		:branch-name="activeContext.branch_name || 'Institution Profile'"
		:menu-items="menuItems"
		active-route="/app/eduedge-institution-profile"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Administration"
					title="Institution Profile"
					subtitle="Maintain the Institution identity used by EdgeSuite headers, report cards, and approved communication services."
				/>
			</template>

			<EdgeFilterBar title="Institution">
				<label class="eduedge-institution-filter">
					<span>Institution</span>
					<select v-model="selectedInstitution" class="form-control" @change="load">
						<option value="">Select Institution</option>
						<option v-for="row in allowedInstitutions" :key="row.name" :value="row.name">
							{{ row.institution_name || row.name }} · {{ row.institution_type || row.company }}
						</option>
					</select>
				</label>
			</EdgeFilterBar>

			<EdgeLoadingState v-if="loading && !loaded" message="Loading Institution profile..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error && !loaded"
				title="Institution profile could not load"
				:message="error"
				action-label="Try again"
				@retry="load"
			/>
			<EdgeEmptyState
				v-else-if="!selectedInstitution"
				title="Select an Institution"
				description="Choose one of your permitted Institutions to view its identity and contact profile."
			/>
			<div v-else class="eduedge-institution-profile-layout">
				<section class="eduedge-institution-card eduedge-institution-preview">
					<div class="eduedge-institution-logo">
						<img v-if="branding.logo" :src="branding.logo" :alt="institution.institution_name || 'Institution logo'" />
						<span v-else>EDU</span>
					</div>
					<h2>{{ institution.official_name || institution.institution_name }}</h2>
					<p v-if="institution.motto">{{ institution.motto }}</p>
					<EdgeStatusBadge
						:label="institution.enabled ? 'Enabled' : 'Disabled'"
						:status="institution.enabled ? 'enabled' : 'disabled'"
						:tone="institution.enabled ? 'success' : 'danger'"
					/>
					<div v-if="canWrite" class="eduedge-institution-actions">
						<button type="button" class="edge-button edge-button--primary" @click="uploadLogo">Upload logo</button>
						<button v-if="institution.logo" type="button" class="edge-button" @click="removeLogo">Remove logo</button>
					</div>
					<div class="eduedge-institution-contact-preview">
						<span><small>Institution code</small><strong>{{ institution.institution_code }}</strong></span>
						<span><small>Company</small><strong>{{ institution.company }}</strong></span>
						<span><small>Institution type</small><strong>{{ institution.institution_type }}</strong></span>
						<span><small>Report address</small><strong>{{ branding.formatted_address || "Not configured" }}</strong></span>
						<span><small>Email</small><strong>{{ branding.email || "Not configured" }}</strong></span>
						<span><small>Phone</small><strong>{{ branding.phone || "Not configured" }}</strong></span>
					</div>
				</section>

				<section class="eduedge-institution-card">
					<div class="eduedge-institution-heading">
						<div>
							<p class="edge-eyebrow">Identity and communication</p>
							<h2>Institution details</h2>
						</div>
						<button
							type="button"
							class="edge-button edge-button--primary"
							:disabled="!canWrite || saving"
							@click="saveProfile"
						>
							{{ saving ? "Saving..." : "Save Institution profile" }}
						</button>
					</div>

					<EdgeEmptyState
						v-if="!canWrite"
						title="Read-only Institution"
						description="Your current role can view this profile but cannot update the Institution."
					/>

					<div class="eduedge-institution-grid">
						<label><span>Institution name</span><input v-model.trim="institution.institution_name" class="form-control" :disabled="!canWrite" /></label>
						<label><span>Official / registered name</span><input v-model.trim="institution.official_name" class="form-control" :disabled="!canWrite" /></label>
						<label><span>Short name</span><input v-model.trim="institution.short_name" class="form-control" :disabled="!canWrite" /></label>
						<label><span>Motto</span><input v-model.trim="institution.motto" class="form-control" :disabled="!canWrite" /></label>
						<label><span>Phone</span><input v-model.trim="institution.phone" class="form-control" :disabled="!canWrite" /></label>
						<label><span>WhatsApp number</span><input v-model.trim="institution.whatsapp_number" class="form-control" :disabled="!canWrite" /></label>
						<label><span>Email</span><input v-model.trim="institution.email" type="email" class="form-control" :disabled="!canWrite" /></label>
						<label><span>Website</span><input v-model.trim="institution.website" class="form-control" :disabled="!canWrite" /></label>
						<label class="eduedge-institution-wide">
							<span>Institution-specific Letter Head</span>
							<input
								v-model.trim="institution.report_card_letter_head"
								list="eduedge-institution-letter-heads"
								class="form-control"
								:disabled="!canWrite"
								placeholder="Optional Letter Head"
								@input="queueLetterHeadSearch(institution.report_card_letter_head)"
							/>
							<small>When blank, report cards use the Institution logo and contact profile before falling back to the global EduEdge report-card setting.</small>
						</label>
						<datalist id="eduedge-institution-letter-heads">
							<option v-for="letterHead in letterHeads" :key="letterHead.value" :value="letterHead.value">{{ letterHead.label }}</option>
						</datalist>
						<label class="eduedge-institution-wide">
							<span>Report and communication footer</span>
							<textarea v-model.trim="institution.report_footer" class="form-control" rows="3" :disabled="!canWrite"></textarea>
						</label>
					</div>
					<p v-if="profileError" class="eduedge-institution-error">{{ profileError }}</p>
				</section>

				<section class="eduedge-institution-card eduedge-institution-address">
					<div class="eduedge-institution-heading">
						<div>
							<p class="edge-eyebrow">Official contact location</p>
							<h2>Institution address</h2>
						</div>
						<div class="eduedge-institution-actions">
							<button
								v-if="canManageAddress"
								type="button"
								class="edge-button edge-button--primary"
								:disabled="savingAddress"
								@click="saveAddress"
							>
								{{ savingAddress ? "Saving..." : "Save address" }}
							</button>
							<button v-if="address.name" type="button" class="edge-button" @click="openAddress">Open full Address</button>
						</div>
					</div>
					<EdgeEmptyState
						v-if="!canManageAddress"
						title="Address editing is restricted"
						description="The linked Address remains readable here. A user with Address create/write permission must maintain it."
					/>
					<div class="eduedge-institution-grid">
						<label><span>Address title</span><input v-model.trim="address.address_title" class="form-control" :disabled="!canManageAddress" /></label>
						<label>
							<span>Address type</span>
							<select v-model="address.address_type" class="form-control" :disabled="!canManageAddress">
								<option>Office</option><option>Billing</option><option>Shipping</option><option>Personal</option><option>Plant</option><option>Postal</option><option>Shop</option><option>Subsidiary</option><option>Warehouse</option><option>Current</option><option>Permanent</option><option>Other</option>
							</select>
						</label>
						<label class="eduedge-institution-wide"><span>Address line 1</span><input v-model.trim="address.address_line1" class="form-control" :disabled="!canManageAddress" /></label>
						<label class="eduedge-institution-wide"><span>Address line 2</span><input v-model.trim="address.address_line2" class="form-control" :disabled="!canManageAddress" /></label>
						<label><span>City / town</span><input v-model.trim="address.city" class="form-control" :disabled="!canManageAddress" /></label>
						<label><span>County / LGA</span><input v-model.trim="address.county" class="form-control" :disabled="!canManageAddress" /></label>
						<label><span>State / province</span><input v-model.trim="address.state" class="form-control" :disabled="!canManageAddress" /></label>
						<label>
							<span>Country</span>
							<input
								v-model.trim="address.country"
								list="eduedge-institution-countries"
								class="form-control"
								:disabled="!canManageAddress"
								@input="queueCountrySearch(address.country)"
							/>
						</label>
						<label><span>Postal code</span><input v-model.trim="address.pincode" class="form-control" :disabled="!canManageAddress" /></label>
						<label><span>Address phone</span><input v-model.trim="address.phone" class="form-control" :disabled="!canManageAddress" /></label>
						<label><span>Address email</span><input v-model.trim="address.email_id" type="email" class="form-control" :disabled="!canManageAddress" /></label>
					</div>
					<datalist id="eduedge-institution-countries">
						<option v-for="country in countries" :key="country.value" :value="country.value">{{ country.label }}</option>
					</datalist>
					<p v-if="addressError" class="eduedge-institution-error">{{ addressError }}</p>
				</section>

				<section class="eduedge-institution-card eduedge-institution-governance">
					<p class="edge-eyebrow">Governance identity</p>
					<h2>Registration and accreditation</h2>
					<div class="eduedge-institution-contact-preview">
						<span><small>Regulatory authority</small><strong>{{ institution.regulatory_authority || "Not configured" }}</strong></span>
						<span><small>Registration number</small><strong>{{ institution.registration_number || "Not configured" }}</strong></span>
						<span><small>Accreditation status</small><strong>{{ institution.accreditation_status || "Not set" }}</strong></span>
					</div>
					<button type="button" class="edge-button" @click="openFullInstitution">Open full Institution form</button>
				</section>
			</div>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const blankInstitution = () => ({
	name: "", institution_name: "", institution_code: "", official_name: "", short_name: "",
	company: "", institution_type: "", logo: "", motto: "", address: "", phone: "",
	whatsapp_number: "", email: "", website: "", report_card_letter_head: "", report_footer: "",
	registration_number: "", regulatory_authority: "", accreditation_status: "", enabled: 1,
});
const blankAddress = () => ({
	name: "", address_title: "", address_type: "Office", address_line1: "", address_line2: "",
	city: "", county: "", state: "", country: "", pincode: "", phone: "", email_id: "",
});

export default {
	name: "EduEdgeInstitutionProfile",
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
			selectedInstitution: "",
			loading: true,
			loaded: false,
			saving: false,
			savingAddress: false,
			error: "",
			profileError: "",
			addressError: "",
			countryTimer: null,
			letterHeadTimer: null,
			countries: [],
			letterHeads: [],
			data: {
				institution: blankInstitution(),
				address: blankAddress(),
				branding: {},
				allowed_institutions: [],
				active_context: {},
				permissions: { can_write: false, can_manage_address: false },
			},
		};
	},
	computed: {
		institution() { return this.data.institution || blankInstitution(); },
		address() { return this.data.address || blankAddress(); },
		branding() { return this.data.branding || {}; },
		allowedInstitutions() { return this.data.allowed_institutions || []; },
		activeContext() { return this.data.active_context || {}; },
		canWrite() { return Boolean(this.data.permissions?.can_write); },
		canManageAddress() { return Boolean(this.canWrite && this.data.permissions?.can_manage_address); },
	},
	mounted() {
		this.load();
		this.loadCountries("");
		this.loadLetterHeads("");
	},
	beforeUnmount() {
		if (this.countryTimer) window.clearTimeout(this.countryTimer);
		if (this.letterHeadTimer) window.clearTimeout(this.letterHeadTimer);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.profiles.get_institution_profile", {
					institution: this.selectedInstitution || undefined,
				});
				this.data = response.message || this.data;
				this.selectedInstitution = this.data.institution?.name || this.selectedInstitution;
				this.data.address = { ...blankAddress(), ...(this.data.address || {}) };
				this.loaded = true;
			} catch (error) {
				this.error = error?.message || "Institution profile could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async saveProfile() {
			if (!this.canWrite) return;
			this.saving = true;
			this.profileError = "";
			try {
				const response = await frappe.call("eduedge.api.profiles.save_institution_profile", {
					institution: this.selectedInstitution,
					profile: JSON.stringify(this.institution),
				});
				this.data = response.message || this.data;
				this.data.address = { ...blankAddress(), ...(this.data.address || {}) };
				await frappe.eduedge?.syncInstitutionContext?.({ force: true });
				frappe.show_alert({ message: __("Institution profile updated"), indicator: "green" });
			} catch (error) {
				this.profileError = error?.message || "Institution profile could not be saved.";
			} finally {
				this.saving = false;
			}
		},
		async saveAddress() {
			if (!this.canManageAddress) return;
			this.savingAddress = true;
			this.addressError = "";
			try {
				const response = await frappe.call("eduedge.api.profiles.save_institution_address", {
					institution: this.selectedInstitution,
					address: JSON.stringify(this.address),
				});
				this.data = response.message || this.data;
				this.data.address = { ...blankAddress(), ...(this.data.address || {}) };
				await frappe.eduedge?.syncInstitutionContext?.({ force: true });
				frappe.show_alert({ message: __("Institution address updated"), indicator: "green" });
			} catch (error) {
				this.addressError = error?.message || "Institution address could not be saved.";
			} finally {
				this.savingAddress = false;
			}
		},
		uploadLogo() {
			if (!this.canWrite || !frappe.ui?.FileUploader) return;
			new frappe.ui.FileUploader({
				doctype: "EduEdge Institution",
				docname: this.selectedInstitution,
				fieldname: "logo",
				allow_multiple: false,
				is_private: 0,
				restrictions: { allowed_file_types: ["image/*"], max_file_size: 2 * 1024 * 1024 },
				on_success: async (file) => {
					try {
						const response = await frappe.call("eduedge.api.profiles.set_institution_logo", {
							institution: this.selectedInstitution,
							file_url: file.file_url,
						});
						this.data = response.message || this.data;
						this.data.address = { ...blankAddress(), ...(this.data.address || {}) };
						await frappe.eduedge?.syncInstitutionContext?.({ force: true });
						frappe.show_alert({ message: __("Institution logo updated"), indicator: "green" });
					} catch (error) {
						this.profileError = error?.message || "Institution logo could not be updated.";
					}
				},
			});
		},
		async removeLogo() {
			try {
				const response = await frappe.call("eduedge.api.profiles.set_institution_logo", {
					institution: this.selectedInstitution,
					file_url: "",
				});
				this.data = response.message || this.data;
				this.data.address = { ...blankAddress(), ...(this.data.address || {}) };
				await frappe.eduedge?.syncInstitutionContext?.({ force: true });
			} catch (error) {
				this.profileError = error?.message || "Institution logo could not be removed.";
			}
		},
		openAddress() {
			if (this.address.name) frappe.set_route("Form", "Address", this.address.name);
		},
		openFullInstitution() {
			if (this.selectedInstitution) frappe.set_route("Form", "EduEdge Institution", this.selectedInstitution);
		},
		queueCountrySearch(value) {
			if (this.countryTimer) window.clearTimeout(this.countryTimer);
			if (this.letterHeadTimer) window.clearTimeout(this.letterHeadTimer);
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
		queueLetterHeadSearch(value) {
			if (this.letterHeadTimer) window.clearTimeout(this.letterHeadTimer);
			this.letterHeadTimer = window.setTimeout(() => this.loadLetterHeads(value), 250);
		},
		async loadLetterHeads(value) {
			try {
				const response = await frappe.call("eduedge.api.profiles.search_letter_heads", { txt: value || "" });
				this.letterHeads = response.message || [];
			} catch (_error) {
				this.letterHeads = [];
			}
		},
	},
};
</script>

<style scoped>
.eduedge-institution-filter { display:grid; gap:.35rem; min-width:min(28rem,100%); font-weight:600; }
.eduedge-institution-profile-layout { display:grid; grid-template-columns:minmax(15rem,.65fr) minmax(0,1.45fr); gap:1rem; margin-top:1rem; }
.eduedge-institution-card { display:grid; gap:1rem; align-content:start; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-institution-preview { text-align:center; }
.eduedge-institution-logo { width:9rem; height:9rem; display:grid; place-items:center; margin:auto; overflow:hidden; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--control-bg); font-weight:700; font-size:1.5rem; }
.eduedge-institution-logo img { width:100%; height:100%; object-fit:contain; }
.eduedge-institution-heading,.eduedge-institution-actions { display:flex; gap:.5rem; flex-wrap:wrap; align-items:center; }
.eduedge-institution-heading { justify-content:space-between; }
.eduedge-institution-heading h2,.eduedge-institution-card h2 { margin:0; }
.eduedge-institution-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }
.eduedge-institution-grid label { display:grid; gap:.35rem; font-weight:600; }
.eduedge-institution-grid small { color:var(--text-muted); }
.eduedge-institution-wide { grid-column:1/-1; }
.eduedge-institution-contact-preview { display:grid; gap:.6rem; }
.eduedge-institution-contact-preview span { display:grid; gap:.15rem; padding:.7rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); text-align:left; }
.eduedge-institution-contact-preview small { color:var(--text-muted); }
.eduedge-institution-address,.eduedge-institution-governance { grid-column:1/-1; }
.eduedge-institution-error { color:var(--red-600,#b42318); margin:0; }
@media (max-width:900px) { .eduedge-institution-profile-layout { grid-template-columns:1fr; } .eduedge-institution-address,.eduedge-institution-governance { grid-column:auto; } }
@media (max-width:650px) { .eduedge-institution-grid { grid-template-columns:1fr; } .eduedge-institution-wide { grid-column:auto; } .eduedge-institution-heading { align-items:stretch; flex-direction:column; } }
</style>
