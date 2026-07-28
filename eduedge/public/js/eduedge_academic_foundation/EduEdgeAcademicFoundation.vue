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
					:title="`${term('academic_section', true, 'Academic Sections')}, ${term('academic_level', true, 'Academic Levels')} and Calendars`"
					subtitle="Configure institution-owned structure, progression pathways, and academic calendars without changing Frappe Education identities."
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading academic foundation..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Academic Foundation could not load"
				:message="error"
				action-label="Try again"
				@retry="load"
			/>
			<template v-else>
				<EdgeFilterBar title="Institution context">
					<div class="eduedge-foundation-context-grid">
						<label>
							<span>Institution</span>
							<select v-model="selectedInstitution" class="form-control" @change="institutionChanged">
								<option value="">Select Institution</option>
								<option
									v-for="institution in data.institutions"
									:key="institution.name"
									:value="institution.name"
								>
									{{ institution.institution_name }} · {{ institution.institution_type }}
								</option>
							</select>
						</label>
						<div class="eduedge-context-summary">
							<span>Current product context</span>
							<strong>{{ activeContext.institution_name || "No active Institution" }}</strong>
							<small>{{ activeContext.branch_name || "No active Branch" }}</small>
						</div>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="openCalendarList">All calendars</button>
						<button
							v-if="data.permissions.can_create_calendar"
							type="button"
							class="edge-button edge-button--primary"
							:disabled="!selectedInstitution"
							@click="createCalendar"
						>
							New calendar
						</button>
					</template>
				</EdgeFilterBar>

				<EdgeEmptyState
					v-if="!selectedInstitution"
					title="Select an Institution"
					description="Choose an Institution to configure its academic structure and calendar."
				/>
				<template v-else>
					<EdgeDashboardLayout min-column-width="12rem">
						<EdgeStatCard
							:label="term('academic_section', true, 'Academic Sections')"
							:value="enabledSections.length"
							helper="Enabled structure groups"
						/>
						<EdgeStatCard
							:label="term('academic_level', true, 'Academic Levels')"
							:value="enabledLevels.length"
							helper="Enabled progression levels"
						/>
						<EdgeStatCard
							label="Academic Calendars"
							:value="visibleCalendars.length"
							helper="Configured for this Institution"
						/>
						<EdgeStatCard
							label="Foundation Readiness"
							:value="selectedReadiness.ready ? 'Ready' : 'Needs attention'"
							:tone="selectedReadiness.ready ? 'success' : 'warning'"
							:helper="`${selectedReadiness.issues.length} issue(s)`"
						/>
					</EdgeDashboardLayout>

					<section class="eduedge-foundation-readiness">
						<div class="eduedge-card-heading">
							<div>
								<p class="edge-eyebrow">Readiness</p>
								<h2>{{ selectedInstitutionLabel }}</h2>
							</div>
							<EdgeStatusBadge
								:label="selectedReadiness.ready ? 'Ready for academic operations' : 'Setup needs attention'"
								:status="selectedReadiness.ready ? 'ready' : 'attention'"
								:tone="selectedReadiness.ready ? 'success' : 'warning'"
							/>
						</div>
						<div v-if="selectedReadiness.issues.length" class="eduedge-issue-list">
							<div
								v-for="issue in selectedReadiness.issues"
								:key="issue.code"
								class="eduedge-issue-row"
							>
								<EdgeStatusBadge
									:label="issue.severity === 'danger' ? 'Required' : 'Review'"
									:status="issue.severity"
									:tone="issue.severity === 'danger' ? 'danger' : 'warning'"
								/>
								<span>{{ issue.message }}</span>
							</div>
						</div>
						<p v-else class="eduedge-ready-copy">
							Enabled structure, progression references, and the current academic calendar are ready.
						</p>
					</section>

					<div class="eduedge-foundation-grid">
						<section class="eduedge-foundation-card">
							<div class="eduedge-card-heading">
								<div>
									<p class="edge-eyebrow">{{ term("academic_section", false, "Academic Section") }}</p>
									<h2>
										{{ sectionDraft.name ? "Edit" : "Create" }}
										{{ term("academic_section", false, "Academic Section") }}
									</h2>
								</div>
								<button type="button" class="edge-button" @click="newSection">New</button>
							</div>
							<label>
								Name
								<input v-model.trim="sectionDraft.section_name" class="form-control" />
							</label>
							<label>
								Code
								<input
									v-model.trim="sectionDraft.section_code"
									class="form-control"
									:disabled="Boolean(sectionDraft.name)"
								/>
							</label>
							<label>
								Sequence
								<input v-model.number="sectionDraft.sequence" type="number" min="1" class="form-control" />
							</label>
							<label class="eduedge-check">
								<input v-model="sectionDraft.enabled" type="checkbox" />
								Enabled
							</label>
							<label>
								Description
								<textarea v-model.trim="sectionDraft.description" class="form-control" rows="3"></textarea>
							</label>
							<button
								type="button"
								class="edge-button edge-button--primary"
								:disabled="!canSaveSection || saving === 'section'"
								@click="saveSection"
							>
								{{ saving === "section" ? "Saving..." : `Save ${term("academic_section", false, "Academic Section")}` }}
							</button>
						</section>

						<section class="eduedge-foundation-card">
							<div class="eduedge-card-heading">
								<div>
									<p class="edge-eyebrow">{{ term("academic_level", false, "Academic Level") }}</p>
									<h2>
										{{ levelDraft.name ? "Edit" : "Create" }}
										{{ term("academic_level", false, "Academic Level") }}
									</h2>
								</div>
								<button type="button" class="edge-button" @click="newLevel">New</button>
							</div>
							<label>
								Name
								<input v-model.trim="levelDraft.level_name" class="form-control" />
							</label>
							<label>
								Code
								<input
									v-model.trim="levelDraft.level_code"
									class="form-control"
									:disabled="Boolean(levelDraft.name)"
								/>
							</label>
							<label>
								{{ term("academic_section", false, "Academic Section") }}
								<select v-model="levelDraft.academic_section" class="form-control">
									<option value="">Not assigned</option>
									<option v-for="row in visibleSections" :key="row.name" :value="row.name">
										{{ row.section_name }}
									</option>
								</select>
							</label>
							<label>
								Sequence
								<input v-model.number="levelDraft.sequence" type="number" min="1" class="form-control" />
							</label>
							<label>
								Next {{ term("academic_level", false, "Academic Level") }}
								<select v-model="levelDraft.next_level" class="form-control">
									<option value="">Not set</option>
									<option
										v-for="row in visibleLevels.filter((item) => item.name !== levelDraft.name)"
										:key="row.name"
										:value="row.name"
									>
										{{ row.level_name }}
									</option>
								</select>
							</label>
							<label class="eduedge-check">
								<input v-model="levelDraft.enabled" type="checkbox" />
								Enabled
							</label>
							<label>
								Description
								<textarea v-model.trim="levelDraft.description" class="form-control" rows="3"></textarea>
							</label>
							<button
								type="button"
								class="edge-button edge-button--primary"
								:disabled="!canSaveLevel || saving === 'level'"
								@click="saveLevel"
							>
								{{ saving === "level" ? "Saving..." : `Save ${term("academic_level", false, "Academic Level")}` }}
							</button>
						</section>
					</div>

					<section class="eduedge-foundation-list">
						<div class="eduedge-card-heading">
							<div>
								<p class="edge-eyebrow">Configured structure</p>
								<h2>{{ selectedInstitutionLabel }}</h2>
							</div>
							<EdgeStatusBadge
								:label="`${visibleSections.length} sections · ${visibleLevels.length} levels`"
								status="active"
								tone="neutral"
							/>
						</div>
						<EdgeEmptyState
							v-if="!visibleSections.length && !visibleLevels.length"
							title="No academic structure configured"
							description="Create the first section or level for this Institution."
						/>
						<div v-else class="eduedge-structure-columns">
							<div>
								<h3>{{ term("academic_section", true, "Academic Sections") }}</h3>
								<button
									v-for="row in visibleSections"
									:key="row.name"
									type="button"
									class="eduedge-structure-row"
									@click="editSection(row)"
								>
									<span>
										<strong>{{ row.section_name }}</strong>
										<small>{{ row.section_code }}</small>
									</span>
									<EdgeStatusBadge
										:label="row.enabled ? 'Enabled' : 'Disabled'"
										:status="row.enabled ? 'active' : 'inactive'"
										:tone="row.enabled ? 'success' : 'neutral'"
									/>
								</button>
							</div>
							<div>
								<h3>{{ term("academic_level", true, "Academic Levels") }}</h3>
								<button
									v-for="row in visibleLevels"
									:key="row.name"
									type="button"
									class="eduedge-structure-row"
									@click="editLevel(row)"
								>
									<span>
										<strong>{{ row.level_name }}</strong>
										<small>
											{{ row.level_code }}
											{{ row.academic_section ? ` · ${sectionName(row.academic_section)}` : "" }}
										</small>
									</span>
									<EdgeStatusBadge
										:label="row.enabled ? 'Enabled' : 'Disabled'"
										:status="row.enabled ? 'active' : 'inactive'"
										:tone="row.enabled ? 'success' : 'neutral'"
									/>
								</button>
							</div>
						</div>
					</section>

					<div class="eduedge-foundation-detail-grid">
						<section class="eduedge-foundation-list">
							<div class="eduedge-card-heading">
								<div>
									<p class="edge-eyebrow">Progression pathway</p>
									<h2>{{ term("academic_level", true, "Academic Levels") }}</h2>
								</div>
								<EdgeStatusBadge
									:label="`${selectedProgression.chains.length} pathway(s)`"
									status="progression"
									tone="neutral"
								/>
							</div>
							<EdgeEmptyState
								v-if="!selectedProgression.chains.length"
								title="No progression pathway"
								description="Configure enabled Academic Levels and their Next Level relationships."
							/>
							<div v-else class="eduedge-progression-list">
								<div
									v-for="(chain, index) in selectedProgression.chains"
									:key="chain.root || index"
									class="eduedge-progression-chain"
								>
									<div class="eduedge-progression-heading">
										<strong>{{ chain.section_name || `Pathway ${index + 1}` }}</strong>
										<small>{{ chain.levels.length }} level(s)</small>
									</div>
									<div class="eduedge-progression-steps">
										<template v-for="(level, levelIndex) in chain.levels" :key="level.name">
											<button type="button" class="eduedge-level-chip" @click="editLevelByName(level.name)">
												<strong>{{ level.level_name }}</strong>
												<small>{{ level.level_code }}</small>
											</button>
											<span v-if="levelIndex < chain.levels.length - 1" class="eduedge-arrow">→</span>
										</template>
									</div>
								</div>
							</div>
						</section>

						<section class="eduedge-foundation-list">
							<div class="eduedge-card-heading">
								<div>
									<p class="edge-eyebrow">Academic calendars</p>
									<h2>Years and periods</h2>
								</div>
								<EdgeStatusBadge
									:label="currentCalendar ? 'Current calendar configured' : 'No current calendar'"
									:status="currentCalendar ? 'current' : 'missing'"
									:tone="currentCalendar ? 'success' : 'warning'"
								/>
							</div>
							<EdgeEmptyState
								v-if="!visibleCalendars.length"
								title="No academic calendar"
								description="Create an Institution Academic Calendar and add its periods."
							/>
							<div v-else class="eduedge-calendar-list">
								<article v-for="calendar in visibleCalendars" :key="calendar.name" class="eduedge-calendar-card">
									<div class="eduedge-calendar-heading">
										<div>
											<strong>{{ calendar.academic_year }}</strong>
											<small>{{ formatDate(calendar.start_date) }} – {{ formatDate(calendar.end_date) }}</small>
										</div>
										<div class="eduedge-calendar-badges">
											<EdgeStatusBadge
												v-if="calendar.is_current"
												label="Current"
												status="current"
												tone="success"
											/>
											<EdgeStatusBadge
												:label="calendar.enabled ? 'Enabled' : 'Disabled'"
												:status="calendar.enabled ? 'active' : 'inactive'"
												:tone="calendar.enabled ? 'neutral' : 'warning'"
											/>
										</div>
									</div>
									<div v-if="calendar.periods.length" class="eduedge-period-list">
										<div v-for="period in calendar.periods" :key="period.name" class="eduedge-period-row">
											<span>
												<strong>{{ period.academic_term }}</strong>
												<small>{{ formatDate(period.start_date) }} – {{ formatDate(period.end_date) }}</small>
											</span>
											<EdgeStatusBadge
												:label="calendar.current_period?.name === period.name ? 'Current period' : 'Configured'"
												:status="calendar.current_period?.name === period.name ? 'current' : 'configured'"
												:tone="calendar.current_period?.name === period.name ? 'success' : 'neutral'"
											/>
										</div>
									</div>
									<p v-else class="text-muted">No Academic Periods configured.</p>
									<p v-if="calendar.has_calendar_gap_today" class="eduedge-calendar-warning">
										Today is inside this calendar but outside every configured Academic Period.
									</p>
									<button
										type="button"
										class="edge-button"
										:disabled="!data.permissions.can_write_calendar"
										@click="editCalendar(calendar)"
									>
										Open calendar
									</button>
								</article>
							</div>
						</section>
					</div>
					<p v-if="saveError" class="eduedge-error">{{ saveError }}</p>
				</template>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

const emptySection = () => ({
	name: "",
	section_name: "",
	section_code: "",
	sequence: 10,
	enabled: true,
	description: "",
});
const emptyLevel = () => ({
	name: "",
	level_name: "",
	level_code: "",
	academic_section: "",
	sequence: 10,
	next_level: "",
	enabled: true,
	description: "",
});

export default {
	name: "EduEdgeAcademicFoundation",
	data() {
		return {
			loading: true,
			error: "",
			saveError: "",
			saving: "",
			selectedInstitution: "",
			sectionDraft: emptySection(),
			levelDraft: emptyLevel(),
			data: {
				active_context: {},
				institutions: [],
				sections: [],
				levels: [],
				calendars: [],
				progression: {},
				readiness: [],
				permissions: {},
			},
			menuItems: EDUEDGE_MENU_ITEMS,
		};
	},
	computed: {
		activeContext() {
			return this.data.active_context || {};
		},
		visibleSections() {
			return this.data.sections.filter((row) => row.institution === this.selectedInstitution);
		},
		visibleLevels() {
			return this.data.levels.filter((row) => row.institution === this.selectedInstitution);
		},
		enabledSections() {
			return this.visibleSections.filter((row) => Boolean(row.enabled));
		},
		enabledLevels() {
			return this.visibleLevels.filter((row) => Boolean(row.enabled));
		},
		visibleCalendars() {
			return this.data.calendars.filter((row) => row.institution === this.selectedInstitution);
		},
		currentCalendar() {
			return this.visibleCalendars.find((row) => Boolean(row.enabled) && Boolean(row.is_current)) || null;
		},
		selectedProgression() {
			return this.data.progression[this.selectedInstitution] || {
				chains: [],
				gaps: [],
				enabled_level_count: 0,
				terminal_level_count: 0,
			};
		},
		selectedReadiness() {
			return (
				this.data.readiness.find((row) => row.institution === this.selectedInstitution) || {
					ready: false,
					issues: [],
					enabled_sections: 0,
					enabled_levels: 0,
					enabled_calendars: 0,
					current_calendar: null,
				}
			);
		},
		selectedInstitutionLabel() {
			return (
				this.data.institutions.find((row) => row.name === this.selectedInstitution)?.institution_name ||
				"Select an Institution"
			);
		},
		canSaveSection() {
			const permitted = this.sectionDraft.name
				? this.data.permissions.can_write_section
				: this.data.permissions.can_create_section;
			return Boolean(
				permitted &&
					this.selectedInstitution &&
					this.sectionDraft.section_name &&
					this.sectionDraft.section_code
			);
		},
		canSaveLevel() {
			const permitted = this.levelDraft.name
				? this.data.permissions.can_write_level
				: this.data.permissions.can_create_level;
			return Boolean(
				permitted &&
					this.selectedInstitution &&
					this.levelDraft.level_name &&
					this.levelDraft.level_code
			);
		},
	},
	mounted() {
		this.load();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		term(key, plural = false, fallback = "") {
			return (
				frappe.eduedge?.term?.(key, {
					plural,
					context: this.activeContext,
					fallback,
				}) || fallback
			);
		},
		sectionName(name) {
			return this.data.sections.find((row) => row.name === name)?.section_name || name;
		},
		formatDate(value) {
			return value ? frappe.datetime.str_to_user(value) : "—";
		},
		async load() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.academic_foundation.get_academic_foundation");
				this.data = response.message || this.data;
				this.selectedInstitution =
					this.selectedInstitution ||
					this.activeContext.institution ||
					this.data.institutions[0]?.name ||
					"";
			} catch (error) {
				this.error = error?.message || "Academic Foundation could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		institutionChanged() {
			this.resetDrafts();
		},
		resetDrafts() {
			this.newSection();
			this.newLevel();
		},
		newSection() {
			this.sectionDraft = emptySection();
			this.saveError = "";
		},
		newLevel() {
			this.levelDraft = emptyLevel();
			this.saveError = "";
		},
		editSection(row) {
			this.sectionDraft = { ...emptySection(), ...row, enabled: Boolean(row.enabled) };
		},
		editLevel(row) {
			this.levelDraft = { ...emptyLevel(), ...row, enabled: Boolean(row.enabled) };
		},
		editLevelByName(name) {
			const row = this.visibleLevels.find((item) => item.name === name);
			if (row) this.editLevel(row);
		},
		async saveSection() {
			if (!this.canSaveSection) return;
			this.saving = "section";
			this.saveError = "";
			try {
				await frappe.call("eduedge.api.academic_foundation.save_academic_section", {
					institution: this.selectedInstitution,
					section: this.sectionDraft.name || undefined,
					section_name: this.sectionDraft.section_name,
					section_code: this.sectionDraft.section_code,
					sequence: this.sectionDraft.sequence,
					enabled: this.sectionDraft.enabled ? 1 : 0,
					description: this.sectionDraft.description,
				});
				frappe.show_alert({ message: __("Academic Section saved"), indicator: "green" });
				this.newSection();
				await this.load();
			} catch (error) {
				this.saveError = error?.message || "Academic Section could not be saved.";
			} finally {
				this.saving = "";
			}
		},
		async saveLevel() {
			if (!this.canSaveLevel) return;
			this.saving = "level";
			this.saveError = "";
			try {
				await frappe.call("eduedge.api.academic_foundation.save_academic_level", {
					institution: this.selectedInstitution,
					level: this.levelDraft.name || undefined,
					level_name: this.levelDraft.level_name,
					level_code: this.levelDraft.level_code,
					academic_section: this.levelDraft.academic_section || undefined,
					sequence: this.levelDraft.sequence,
					next_level: this.levelDraft.next_level || undefined,
					enabled: this.levelDraft.enabled ? 1 : 0,
					description: this.levelDraft.description,
				});
				frappe.show_alert({ message: __("Academic Level saved"), indicator: "green" });
				this.newLevel();
				await this.load();
			} catch (error) {
				this.saveError = error?.message || "Academic Level could not be saved.";
			} finally {
				this.saving = "";
			}
		},
		openCalendarList() {
			window.open(
				"/app/eduedge-institution-academic-calendar",
				"_blank",
				"noopener,noreferrer"
			);
		},
		createCalendar() {
			if (!this.selectedInstitution || !this.data.permissions.can_create_calendar) return;
			frappe.new_doc("EduEdge Institution Academic Calendar", {
				institution: this.selectedInstitution,
				enabled: 1,
			});
		},
		editCalendar(calendar) {
			if (!calendar?.name || !this.data.permissions.can_write_calendar) return;
			frappe.set_route("Form", "EduEdge Institution Academic Calendar", calendar.name);
		},
	},
};
</script>

<style scoped>
.eduedge-foundation-context-grid {
	display: grid;
	grid-template-columns: minmax(16rem, 1fr) minmax(14rem, 1fr);
	gap: 1rem;
	width: 100%;
	align-items: end;
}

.eduedge-foundation-context-grid label,
.eduedge-context-summary,
.eduedge-foundation-card label {
	display: grid;
	gap: 0.35rem;
}

.eduedge-context-summary small,
.eduedge-structure-row small,
.eduedge-progression-heading small,
.eduedge-level-chip small,
.eduedge-calendar-heading small,
.eduedge-period-row small {
	color: var(--text-muted);
}

.eduedge-foundation-readiness,
.eduedge-foundation-card,
.eduedge-foundation-list {
	display: grid;
	gap: 0.75rem;
	padding: 1rem;
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-lg, 12px);
	background: var(--card-bg);
}

.eduedge-foundation-readiness {
	margin-top: 1rem;
}

.eduedge-foundation-grid,
.eduedge-foundation-detail-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 1rem;
	margin-top: 1rem;
}

.eduedge-card-heading,
.eduedge-calendar-heading,
.eduedge-progression-heading {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 1rem;
}

.eduedge-card-heading h2,
.eduedge-foundation-card h2 {
	margin: 0;
}

.eduedge-check {
	display: flex !important;
	gap: 0.5rem !important;
	justify-content: flex-start;
	align-items: center;
}

.eduedge-issue-list,
.eduedge-progression-list,
.eduedge-calendar-list,
.eduedge-period-list {
	display: grid;
	gap: 0.75rem;
}

.eduedge-issue-row {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	padding: 0.75rem;
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-md, 8px);
	background: var(--control-bg);
}

.eduedge-ready-copy {
	margin: 0;
	color: var(--text-muted);
}

.eduedge-structure-columns {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 1rem;
}

.eduedge-structure-columns > div {
	display: grid;
	gap: 0.5rem;
	align-content: start;
}

.eduedge-structure-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 1rem;
	width: 100%;
	padding: 0.75rem;
	border: 1px solid var(--border-color);
	border-radius: 0.75rem;
	background: var(--control-bg);
	text-align: left;
}

.eduedge-structure-row span,
.eduedge-period-row span {
	display: grid;
	gap: 0.15rem;
}

.eduedge-progression-chain,
.eduedge-calendar-card {
	display: grid;
	gap: 0.75rem;
	padding: 0.9rem;
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-md, 8px);
	background: var(--control-bg);
}

.eduedge-progression-steps {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 0.5rem;
}

.eduedge-level-chip {
	display: grid;
	gap: 0.15rem;
	padding: 0.55rem 0.7rem;
	border: 1px solid var(--border-color);
	border-radius: 999px;
	background: var(--card-bg);
	text-align: left;
}

.eduedge-arrow {
	color: var(--text-muted);
	font-weight: 700;
}

.eduedge-calendar-badges {
	display: flex;
	flex-wrap: wrap;
	justify-content: flex-end;
	gap: 0.4rem;
}

.eduedge-period-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 0.75rem;
	padding: 0.65rem;
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-md, 8px);
	background: var(--card-bg);
}

.eduedge-calendar-warning,
.eduedge-error {
	margin: 0;
	color: var(--red-600, #b42318);
}

@media (max-width: 900px) {
	.eduedge-foundation-context-grid,
	.eduedge-foundation-grid,
	.eduedge-foundation-detail-grid,
	.eduedge-structure-columns {
		grid-template-columns: 1fr;
	}
}
</style>
