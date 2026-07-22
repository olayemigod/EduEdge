<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || 'Academic Foundation'"
		:menu-items="menuItems"
		active-route="/app/eduedge-academic-foundation"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Foundation"
					:title="`${term('academic_section', true, 'Academic Sections')} and ${term('academic_level', true, 'Academic Levels')}`"
					subtitle="Configure institution-owned sections, levels, progression order, and academic calendars without changing Frappe's underlying DocType identities."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading academic foundation..." :skeleton="true" />
			<EdgeErrorState v-else-if="error" title="Academic Foundation could not load" :message="error" action-label="Try again" @retry="load" />
			<template v-else>
				<section class="eduedge-foundation-context">
					<label>
						<span>Institution</span>
						<select v-model="selectedInstitution" class="form-control" @change="resetDrafts">
							<option value="">Select Institution</option>
							<option v-for="institution in data.institutions" :key="institution.name" :value="institution.name">
								{{ institution.institution_name }} · {{ institution.institution_type }}
							</option>
						</select>
					</label>
					<div>
						<span>Current context</span>
						<strong>{{ activeContext.institution_name || 'No active Institution' }}</strong>
						<small>{{ activeContext.branch_name || 'No active Branch' }}</small>
					</div>
					<button type="button" class="edge-button" @click="openCalendar">Open Academic Calendars</button>
				</section>

				<div class="eduedge-foundation-grid">
					<section class="eduedge-foundation-card">
						<div class="eduedge-card-heading">
							<div><p class="edge-eyebrow">{{ term('academic_section', false, 'Academic Section') }}</p><h2>{{ sectionDraft.name ? 'Edit' : 'Create' }} {{ term('academic_section', false, 'Academic Section') }}</h2></div>
							<button type="button" class="edge-button" @click="newSection">New</button>
						</div>
						<label>Name<input v-model.trim="sectionDraft.section_name" class="form-control" /></label>
						<label>Code<input v-model.trim="sectionDraft.section_code" class="form-control" :disabled="Boolean(sectionDraft.name)" /></label>
						<label>Sequence<input v-model.number="sectionDraft.sequence" type="number" min="1" class="form-control" /></label>
						<label class="eduedge-check"><input v-model="sectionDraft.enabled" type="checkbox" /> Enabled</label>
						<label>Description<textarea v-model.trim="sectionDraft.description" class="form-control" rows="3"></textarea></label>
						<button type="button" class="edge-button edge-button--primary" :disabled="!canSaveSection || saving === 'section'" @click="saveSection">
							{{ saving === 'section' ? 'Saving...' : `Save ${term('academic_section', false, 'Academic Section')}` }}
						</button>
					</section>

					<section class="eduedge-foundation-card">
						<div class="eduedge-card-heading">
							<div><p class="edge-eyebrow">{{ term('academic_level', false, 'Academic Level') }}</p><h2>{{ levelDraft.name ? 'Edit' : 'Create' }} {{ term('academic_level', false, 'Academic Level') }}</h2></div>
							<button type="button" class="edge-button" @click="newLevel">New</button>
						</div>
						<label>Name<input v-model.trim="levelDraft.level_name" class="form-control" /></label>
						<label>Code<input v-model.trim="levelDraft.level_code" class="form-control" :disabled="Boolean(levelDraft.name)" /></label>
						<label>{{ term('academic_section', false, 'Academic Section') }}
							<select v-model="levelDraft.academic_section" class="form-control"><option value="">Not assigned</option><option v-for="row in visibleSections" :key="row.name" :value="row.name">{{ row.section_name }}</option></select>
						</label>
						<label>Sequence<input v-model.number="levelDraft.sequence" type="number" min="1" class="form-control" /></label>
						<label>Next {{ term('academic_level', false, 'Academic Level') }}
							<select v-model="levelDraft.next_level" class="form-control"><option value="">Not set</option><option v-for="row in visibleLevels.filter(item => item.name !== levelDraft.name)" :key="row.name" :value="row.name">{{ row.level_name }}</option></select>
						</label>
						<label class="eduedge-check"><input v-model="levelDraft.enabled" type="checkbox" /> Enabled</label>
						<label>Description<textarea v-model.trim="levelDraft.description" class="form-control" rows="3"></textarea></label>
						<button type="button" class="edge-button edge-button--primary" :disabled="!canSaveLevel || saving === 'level'" @click="saveLevel">
							{{ saving === 'level' ? 'Saving...' : `Save ${term('academic_level', false, 'Academic Level')}` }}
						</button>
					</section>
				</div>

				<section class="eduedge-foundation-list">
					<div class="eduedge-card-heading"><div><p class="edge-eyebrow">Configured structure</p><h2>{{ selectedInstitutionLabel }}</h2></div><EdgeStatusBadge :label="`${visibleSections.length} sections · ${visibleLevels.length} levels`" status="active" tone="neutral" /></div>
					<EdgeEmptyState v-if="!selectedInstitution" title="Select an Institution" description="Choose an Institution to configure its academic structure." />
					<EdgeEmptyState v-else-if="!visibleSections.length && !visibleLevels.length" title="No academic structure configured" description="Create the first section or level for this Institution." />
					<div v-else class="eduedge-structure-columns">
						<div><h3>{{ term('academic_section', true, 'Academic Sections') }}</h3><button v-for="row in visibleSections" :key="row.name" type="button" class="eduedge-structure-row" @click="editSection(row)"><span><strong>{{ row.section_name }}</strong><small>{{ row.section_code }}</small></span><EdgeStatusBadge :label="row.enabled ? 'Enabled' : 'Disabled'" :status="row.enabled ? 'active' : 'inactive'" :tone="row.enabled ? 'success' : 'neutral'" /></button></div>
						<div><h3>{{ term('academic_level', true, 'Academic Levels') }}</h3><button v-for="row in visibleLevels" :key="row.name" type="button" class="eduedge-structure-row" @click="editLevel(row)"><span><strong>{{ row.level_name }}</strong><small>{{ row.level_code }}{{ row.academic_section ? ` · ${sectionName(row.academic_section)}` : '' }}</small></span><EdgeStatusBadge :label="row.enabled ? 'Enabled' : 'Disabled'" :status="row.enabled ? 'active' : 'inactive'" :tone="row.enabled ? 'success' : 'neutral'" /></button></div>
					</div>
				</section>
				<p v-if="saveError" class="eduedge-error">{{ saveError }}</p>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";
const emptySection = () => ({ name: "", section_name: "", section_code: "", sequence: 10, enabled: true, description: "" });
const emptyLevel = () => ({ name: "", level_name: "", level_code: "", academic_section: "", sequence: 10, next_level: "", enabled: true, description: "" });

export default {
	name: "EduEdgeAcademicFoundation",
	data() { return { loading: true, error: "", saveError: "", saving: "", selectedInstitution: "", sectionDraft: emptySection(), levelDraft: emptyLevel(), data: { active_context: {}, institutions: [], sections: [], levels: [], calendars: [], permissions: {} }, menuItems: EDUEDGE_MENU_ITEMS }; },
	computed: {
		activeContext() { return this.data.active_context || {}; },
		visibleSections() { return this.data.sections.filter(row => row.institution === this.selectedInstitution); },
		visibleLevels() { return this.data.levels.filter(row => row.institution === this.selectedInstitution); },
		selectedInstitutionLabel() { return this.data.institutions.find(row => row.name === this.selectedInstitution)?.institution_name || 'Select an Institution'; },
		canSaveSection() { const p = this.sectionDraft.name ? this.data.permissions.can_write_section : this.data.permissions.can_create_section; return Boolean(p && this.selectedInstitution && this.sectionDraft.section_name && this.sectionDraft.section_code); },
		canSaveLevel() { const p = this.levelDraft.name ? this.data.permissions.can_write_level : this.data.permissions.can_create_level; return Boolean(p && this.selectedInstitution && this.levelDraft.level_name && this.levelDraft.level_code); },
	},
	mounted() { this.load(); },
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") { return frappe.eduedge?.term?.(key, { plural, context: this.activeContext, fallback }) || fallback; },
		sectionName(name) { return this.data.sections.find(row => row.name === name)?.section_name || name; },
		async load() { this.loading = true; this.error = ""; try { const response = await frappe.call('eduedge.api.academic_foundation.get_academic_foundation'); this.data = response.message || this.data; this.selectedInstitution = this.selectedInstitution || this.activeContext.institution || this.data.institutions[0]?.name || ""; } catch (error) { this.error = error?.message || 'Academic Foundation could not be loaded.'; } finally { this.loading = false; } },
		resetDrafts() { this.newSection(); this.newLevel(); },
		newSection() { this.sectionDraft = emptySection(); this.saveError = ""; },
		newLevel() { this.levelDraft = emptyLevel(); this.saveError = ""; },
		editSection(row) { this.sectionDraft = { ...emptySection(), ...row, enabled: Boolean(row.enabled) }; },
		editLevel(row) { this.levelDraft = { ...emptyLevel(), ...row, enabled: Boolean(row.enabled) }; },
		async saveSection() { if (!this.canSaveSection) return; this.saving = 'section'; this.saveError = ""; try { await frappe.call('eduedge.api.academic_foundation.save_academic_section', { institution: this.selectedInstitution, section: this.sectionDraft.name || undefined, section_name: this.sectionDraft.section_name, section_code: this.sectionDraft.section_code, sequence: this.sectionDraft.sequence, enabled: this.sectionDraft.enabled ? 1 : 0, description: this.sectionDraft.description }); frappe.show_alert({ message: __('Academic Section saved'), indicator: 'green' }); this.newSection(); await this.load(); } catch (error) { this.saveError = error?.message || 'Academic Section could not be saved.'; } finally { this.saving = ""; } },
		async saveLevel() { if (!this.canSaveLevel) return; this.saving = 'level'; this.saveError = ""; try { await frappe.call('eduedge.api.academic_foundation.save_academic_level', { institution: this.selectedInstitution, level: this.levelDraft.name || undefined, level_name: this.levelDraft.level_name, level_code: this.levelDraft.level_code, academic_section: this.levelDraft.academic_section || undefined, sequence: this.levelDraft.sequence, next_level: this.levelDraft.next_level || undefined, enabled: this.levelDraft.enabled ? 1 : 0, description: this.levelDraft.description }); frappe.show_alert({ message: __('Academic Level saved'), indicator: 'green' }); this.newLevel(); await this.load(); } catch (error) { this.saveError = error?.message || 'Academic Level could not be saved.'; } finally { this.saving = ""; } },
		openCalendar() { window.open('/app/eduedge-institution-academic-calendar', '_blank', 'noopener,noreferrer'); },
	},
};
</script>

<style scoped>
.eduedge-foundation-context { display:grid; grid-template-columns:minmax(16rem,1fr) minmax(14rem,1fr) auto; gap:1rem; align-items:end; padding:1rem; margin-bottom:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-foundation-context label,.eduedge-foundation-context > div,.eduedge-foundation-card label { display:grid; gap:.35rem; }
.eduedge-foundation-context small,.eduedge-structure-row small { color:var(--text-muted); }
.eduedge-foundation-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; }
.eduedge-foundation-card,.eduedge-foundation-list { display:grid; gap:.75rem; padding:1rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-lg,12px); background:var(--card-bg); }
.eduedge-foundation-list { margin-top:1rem; }
.eduedge-card-heading { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }
.eduedge-card-heading h2,.eduedge-foundation-card h2 { margin:0; }
.eduedge-check { display:flex !important; grid-auto-flow:column; justify-content:start; align-items:center; }
.eduedge-structure-columns { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; }
.eduedge-structure-columns > div { display:grid; gap:.5rem; align-content:start; }
.eduedge-structure-row { width:100%; display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:.75rem; border:1px solid var(--border-color); border-radius:.75rem; background:var(--control-bg); text-align:left; }
.eduedge-structure-row span { display:grid; gap:.15rem; }
.eduedge-error { color:var(--red-600,#b42318); }
@media (max-width: 800px) { .eduedge-foundation-context,.eduedge-foundation-grid,.eduedge-structure-columns { grid-template-columns:1fr; } }
</style>
