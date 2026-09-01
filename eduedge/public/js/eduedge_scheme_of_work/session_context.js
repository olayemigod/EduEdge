const SESSION_WORKBENCH_METHOD = "eduedge.api.scheme_of_work_session_context.get_scheme_workbench";

const blankData = () => ({
	allowed_branches: [],
	offerings: [],
	academic_years: [],
	terms: [],
	groups: [],
	courses: [],
	topics: [],
	schemes: [],
	selected_term: null,
	filters: {},
	paging: { start: 0, page_length: 25, has_more: false },
	permissions: {},
});

const blankScheme = (filters = {}, offering = null, term = null) => ({
	name: "",
	scheme_title: "",
	status: "Draft",
	version_no: 1,
	supersedes_scheme: "",
	institution: offering?.institution || "",
	school_branch: filters.school_branch || "",
	program_offering: filters.program_offering || "",
	student_group: filters.student_group || "",
	course: filters.course || "",
	academic_year: filters.academic_year || offering?.academic_year || "",
	academic_term: filters.academic_term || offering?.academic_term || "",
	period_start_date: term?.start_date || offering?.period_start_date || "",
	period_end_date: term?.end_date || offering?.period_end_date || "",
	prepared_by: "",
	approved_by: "",
	approved_on: null,
	snapshot_on: null,
	offering_title_snapshot: "",
	student_group_name_snapshot: "",
	course_name_snapshot: "",
	notes: "",
	items: [],
});

function applyRoutePreset(vm) {
	if (typeof window === "undefined") return;
	const params = new URLSearchParams(window.location.search || "");
	const branch = params.get("branch") || params.get("school_branch") || "";
	if (branch) vm.filters.school_branch = branch;
	for (const key of ["academic_year", "program_offering", "academic_term", "student_group", "course", "status"]) {
		const value = params.get(key);
		if (value) vm.filters[key] = value;
	}
}

function syncSessionContextUi(vm) {
	const root = vm?.$el;
	if (!root?.querySelector) return;
	const year = String(vm.filters?.academic_year || "").trim();
	const filterGrid = root.querySelector(".scheme-filters");
	let sessionField = root.querySelector("[data-eduedge-session-context]");
	if (year && filterGrid) {
		if (!sessionField) {
			sessionField = document.createElement("label");
			sessionField.setAttribute("data-eduedge-session-context", "1");
			sessionField.innerHTML = '<span>Academic Session</span><input class="form-control" type="text" readonly />';
			filterGrid.insertBefore(sessionField, filterGrid.children[1] || null);
		}
		const input = sessionField.querySelector("input");
		if (input) input.value = year;
	} else if (sessionField) {
		sessionField.remove();
	}

	let hint = root.querySelector("[data-eduedge-scheme-approval-hint]");
	const needsHint = Boolean(
		vm.draft?.name
		&& vm.draft?.status === "Draft"
		&& vm.data?.permissions?.is_manager
		&& !(vm.draft?.items || []).length
	);
	if (needsHint) {
		if (!hint) {
			hint = document.createElement("p");
			hint.setAttribute("data-eduedge-scheme-approval-hint", "1");
			hint.style.margin = "0";
			hint.style.padding = ".65rem .75rem";
			hint.style.border = "1px solid var(--border-color)";
			hint.style.borderRadius = "8px";
			hint.style.background = "var(--control-bg)";
			hint.style.color = "var(--text-muted)";
			const heading = root.querySelector(".scheme-panel.editor > .scheme-heading");
			heading?.insertAdjacentElement("afterend", hint);
		}
		hint.textContent = "Approval requires at least one Scheme Item. Add a Topic first; when Approve is used, EduEdge saves the current Draft before approval.";
	} else if (hint) {
		hint.remove();
	}
}

export function installSchemeSessionContext(component) {
	if (!component || component.__eduedgeSessionContextInstalled) return component;
	component.__eduedgeSessionContextInstalled = true;

	const originalData = component.data;
	component.data = function sessionAwareData() {
		const state = originalData ? originalData.call(this) : {};
		state.filters = { academic_year: "", ...(state.filters || {}) };
		return state;
	};

	component.mounted = function sessionAwareMounted() {
		applyRoutePreset(this);
		this.load();
	};

	component.updated = function sessionAwareUpdated() {
		syncSessionContextUi(this);
	};

	component.methods = {
		...(component.methods || {}),
		async load(reset = false, selectedName = "") {
			if (reset) this.filters.start = 0;
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call(SESSION_WORKBENCH_METHOD, {
					school_branch: this.filters.school_branch || undefined,
					academic_year: this.filters.academic_year || undefined,
					program_offering: this.filters.program_offering || undefined,
					academic_term: this.filters.academic_term || undefined,
					student_group: this.filters.student_group || undefined,
					course: this.filters.course || undefined,
					status: this.filters.status || undefined,
					start: this.filters.start,
					page_length: this.data.paging?.page_length || 25,
				});
				this.data = response.message || blankData();
				this.filters = { ...this.filters, ...(this.data.filters || {}), start: this.data.paging?.start || 0 };
				this.loaded = true;
				if (selectedName) await this.loadScheme(selectedName);
				else if (!this.draft.name) this.draft = blankScheme(this.filters, this.selectedOffering, this.selectedTerm);
			} catch (error) {
				this.error = error?.message || "Scheme of Work could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async approve() {
			if (!this.draft?.name || this.saving) return;
			if (!(this.draft.items || []).length) {
				frappe.msgprint({
					title: __("Scheme is not ready for approval"),
					message: __("Add at least one Scheme Item before approval."),
					indicator: "orange",
				});
				return;
			}
			await this.save();
			if (this.saveError || !this.draft?.name || this.draft.status !== "Draft") return;
			await this.runAction("eduedge.api.scheme_of_work.approve_scheme", "Scheme of Work approved");
		},
	};

	return component;
}
