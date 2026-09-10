const TERMINOLOGY_METHOD = "eduedge.api.academic_foundation_editor.get_institution_terminology";
const CALENDAR_EDITOR_METHOD = "eduedge.api.academic_foundation_editor.get_academic_calendar_editor";
const CALENDAR_SAVE_METHOD = "eduedge.api.academic_foundation_editor.save_academic_calendar";
const CANONICAL_TEXT = Symbol("eduedgeAcademicFoundationCanonicalText");

function messageFromError(error, fallback) {
	return error?.message || error?._server_messages || error?.exc_type || fallback;
}

function termFromContext(context, key, plural = false, fallback = "") {
	const row = context?.terms?.[key] || {};
	return row[plural ? "plural" : "singular"] || fallback;
}

function selectedContext(vm) {
	return vm.selectedInstitutionTerminology?.terms
		? vm.selectedInstitutionTerminology
		: vm.activeContext || {};
}

function selectedTerm(vm, key, plural = false, fallback = "") {
	return termFromContext(selectedContext(vm), key, plural, fallback);
}

function translateFoundationText(value, vm) {
	const section = selectedTerm(vm, "academic_section", false, "Academic Section");
	const sections = selectedTerm(vm, "academic_section", true, "Academic Sections");
	const level = selectedTerm(vm, "academic_level", false, "Academic Level");
	const levels = selectedTerm(vm, "academic_level", true, "Academic Levels");
	const academicYears = selectedTerm(vm, "academic_year", true, "Academic Years");
	const academicTerm = selectedTerm(vm, "academic_term", false, "Academic Term");
	const academicTerms = selectedTerm(vm, "academic_term", true, "Academic Terms");

	let next = String(value || "");
	const replacements = [
		["Years and periods", `${academicYears} and ${academicTerms}`],
		["Current period", `Current ${academicTerm}`],
		["Academic Level(s)", levels],
		["Academic Sections", sections],
		["Academic Section", section],
		["Academic Levels", levels],
		["Academic Level", level],
		["Academic Periods", academicTerms],
		["Academic Period", academicTerm],
		["add its periods", `add its ${academicTerms.toLowerCase()}`],
		["progression levels", `${levels.toLowerCase()}`],
	];
	for (const [from, to] of replacements) next = next.split(from).join(to);
	next = next.replace(
		/(\d+)\s+sections\s+·\s+(\d+)\s+levels/gi,
		(_match, sectionCount, levelCount) =>
			`${sectionCount} ${sections.toLowerCase()} · ${levelCount} ${levels.toLowerCase()}`
	);
	next = next.replace(
		/(\d+)\s+level\(s\)/gi,
		(_match, count) => `${count} ${Number(count) === 1 ? level : levels}`
	);
	return next;
}

function applySelectedTerminology(vm) {
	const root = vm?.$el;
	if (!root || !vm.selectedInstitution) return;
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
		acceptNode(node) {
			const parent = node.parentElement;
			if (!parent || !node.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
			if (parent.closest("script, style, textarea, input, select, option, code, pre, [contenteditable='true']")) {
				return NodeFilter.FILTER_REJECT;
			}
			return NodeFilter.FILTER_ACCEPT;
		},
	});
	const nodes = [];
	while (walker.nextNode()) nodes.push(walker.currentNode);
	for (const node of nodes) {
		if (node[CANONICAL_TEXT] === undefined) node[CANONICAL_TEXT] = node.nodeValue;
		const translated = translateFoundationText(node[CANONICAL_TEXT], vm);
		if (translated !== node.nodeValue) node.nodeValue = translated;
	}
}

function scheduleTerminology(vm) {
	if (!vm || vm.__eduedgeFoundationTerminologyScheduled) return;
	vm.__eduedgeFoundationTerminologyScheduled = true;
	requestAnimationFrame(() => {
		vm.__eduedgeFoundationTerminologyScheduled = false;
		applySelectedTerminology(vm);
	});
}

async function refreshSelectedTerminology(vm) {
	const institution = vm.selectedInstitution;
	if (!institution) {
		vm.selectedInstitutionTerminology = {};
		return;
	}
	try {
		const response = await frappe.call(TERMINOLOGY_METHOD, { institution });
		if (institution !== vm.selectedInstitution) return;
		vm.selectedInstitutionTerminology = response.message || {};
		vm.$forceUpdate?.();
		vm.$nextTick?.(() => scheduleTerminology(vm));
	} catch (error) {
		vm.selectedInstitutionTerminology = {};
		frappe.show_alert({
			message: messageFromError(error, __("Institution terminology could not be loaded.")),
			indicator: "orange",
		});
	}
}

function installDialogStyle() {
	if (document.getElementById("eduedge-academic-calendar-dialog-style")) return;
	const style = document.createElement("style");
	style.id = "eduedge-academic-calendar-dialog-style";
	style.textContent = `
		.eduedge-academic-calendar-dialog .modal-dialog { max-width: min(72rem, 96vw); }
		.eduedge-academic-calendar-dialog .modal-content { border-radius: var(--edge-radius-lg, 12px); }
		.eduedge-calendar-dialog-guidance { padding:.75rem; margin-bottom:.5rem; border:1px solid var(--border-color); border-radius:var(--edge-radius-md,8px); background:var(--control-bg); color:var(--text-muted); }
	`;
	document.head.appendChild(style);
}

function calendarPeriodRows(dialog) {
	const grid = dialog.fields_dict?.periods?.grid;
	const rows = grid?.get_data?.() || dialog.get_value("periods") || [];
	return rows
		.filter((row) => row && !row.__deleted)
		.map((row, index) => ({
			academic_term: row.academic_term || "",
			start_date: row.start_date || "",
			end_date: row.end_date || "",
			sequence: Number(row.sequence) || (index + 1) * 10,
			result_publication_date: row.result_publication_date || "",
		}));
}

async function openCalendarEditor(vm, calendar = null) {
	if (!frappe.ui?.Dialog) {
		frappe.msgprint(__("Calendar dialog services are unavailable."));
		return;
	}
	let editor;
	try {
		const response = await frappe.call(CALENDAR_EDITOR_METHOD, {
			institution: vm.selectedInstitution || undefined,
			calendar: calendar?.name || undefined,
		});
		editor = response.message || {};
	} catch (error) {
		frappe.msgprint({
			title: __("Academic calendar could not load"),
			message: messageFromError(error, __("The calendar editor could not be opened.")),
			indicator: "red",
		});
		return;
	}

	const values = editor.values || {};
	const context = editor.terminology || selectedContext(vm);
	const yearLabel = termFromContext(context, "academic_year", false, "Academic Year");
	const termLabel = termFromContext(context, "academic_term", false, "Academic Term");
	const termsLabel = termFromContext(context, "academic_term", true, "Academic Terms");
	const isNew = Boolean(editor.is_new);
	let dialog;
	const periodFields = [
		{
			fieldname: "academic_term",
			fieldtype: "Link",
			label: termLabel,
			options: "Academic Term",
			reqd: 1,
			in_list_view: 1,
			get_query: () => ({ filters: { academic_year: dialog?.get_value("academic_year") || "" } }),
		},
		{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"), reqd: 1, in_list_view: 1 },
		{ fieldname: "end_date", fieldtype: "Date", label: __("End Date"), reqd: 1, in_list_view: 1 },
		{ fieldname: "sequence", fieldtype: "Int", label: __("Sequence"), default: 10, in_list_view: 1 },
		{ fieldname: "result_publication_date", fieldtype: "Date", label: __("Result Publication Date"), in_list_view: 1 },
	];

	dialog = new frappe.ui.Dialog({
		title: isNew ? __("New Institution Academic Calendar") : __("Edit Institution Academic Calendar"),
		size: "extra-large",
		fields: [
			{
				fieldname: "guidance",
				fieldtype: "HTML",
				options: `<div class="eduedge-calendar-dialog-guidance">${frappe.utils.escape_html(
					__("Maintain the Institution calendar here. Date overlap, current-calendar switching, Academic Year ownership, and submitted-record safety remain server validated.")
				)}</div>`,
			},
			{ fieldname: "institution_label", fieldtype: "Data", label: __("Institution"), read_only: 1, default: context.institution_name || values.institution },
			{ fieldname: "academic_year", fieldtype: "Link", label: yearLabel, options: "Academic Year", reqd: 1, read_only: !isNew, default: values.academic_year || "" },
			{ fieldtype: "Column Break" },
			{ fieldname: "is_current", fieldtype: "Check", label: __("Current Calendar"), default: Number(values.is_current || 0) },
			{ fieldname: "enabled", fieldtype: "Check", label: __("Enabled"), default: values.enabled === undefined ? 1 : Number(values.enabled) },
			{ fieldtype: "Section Break", label: __("Calendar Dates") },
			{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date"), reqd: 1, default: values.start_date || "" },
			{ fieldtype: "Column Break" },
			{ fieldname: "end_date", fieldtype: "Date", label: __("End Date"), reqd: 1, default: values.end_date || "" },
			{ fieldtype: "Section Break", label: termsLabel },
			{
				fieldname: "periods",
				fieldtype: "Table",
				label: termsLabel,
				cannot_add_rows: false,
				cannot_delete_rows: false,
				in_place_edit: true,
				data: values.periods || [],
				fields: periodFields,
			},
			{ fieldtype: "Section Break", label: __("Notes") },
			{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes"), default: values.notes || "" },
		],
		primary_action_label: editor.can_save === false ? undefined : __("Save Calendar"),
		primary_action: editor.can_save === false
			? undefined
			: async () => {
				const formValues = dialog.get_values();
				if (!formValues) return;
				dialog.disable_primary_action();
				try {
					await frappe.call(CALENDAR_SAVE_METHOD, {
						calendar: values.name || undefined,
						institution: values.institution || vm.selectedInstitution,
						academic_year: formValues.academic_year,
						is_current: formValues.is_current ? 1 : 0,
						enabled: formValues.enabled ? 1 : 0,
						start_date: formValues.start_date,
						end_date: formValues.end_date,
						periods: JSON.stringify(calendarPeriodRows(dialog)),
						notes: formValues.notes || "",
					});
					dialog.hide();
					frappe.show_alert({ message: __("Institution Academic Calendar saved"), indicator: "green" });
					await vm.load();
				} catch (error) {
					frappe.msgprint({
						title: __("Calendar could not be saved"),
						message: messageFromError(error, __("The Institution Academic Calendar could not be saved.")),
						indicator: "red",
					});
				} finally {
					dialog.enable_primary_action();
				}
			},
		secondary_action_label: editor.full_form_route ? __("Open Advanced Form") : undefined,
		secondary_action: editor.full_form_route
			? () => window.open(editor.full_form_route, "_blank", "noopener,noreferrer")
			: undefined,
	});
	installDialogStyle();
	dialog.$wrapper?.addClass("eduedge-academic-calendar-dialog");
	dialog.show();
}

function wrapLifecycle(component, hookName, callback) {
	const original = component[hookName];
	component[hookName] = function wrappedLifecycle(...args) {
		const result = typeof original === "function" ? original.apply(this, args) : undefined;
		callback.call(this);
		return result;
	};
}

export function installAcademicFoundationQaFixes(component) {
	if (!component || component.__eduedgeAcademicFoundationQaFixed) return component;
	component.__eduedgeAcademicFoundationQaFixed = true;
	const originalData = component.data;
	component.data = function patchedData() {
		return {
			...(typeof originalData === "function" ? originalData.call(this) : {}),
			selectedInstitutionTerminology: {},
		};
	};

	const originalLoad = component.methods?.load;
	const originalInstitutionChanged = component.methods?.institutionChanged;
	component.methods = component.methods || {};
	component.methods.term = function selectedInstitutionTerm(key, plural = false, fallback = "") {
		return selectedTerm(this, key, plural, fallback);
	};
	component.methods.load = async function patchedLoad(...args) {
		const result = await originalLoad?.apply(this, args);
		await refreshSelectedTerminology(this);
		return result;
	};
	component.methods.institutionChanged = async function patchedInstitutionChanged(...args) {
		const result = await originalInstitutionChanged?.apply(this, args);
		this.selectedInstitutionTerminology = {};
		await refreshSelectedTerminology(this);
		return result;
	};
	component.methods.createCalendar = function createCalendarInEdgeSuiteDialog() {
		if (!this.selectedInstitution || !this.data.permissions.can_create_calendar) return;
		return openCalendarEditor(this);
	};
	component.methods.editCalendar = function editCalendarInEdgeSuiteDialog(calendar) {
		if (!calendar?.name || !this.data.permissions.can_write_calendar) return;
		return openCalendarEditor(this, calendar);
	};

	wrapLifecycle(component, "mounted", function mountedTerminologyFix() {
		this.$nextTick?.(() => {
			if (!this.__eduedgeFoundationObserver && this.$el) {
				this.__eduedgeFoundationObserver = new MutationObserver(() => scheduleTerminology(this));
				this.__eduedgeFoundationObserver.observe(this.$el, { childList: true, subtree: true, characterData: true });
			}
			scheduleTerminology(this);
		});
	});
	wrapLifecycle(component, "updated", function updatedTerminologyFix() {
		scheduleTerminology(this);
	});
	const originalBeforeUnmount = component.beforeUnmount;
	component.beforeUnmount = function patchedBeforeUnmount(...args) {
		this.__eduedgeFoundationObserver?.disconnect();
		this.__eduedgeFoundationObserver = null;
		return typeof originalBeforeUnmount === "function" ? originalBeforeUnmount.apply(this, args) : undefined;
	};
	return component;
}
