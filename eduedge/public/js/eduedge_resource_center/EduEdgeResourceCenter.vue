<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="schoolIdentity.name || ''"
		:branch-name="activeBranchLabel"
		:menu-items="menuItems"
		:active-route="activeRoute"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					:eyebrow="page.eyebrow || 'EduEdge'"
					:title="page.title || 'Records'"
					:subtitle="page.subtitle || ''"
					:action-label="page.permissions.can_create ? `Add ${singularTitle}` : ''"
					@action="openCreate"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading records..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="This EduEdge page could not load"
				:message="error"
				action-label="Try again"
				@retry="loadPage(true)"
			/>
			<template v-else>
				<EdgeFilterBar :title="`${page.title} filters`">
					<div class="eduedge-resource-filters">
						<label class="eduedge-resource-search">
							<span>Search</span>
							<input
								v-model.trim="search"
								type="search"
								class="form-control"
								:placeholder="`Search ${String(page.title || 'records').toLowerCase()}`"
								@keyup.enter="applyFilters"
							/>
						</label>
						<label v-for="field in page.filters" :key="field.fieldname">
							<span>{{ field.label }}</span>
							<select
								v-if="['Select', 'Branch'].includes(field.type)"
								v-model="filterValues[field.fieldname]"
								class="form-control"
								@change="applyFilters"
							>
								<option value="">All</option>
								<option
									v-for="option in normalizedOptions(field.options)"
									:key="option.value"
									:value="option.value"
								>
									{{ option.label }}
								</option>
							</select>
							<input
								v-else
								v-model.trim="filterValues[field.fieldname]"
								class="form-control"
								:list="`resource-filter-${field.fieldname}`"
								placeholder="Type to filter"
								@change="applyFilters"
							/>
							<datalist v-if="field.options?.length" :id="`resource-filter-${field.fieldname}`">
								<option v-for="option in normalizedOptions(field.options)" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</datalist>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button" @click="resetFilters">Reset</button>
						<button type="button" class="edge-button edge-button--primary" @click="applyFilters">Refresh</button>
					</template>
				</EdgeFilterBar>

				<section class="eduedge-resource-panel">
					<div class="eduedge-resource-panel__heading">
						<div>
							<p class="edge-eyebrow">Permission-aware records</p>
							<h2>{{ page.title }}</h2>
							<p>{{ page.rows.length }} record{{ page.rows.length === 1 ? '' : 's' }} on this page</p>
						</div>
						<button
							v-if="page.permissions.can_create"
							type="button"
							class="edge-button edge-button--primary"
							@click="openCreate"
						>
							Add {{ singularTitle }}
						</button>
					</div>

					<EdgeEmptyState
						v-if="!page.rows.length"
						:title="`No ${String(page.title || 'records').toLowerCase()} found`"
						description="Change the filters or add a new record if your role permits it."
					/>
					<div v-else class="eduedge-resource-table-wrap">
						<table class="table eduedge-resource-table">
							<thead>
								<tr>
									<th v-for="column in page.columns" :key="column.fieldname">{{ column.label }}</th>
									<th>Actions</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in page.rows" :key="row.name">
									<td v-for="column in page.columns" :key="column.fieldname">
										<EdgeStatusBadge
											v-if="column.type === 'Check'"
											:label="truthy(row[column.fieldname]) ? 'Yes' : 'No'"
											:status="truthy(row[column.fieldname]) ? 'active' : 'inactive'"
											:tone="truthy(row[column.fieldname]) ? 'success' : 'neutral'"
										/>
										<EdgeStatusBadge
											v-else-if="column.type === 'Status'"
											:label="row[column.fieldname] || 'Not set'"
											:status="row[column.fieldname] || 'not-set'"
											:tone="statusTone(row[column.fieldname])"
										/>
										<span v-else>{{ displayValue(row[column.fieldname]) }}</span>
									</td>
									<td>
										<div class="eduedge-resource-actions">
											<button
												v-if="page.permissions.can_write"
												type="button"
												class="edge-button"
												@click="openEdit(row)"
											>
												Edit
											</button>
											<button type="button" class="edge-button" @click="openFullForm(row)">Full form</button>
											<button
												v-if="page.permissions.can_delete"
												type="button"
												class="edge-button edge-button--danger"
												@click="requestDelete(row)"
											>
												Delete
											</button>
										</div>
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<div class="eduedge-resource-pagination">
						<button type="button" class="edge-button" :disabled="page.start <= 0" @click="previousPage">Previous</button>
						<span>Page {{ currentPage }}</span>
						<button type="button" class="edge-button" :disabled="!page.has_more" @click="nextPage">Next</button>
					</div>
				</section>
			</template>
		</EdgePageLayout>

		<EdgeFormDialog
			:open="modal.open"
			:title="modal.title"
			:subtitle="modalSubtitle"
			:fields="modal.fields"
			:model-value="modal.values"
			:field-errors="modal.fieldErrors"
			:error="modal.error"
			:loading="modal.loading"
			:busy="modal.busy"
			:submit-label="modal.submitLabel"
			:show-full-form="Boolean(modal.fullFormRoute)"
			@close="closeModal"
			@update:model-value="updateModalValues"
			@field-change="onModalFieldChange"
			@search-options="onSearchOptions"
			@submit="saveModal"
			@open-full-form="openModalFullForm"
		/>

		<EdgeModal
			:open="deleteState.open"
			title="Delete record?"
			:subtitle="deleteState.label"
			:busy="deleteState.busy"
			@close="closeDelete"
		>
			<p>This action uses normal Frappe delete permission and linked-record validation. It cannot delete submitted records.</p>
			<p v-if="deleteState.error" class="eduedge-resource-error">{{ deleteState.error }}</p>
			<template #footer>
				<button type="button" class="edge-button" :disabled="deleteState.busy" @click="closeDelete">Cancel</button>
				<button type="button" class="edge-button edge-button--danger" :disabled="deleteState.busy" @click="confirmDelete">
					{{ deleteState.busy ? 'Deleting...' : 'Delete' }}
				</button>
			</template>
		</EdgeModal>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";
import {
	closeResourceModal,
	createResourceModalState,
	handleResourceFieldChange,
	openResourceFullForm,
	openResourceModal,
	saveResourceModal,
	searchResourceOptions,
	updateResourceModalValues,
} from "../eduedge_ui/resource_modal";

export default {
	name: "EduEdgeResourceCenter",
	props: {
		resourceKey: { type: String, required: true },
		activeRoute: { type: String, required: true },
	},
	data() {
		return {
			loading: true,
			error: "",
			search: "",
			filterValues: {},
			menuItems: EDUEDGE_MENU_ITEMS,
			page: {
				title: "",
				eyebrow: "",
				subtitle: "",
				columns: [],
				rows: [],
				filters: [],
				start: 0,
				page_length: 20,
				has_more: false,
				permissions: { can_create: false, can_write: false, can_delete: false },
			},
			modal: createResourceModalState(),
			deleteState: { open: false, busy: false, name: "", label: "", error: "" },
		};
	},
	computed: {
		singularTitle() {
			const title = String(this.page.title || "Record");
			if (title.endsWith("ies")) return `${title.slice(0, -3)}y`;
			if (title.endsWith("s")) return title.slice(0, -1);
			return title;
		},
		currentPage() {
			return Math.floor((this.page.start || 0) / (this.page.page_length || 20)) + 1;
		},
		activeBranchLabel() {
			const branchFilter = this.page.filters.find((field) => field.type === "Branch");
			const selected = this.filterValues.branch;
			const option = this.normalizedOptions(branchFilter?.options).find((item) => item.value === selected);
			return option?.label || "All permitted branches";
		},
		schoolIdentity() {
			return frappe.boot?.eduedge_ui_identity?.school || {};
		},
		modalSubtitle() {
			return [this.modal.subtitle, this.modal.advancedNote].filter(Boolean).join(" ");
		},
	},
	mounted() {
		this.loadPage(true);
	},
	methods: {
		openRoute: openEduEdgeRoute,
		normalizedOptions(options) {
			return (Array.isArray(options) ? options : []).map((option) =>
				typeof option === "object"
					? { value: String(option.value ?? option.name ?? ""), label: String(option.label ?? option.value ?? option.name ?? "") }
					: { value: String(option), label: option === "1" ? "Yes" : option === "0" ? "No" : String(option) }
			);
		},
		truthy(value) {
			return value === true || Number(value) === 1 || String(value).toLowerCase() === "yes";
		},
		displayValue(value) {
			return value === undefined || value === null || value === "" ? "—" : String(value);
		},
		statusTone(status) {
			if (["Approved", "Admitted", "Active", "Published"].includes(status)) return "success";
			if (["Rejected", "Disabled", "Cancelled"].includes(status)) return "danger";
			if (["Applied", "Pending", "Draft"].includes(status)) return "warning";
			return "neutral";
		},
		async loadPage(resetStart = false) {
			if (resetStart) this.page.start = 0;
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.resource_center.get_resource_page", {
					resource: this.resourceKey,
					search: this.search,
					filters: JSON.stringify(this.filterValues || {}),
					start: this.page.start || 0,
					page_length: this.page.page_length || 20,
				});
				const next = response.message || {};
				this.page = { ...this.page, ...next };
				for (const field of this.page.filters || []) {
					if (!(field.fieldname in this.filterValues)) this.filterValues[field.fieldname] = "";
				}
			} catch (error) {
				this.error = error?.message || "Records could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		applyFilters() {
			this.loadPage(true);
		},
		resetFilters() {
			this.search = "";
			this.filterValues = {};
			this.loadPage(true);
		},
		previousPage() {
			this.page.start = Math.max(0, (this.page.start || 0) - (this.page.page_length || 20));
			this.loadPage(false);
		},
		nextPage() {
			if (!this.page.has_more) return;
			this.page.start = (this.page.start || 0) + (this.page.page_length || 20);
			this.loadPage(false);
		},
		modalContext() {
			const context = {};
			if (this.filterValues.branch) {
				if (this.resourceKey === "program_offerings") context.school_branch = this.filterValues.branch;
				else if (["admissions", "applicants", "students"].includes(this.resourceKey)) context.eduedge_school_branch = this.filterValues.branch;
			}
			return context;
		},
		openCreate() {
			openResourceModal(this.modal, { resource: this.resourceKey, context: this.modalContext() });
		},
		openEdit(row) {
			openResourceModal(this.modal, { resource: this.resourceKey, name: row.name });
		},
		closeModal() {
			closeResourceModal(this.modal);
		},
		updateModalValues(values) {
			updateResourceModalValues(this.modal, values);
		},
		onModalFieldChange(payload) {
			handleResourceFieldChange(this.modal, payload);
		},
		onSearchOptions(payload) {
			searchResourceOptions(this.modal, payload);
		},
		async saveModal() {
			const saved = await saveResourceModal(this.modal);
			if (!saved) return;
			closeResourceModal(this.modal);
			await this.loadPage(true);
			frappe.show_alert({ message: __("Record saved"), indicator: "green" });
		},
		openModalFullForm() {
			openResourceFullForm(this.modal);
		},
		openFullForm(row) {
			const route = `${this.page.full_form_route || ''}/${encodeURIComponent(row.name)}`;
			window.open(route, "_blank", "noopener,noreferrer");
		},
		requestDelete(row) {
			this.deleteState = {
				open: true,
				busy: false,
				name: row.name,
				label: row[this.page.title_field] || row.name,
				error: "",
			};
		},
		closeDelete() {
			if (this.deleteState.busy) return;
			this.deleteState = { open: false, busy: false, name: "", label: "", error: "" };
		},
		async confirmDelete() {
			this.deleteState.busy = true;
			this.deleteState.error = "";
			try {
				await frappe.call("eduedge.api.resource_center.delete_resource_record", {
					resource: this.resourceKey,
					name: this.deleteState.name,
				});
				this.closeDelete();
				await this.loadPage(false);
				frappe.show_alert({ message: __("Record deleted"), indicator: "green" });
			} catch (error) {
				this.deleteState.error = error?.message || "The record could not be deleted.";
				this.deleteState.busy = false;
			}
		},
	},
};
</script>

<style scoped>
.eduedge-resource-filters {
	display: grid;
	gap: .8rem;
	grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
	width: min(64rem, 100%);
}
.eduedge-resource-filters label { display: grid; gap: .35rem; }
.eduedge-resource-search { min-width: 16rem; }
.eduedge-resource-panel {
	background: var(--edge-color-surface, var(--card-bg));
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-lg, 12px);
	margin-top: var(--edge-section-gap, 1rem);
	padding: var(--edge-space-5, 1.25rem);
}
.eduedge-resource-panel__heading {
	align-items: flex-start;
	display: flex;
	gap: 1rem;
	justify-content: space-between;
	margin-bottom: 1rem;
}
.eduedge-resource-panel__heading h2 { margin: .2rem 0; }
.eduedge-resource-panel__heading p { color: var(--text-muted); margin-bottom: 0; }
.eduedge-resource-table-wrap { overflow-x: auto; }
.eduedge-resource-table { margin-bottom: 0; min-width: 58rem; }
.eduedge-resource-table th { white-space: nowrap; }
.eduedge-resource-table td { vertical-align: middle; }
.eduedge-resource-actions { display: flex; flex-wrap: wrap; gap: .4rem; }
.eduedge-resource-pagination {
	align-items: center;
	display: flex;
	gap: .75rem;
	justify-content: flex-end;
	margin-top: 1rem;
}
.eduedge-resource-error { color: var(--red-600, #b42318); }
.edge-button--danger { border-color: var(--red-500, #d64545); color: var(--red-600, #b42318); }
@media (max-width: 47.99rem) {
	.eduedge-resource-panel__heading { flex-direction: column; }
	.eduedge-resource-pagination { justify-content: space-between; }
}
</style>
