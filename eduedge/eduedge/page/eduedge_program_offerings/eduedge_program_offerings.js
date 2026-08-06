frappe.pages["eduedge-program-offerings"].on_page_load = function (wrapper) {
	wrapper.page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Programme Offerings"),
		single_column: true,
	});
};

function selected_offering_context(wrapper) {
	const proxy = wrapper.vue_app?._instance?.proxy;
	const draft = proxy?.draft || {};
	const filters = proxy?.filters || {};
	return {
		branch: draft.school_branch || filters.branch || "",
		offering: draft.name || "",
		offering_title: draft.offering_title || draft.name || "",
		institution_context: proxy?.draftContext || proxy?.activeContext || {},
	};
}

function require_selected_offering(wrapper) {
	const context = selected_offering_context(wrapper);
	if (!context.offering) {
		frappe.msgprint({
			title: __("Select a Class / Programme Offering"),
			message: __("Select an existing Class / Programme Offering card before reviewing or managing its curriculum."),
			indicator: "orange",
		});
		return null;
	}
	if (!context.branch) {
		frappe.msgprint({
			title: __("Branch context required"),
			message: __("The selected Class / Programme Offering does not have a usable Branch / Campus context."),
			indicator: "red",
		});
		return null;
	}
	return context;
}

function curriculum_route(context) {
	const params = new URLSearchParams();
	params.set("branch", context.branch);
	params.set("offering", context.offering);
	return `/app/eduedge-curriculum?${params.toString()}`;
}

function open_offering_operation(wrapper, route, options = {}) {
	const context = options.require_offering === false
		? selected_offering_context(wrapper)
		: require_selected_offering(wrapper);
	if (!context) return;
	const params = new URLSearchParams();
	if (context.branch) params.set("branch", context.branch);
	if (context.offering) params.set("offering", context.offering);
	window.location.href = `${route}${params.toString() ? `?${params.toString()}` : ""}`;
}

function curriculum_terms(context) {
	const term = frappe.eduedge?.term;
	return {
		singular: term?.("course", {
			plural: false,
			context: context.institution_context,
			fallback: "Subject / Course",
		}) || "Subject / Course",
		plural: term?.("course", {
			plural: true,
			context: context.institution_context,
			fallback: "Subjects / Courses",
		}) || "Subjects / Courses",
	};
}

function curriculum_review_html(courses, terms) {
	if (!courses.length) {
		return `
			<div class="text-muted" style="padding:1rem 0;">
				<strong>${__(`No configured ${terms.plural.toLowerCase()}`)}</strong>
				<div>${__("Use Manage Curriculum to add Institution subjects to this Class / Programme.")}</div>
			</div>
		`;
	}
	const rows = courses.map((course) => `
		<tr>
			<td><strong>${frappe.utils.escape_html(course.course_name || course.name || "")}</strong></td>
			<td>${frappe.utils.escape_html(course.department || __("Not assigned"))}</td>
			<td>${frappe.utils.escape_html(course.default_grading_scale || __("No default"))}</td>
		</tr>
	`).join("");
	return `
		<div style="display:flex;justify-content:space-between;gap:.75rem;align-items:center;margin-bottom:.75rem;">
			<span class="text-muted">${courses.length} ${frappe.utils.escape_html(courses.length === 1 ? terms.singular : terms.plural)} configured for the selected Class / Programme.</span>
		</div>
		<div class="table-responsive">
			<table class="table table-bordered table-hover">
				<thead>
					<tr>
						<th>${frappe.utils.escape_html(terms.singular)}</th>
						<th>${__("Department / School Section")}</th>
						<th>${__("Default Grading Scale")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		</div>
	`;
}

async function review_selected_curriculum(wrapper) {
	const context = require_selected_offering(wrapper);
	if (!context) return;
	const terms = curriculum_terms(context);
	try {
		const response = await frappe.call({
			method: "eduedge.api.curriculum_management.get_curriculum_page",
			args: {
				branch: context.branch,
				program_offering: context.offering,
				start: 0,
				page_length: 100,
			},
			freeze: true,
			freeze_message: __(`Loading ${terms.plural.toLowerCase()}...`),
		});
		const courses = response.message?.courses || [];
		const dialog = new frappe.ui.Dialog({
			title: __(`Class Curriculum — ${context.offering_title || context.offering}`),
			size: "large",
			fields: [{ fieldtype: "HTML", fieldname: "curriculum_review" }],
			primary_action_label: __("Manage Curriculum"),
			primary_action() {
				dialog.hide();
				window.location.href = curriculum_route(context);
			},
		});
		dialog.fields_dict.curriculum_review.$wrapper.html(curriculum_review_html(courses, terms));
		dialog.show();
	} catch (error) {
		frappe.msgprint({
			title: __("Curriculum could not load"),
			message: frappe.utils.escape_html(error?.message || String(error)),
			indicator: "red",
		});
	}
}

function ensure_curriculum_bridge_styles() {
	if (document.querySelector("style[data-eduedge-offering-curriculum-bridge]")) return;
	const style = document.createElement("style");
	style.setAttribute("data-eduedge-offering-curriculum-bridge", "1");
	style.textContent = `
		.eduedge-offering-curriculum-bridge{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding:.85rem 1rem;margin-bottom:1rem;border:1px solid var(--border-color);border-radius:12px;background:var(--card-bg)}
		.eduedge-offering-curriculum-bridge__copy{display:grid;gap:.2rem}.eduedge-offering-curriculum-bridge__copy span{color:var(--text-muted);font-size:.82rem}
		.eduedge-offering-curriculum-bridge__actions{display:flex;gap:.5rem;flex-wrap:wrap}
	`;
	document.head.appendChild(style);
}

function add_visible_curriculum_bridge(wrapper, root) {
	ensure_curriculum_bridge_styles();
	const panel = $(
		`<section class="eduedge-offering-curriculum-bridge">
			<div class="eduedge-offering-curriculum-bridge__copy">
				<strong>${__("Class Curriculum")}</strong>
				<span>${__("Select an existing Class / Programme Offering, then review or manage its configured Subjects / Courses.")}</span>
			</div>
			<div class="eduedge-offering-curriculum-bridge__actions">
				<button type="button" class="edge-button" data-action="review-curriculum">${__("Review Subjects / Courses")}</button>
				<button type="button" class="edge-button edge-button--primary" data-action="manage-curriculum">${__("Manage Curriculum")}</button>
			</div>
		</section>`
	);
	panel.find('[data-action="review-curriculum"]').on("click", () => review_selected_curriculum(wrapper));
	panel.find('[data-action="manage-curriculum"]').on("click", () => {
		const context = require_selected_offering(wrapper);
		if (context) window.location.href = curriculum_route(context);
	});
	panel.insertBefore(root);
}

function add_offering_operation_buttons(wrapper) {
	const page = wrapper.page;
	page.clear_inner_toolbar?.();
	page.add_inner_button(
		__("Review Curriculum"),
		() => review_selected_curriculum(wrapper),
		__("Class Operations")
	);
	page.add_inner_button(
		__("Manage Curriculum"),
		() => open_offering_operation(wrapper, "/app/eduedge-curriculum"),
		__("Class Operations")
	);
	page.add_inner_button(
		__("Assign Instructors"),
		() => open_offering_operation(wrapper, "/app/eduedge-instructor-assignments"),
		__("Class Operations")
	);
}

frappe.pages["eduedge-program-offerings"].on_page_show = function (wrapper) {
	const page = wrapper.page;
	wrapper.current_visit_id = (wrapper.current_visit_id || 0) + 1;
	const visitId = wrapper.current_visit_id;

	if (wrapper.vue_app) {
		try {
			wrapper.vue_app.unmount();
		} catch (error) {
			console.error("Failed to unmount EduEdge Programme Offerings", error);
		}
		wrapper.vue_app = null;
	}

	$(page.body).empty();
	const $loading = $(
		`<div class="p-6 text-center text-muted">${__("Loading Programme Offerings...")}</div>`
	).appendTo(page.body);

	const fail = (message) => {
		$loading.remove();
		$(
			`<div class="alert alert-danger p-6 text-center">
				<strong>${__("Programme Offerings failed to load")}</strong>
				<div>${frappe.utils.escape_html(message || "")}</div>
			</div>`
		).appendTo(page.body);
	};

	frappe.require("edgesuite_ui.bundle.js", () => {
		if (wrapper.current_visit_id !== visitId) return;
		frappe.require("eduedge_programme_offerings.bundle.js", () => {
			if (wrapper.current_visit_id !== visitId) return;
			if (
				!window.EduEdgeProgrammeOfferings ||
				typeof window.createEduEdgeProgrammeOfferingsApp !== "function"
			) {
				fail(__("The EduEdge Programme Offerings bundle is unavailable or incomplete."));
				return;
			}
			$loading.remove();
			const root = $(
				'<div class="eduedge-programme-offerings-root" data-edge-product="eduedge"></div>'
			).appendTo(page.body);
			try {
				wrapper.vue_app = window.createEduEdgeProgrammeOfferingsApp({
					pageName: "eduedge-program-offerings",
				});
				wrapper.vue_app.mount(root[0]);
				add_visible_curriculum_bridge(wrapper, root);
				add_offering_operation_buttons(wrapper);
			} catch (error) {
				console.error("Failed to mount EduEdge Programme Offerings", error);
				fail(error.message || String(error));
			}
		});
	});
};
