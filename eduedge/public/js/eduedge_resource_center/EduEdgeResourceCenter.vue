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
					:action-label="page.permissions.can_create ? (page.create_label || `Add ${singularTitle}`) : ''"
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

				<section v-if="resourceKey === 'result_audit'" class="eduedge-resource-panel eduedge-archive-audit">
					<div class="eduedge-resource-panel__heading">
						<div>
							<p class="edge-eyebrow">Immutable issued report</p>
							<h2>Issued Report Integrity</h2>
							<p>Verify both the frozen Report Card payload and the stored official PDF after backup, restore, or storage changes.</p>
						</div>
						<div class="eduedge-archive-controls">
							<input
								v-model.trim="archiveAudit.search"
								type="search"
								class="form-control"
								placeholder="Search issue, student or publication"
								@keyup.enter="applyArchiveFilters"
							/>
							<select v-model="archiveAudit.branch" class="form-control" @change="applyArchiveFilters">
								<option value="">Current / permitted scope</option>
								<option v-for="branch in archiveAudit.allowed_branches" :key="branch.name" :value="branch.name">
									{{ branch.branch_name || branch.name }}
								</option>
							</select>
							<input
								v-model.trim="archiveAudit.publication"
								class="form-control"
								placeholder="Result Publication"
								@change="applyArchiveFilters"
							/>
							<input
								v-model.trim="archiveAudit.student"
								class="form-control"
								placeholder="Student ID"
								@change="applyArchiveFilters"
							/>
							<button type="button" class="edge-button" @click="resetArchiveFilters">Reset</button>
							<button type="button" class="edge-button" :disabled="archiveAudit.loading" @click="loadArchiveAudit(false)">Recheck</button>
							<button
								type="button"
								class="edge-button edge-button--primary"
								:disabled="archiveAudit.loading || !archiveAudit.rows.length"
								@click="exportArchiveEvidence"
							>
								Export checked page
							</button>
						</div>
					</div>
					<EdgeLoadingState v-if="archiveAudit.loading" message="Checking issued Report Card payloads and PDFs..." :skeleton="true" />
					<EdgeErrorState
						v-else-if="archiveAudit.error"
						title="Archive integrity check failed"
						:message="archiveAudit.error"
						action-label="Try again"
						@retry="loadArchiveAudit(false)"
					/>
					<template v-else>
						<EdgeDashboardLayout min-column-width="10rem">
							<EdgeStatCard label="Checked" :value="archiveAudit.summary.checked || 0" helper="Visible audit page" />
							<EdgeStatCard label="Healthy" :value="archiveAudit.summary.healthy || 0" helper="Payload and PDF verified" />
							<EdgeStatCard label="Needs Attention" :value="archiveAudit.summary.needs_attention || 0" helper="Payload or PDF integrity failure" />
							<EdgeStatCard label="Legacy" :value="archiveAudit.summary.legacy || 0" helper="Payload verified; predates PDF archival" />
						</EdgeDashboardLayout>
						<p class="eduedge-archive-scope-note">
							{{ archiveAudit.scope_note }}
							<template v-if="archiveAudit.checked_on"> Checked {{ displayValue(archiveAudit.checked_on) }} by {{ archiveAudit.checked_by || 'current user' }}.</template>
						</p>
						<EdgeEmptyState
							v-if="!archiveAudit.rows.length"
							title="No issued report cards in this scope"
							description="There are no permission-visible Report Card Issues to verify on this page."
						/>
						<div v-else class="eduedge-resource-table-wrap">
							<table class="table eduedge-resource-table eduedge-archive-table">
								<thead>
									<tr>
										<th>Issue</th>
										<th>Student</th>
										<th>Publication</th>
										<th>Branch</th>
										<th>Overall</th>
										<th>Payload</th>
										<th>PDF</th>
										<th>Size</th>
										<th>Issued</th>
										<th>Actions</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="row in archiveAudit.rows" :key="row.name">
										<td>
											<strong>{{ row.name }}</strong>
											<small>Issue v{{ row.issue_version || 1 }} · Payload {{ row.payload_fingerprint || 'No fingerprint' }} · PDF {{ row.pdf_fingerprint || 'Legacy / unavailable' }}</small>
										</td>
										<td>{{ row.student_name || row.student }}</td>
										<td>{{ row.result_publication }} · v{{ row.publication_version || 1 }}</td>
										<td>{{ row.school_branch }}</td>
										<td>
											<EdgeStatusBadge :label="row.archive_status" :status="row.archive_status" :tone="archiveTone(row.archive_status)" />
											<small>{{ row.archive_detail }}</small>
										</td>
										<td>
											<EdgeStatusBadge :label="row.payload_status || 'Unknown'" :status="row.payload_status || 'unknown'" :tone="archiveTone(row.payload_status)" />
										</td>
										<td>
											<EdgeStatusBadge :label="row.pdf_status || 'Unknown'" :status="row.pdf_status || 'unknown'" :tone="archiveTone(row.pdf_status)" />
										</td>
										<td>{{ formatArchiveSize(row.actual_size_bytes ?? row.expected_size_bytes) }}</td>
										<td>{{ displayValue(row.issued_on) }}</td>
										<td>
											<div class="eduedge-resource-actions">
												<button
													v-if="row.archive_ok"
													type="button"
													class="edge-button"
													@click="downloadArchiveIssue(row)"
												>
													Download PDF
												</button>
												<button type="button" class="edge-button" @click="openArchiveIssue(row)">Open Issue</button>
											</div>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
						<div class="eduedge-resource-pagination">
							<button type="button" class="edge-button" :disabled="archiveAudit.start <= 0" @click="previousArchivePage">Previous</button>
							<span>Archive page {{ archivePage }}</span>
							<button type="button" class="edge-button" :disabled="!archiveAudit.has_more" @click="nextArchivePage">Next</button>
						</div>
					</template>
				</section>

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
							{{ page.create_label || `Add ${singularTitle}` }}
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
										<EdgeStatusBadge
											v-else-if="column.type === 'DocStatus'"
											:label="docStatusLabel(row[column.fieldname])"
											:status="docStatusLabel(row[column.fieldname])"
											:tone="docStatusTone(row[column.fieldname])"
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
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";
import { openNativeResourceDialog } from "../eduedge_ui/resource_modal";

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
			archiveAudit: {
				loading: false,
				error: "",
				branch: "",
				publication: "",
				student: "",
				search: "",
				checked_on: "",
				checked_by: "",
				allowed_branches: [],
				rows: [],
				summary: { checked: 0, healthy: 0, needs_attention: 0, legacy: 0 },
				scope_note: "",
				start: 0,
				page_length: 10,
				has_more: false,
			},
			page: {
				title: "",
				singular_title: "",
				eyebrow: "",
				subtitle: "",
				columns: [],
				rows: [],
				filters: [],
				start: 0,
				page_length: 20,
				has_more: false,
				quick_create: true,
				quick_edit: true,
				create_route: "",
				create_label: "",
				permissions: { can_create: false, can_write: false, can_delete: false },
			},
		};
	},
	computed: {
		singularTitle() {
			return String(this.page.singular_title || "Record");
		},
		currentPage() {
			return Math.floor((this.page.start || 0) / (this.page.page_length || 20)) + 1;
		},
		archivePage() {
			return Math.floor((this.archiveAudit.start || 0) / (this.archiveAudit.page_length || 10)) + 1;
		},
		activeBranchLabel() {
			const branchFilter = this.page.filters.find((field) => field.type === "Branch");
			const selected = branchFilter ? this.filterValues[branchFilter.fieldname] : "";
			const option = this.normalizedOptions(branchFilter?.options).find((item) => item.value === selected);
			return option?.label || "All permitted branches";
		},
		schoolIdentity() {
			return frappe.boot?.eduedge_ui_identity?.school || {};
		},
	},
	mounted() {
		this.loadPage(true);
		if (this.resourceKey === "result_audit") this.loadArchiveAudit(true);
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
		docStatusLabel(value) {
			const status = Number(value);
			return status === 1 ? "Submitted" : status === 2 ? "Cancelled" : "Draft";
		},
		docStatusTone(value) {
			const status = Number(value);
			return status === 1 ? "success" : status === 2 ? "danger" : "warning";
		},
		archiveTone(status) {
			if (status === "Healthy") return "success";
			if (status === "Legacy") return "neutral";
			return "danger";
		},
		formatArchiveSize(value) {
			const bytes = Number(value || 0);
			if (!bytes) return "—";
			if (bytes < 1024) return `${bytes} B`;
			if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
			return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
		},
		async loadArchiveAudit(resetStart = false) {
			if (this.resourceKey !== "result_audit") return;
			if (resetStart) this.archiveAudit.start = 0;
			this.archiveAudit.loading = true;
			this.archiveAudit.error = "";
			try {
				const response = await frappe.call("eduedge.api.report_card_archive_audit.get_report_card_archive_integrity", {
					branch: this.archiveAudit.branch || undefined,
					publication: this.archiveAudit.publication || undefined,
					student: this.archiveAudit.student || undefined,
					search: this.archiveAudit.search || undefined,
					start: this.archiveAudit.start || 0,
					page_length: this.archiveAudit.page_length || 10,
				});
				const next = response.message || {};
				this.archiveAudit = {
					...this.archiveAudit,
					...next,
					...(next.filters || {}),
					loading: false,
					error: "",
				};
			} catch (error) {
				this.archiveAudit.error = error?.message || "Archived report PDFs could not be checked.";
				this.archiveAudit.loading = false;
			}
		},
		applyArchiveFilters() {
			this.loadArchiveAudit(true);
		},
		resetArchiveFilters() {
			this.archiveAudit.branch = "";
			this.archiveAudit.publication = "";
			this.archiveAudit.student = "";
			this.archiveAudit.search = "";
			this.loadArchiveAudit(true);
		},
		csvEvidenceCell(value) {
			let text = value === undefined || value === null ? "" : String(value);
			if (/^[=+\-@]/.test(text)) text = `'${text}`;
			return `"${text.replace(/"/g, '""')}"`;
		},
		exportArchiveEvidence() {
			if (!this.archiveAudit.rows.length) return;
			const headers = [
				"Checked On", "Checked By", "Issue", "Student", "Student Name", "Branch",
				"Publication", "Publication Version", "Issue Version", "Issued On",
				"Overall Status", "Payload Status", "Payload Fingerprint",
				"PDF Status", "PDF Fingerprint", "Expected PDF Bytes", "Actual PDF Bytes", "Detail",
			];
			const rows = this.archiveAudit.rows.map((row) => [
				this.archiveAudit.checked_on,
				this.archiveAudit.checked_by,
				row.name,
				row.student,
				row.student_name,
				row.school_branch,
				row.result_publication,
				row.publication_version,
				row.issue_version,
				row.issued_on,
				row.archive_status,
				row.payload_status,
				row.payload_fingerprint,
				row.pdf_status,
				row.pdf_fingerprint,
				row.expected_size_bytes,
				row.actual_size_bytes,
				row.archive_detail,
			]);
			const csv = [headers, ...rows]
				.map((row) => row.map((value) => this.csvEvidenceCell(value)).join(","))
				.join("\r\n");
			const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			const day = String(this.archiveAudit.checked_on || "").slice(0, 10) || "current";
			link.href = url;
			link.download = `eduedge-issued-report-integrity-${day}.csv`;
			document.body.appendChild(link);
			link.click();
			link.remove();
			URL.revokeObjectURL(url);
		},
		previousArchivePage() {
			this.archiveAudit.start = Math.max(0, (this.archiveAudit.start || 0) - (this.archiveAudit.page_length || 10));
			this.loadArchiveAudit(false);
		},
		nextArchivePage() {
			if (!this.archiveAudit.has_more) return;
			this.archiveAudit.start = (this.archiveAudit.start || 0) + (this.archiveAudit.page_length || 10);
			this.loadArchiveAudit(false);
		},
		downloadArchiveIssue(row) {
			if (!row?.name) return;
			open_url_post("/api/method/eduedge.api.report_cards.download_report_card_issue", { issue: row.name }, true);
		},
		openArchiveIssue(row) {
			if (!row?.name) return;
			window.open(`/app/eduedge-report-card-issue/${encodeURIComponent(row.name)}`, "_blank", "noopener,noreferrer");
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
		async openCreate() {
			if (!this.page.quick_create && this.page.create_route) {
				window.location.href = this.page.create_route;
				return;
			}
			await openNativeResourceDialog({
				resource: this.resourceKey,
				context: this.modalContext(),
				onSaved: async () => {
					await this.loadPage(true);
					frappe.show_alert({ message: __("Record saved"), indicator: "green" });
				},
			});
		},
		async openEdit(row) {
			if (!this.page.quick_edit) {
				this.openFullForm(row);
				return;
			}
			await openNativeResourceDialog({
				resource: this.resourceKey,
				name: row.name,
				onSaved: async () => {
					await this.loadPage(false);
					frappe.show_alert({ message: __("Record saved"), indicator: "green" });
				},
			});
		},
		openFullForm(row) {
			const route = `${this.page.full_form_route || ""}/${encodeURIComponent(row.name)}`;
			window.open(route, "_blank", "noopener,noreferrer");
		},
		requestDelete(row) {
			const label = row[this.page.title_field] || row.name;
			frappe.confirm(
				__(`Delete ${label}? This uses normal Frappe permissions and linked-record validation.`),
				async () => {
					try {
						await frappe.call("eduedge.api.resource_center.delete_resource_record", {
							resource: this.resourceKey,
							name: row.name,
						});
						await this.loadPage(false);
						frappe.show_alert({ message: __("Record deleted"), indicator: "green" });
					} catch (error) {
						frappe.msgprint({
							title: __("Record could not be deleted"),
							message: error?.message || __("The record could not be deleted."),
							indicator: "red",
						});
					}
				}
			);
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
.eduedge-archive-controls { display:flex; flex-wrap:wrap; gap:.5rem; align-items:end; }
.eduedge-archive-controls .form-control { min-width:14rem; flex:1 1 14rem; }
.eduedge-archive-scope-note { color:var(--text-muted); margin:.75rem 0; }
.eduedge-archive-table td { vertical-align:top; }
.eduedge-archive-table td strong, .eduedge-archive-table td small { display:block; }
.eduedge-archive-table td small { color:var(--text-muted); margin-top:.2rem; max-width:20rem; white-space:normal; }
.edge-button--danger { border-color: var(--red-500, #d64545); color: var(--red-600, #b42318); }
@media (max-width: 47.99rem) {
	.eduedge-resource-panel__heading { flex-direction: column; }
	.eduedge-resource-pagination { justify-content: space-between; }
}
</style>
