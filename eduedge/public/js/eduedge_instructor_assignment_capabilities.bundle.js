import InstructorAssignmentCapabilityDialog from "./eduedge_ui/components/InstructorAssignmentCapabilityDialog.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const ADMIN_STATE_METHOD = "eduedge.api.instructor_assignment_capabilities.get_instructor_assignment_capability_admin_states";
const capabilityBusy = new WeakMap();

export function createEduEdgeInstructorAssignmentCapabilityApp(rootProps = null) {
	return createEduEdgeApp(InstructorAssignmentCapabilityDialog, rootProps);
}

function capabilityCount(item) {
	return Object.values(item?.capabilities || {}).filter((value) => Number(value || 0)).length;
}

function openCapabilityDialog({ item, onBusy, onComplete }) {
	if (!item?.name) return null;
	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-capability-host";
	document.body.appendChild(host);

	let app = null;
	let closed = false;
	const cleanup = () => {
		if (closed) return;
		closed = true;
		window.setTimeout(() => {
			try { app?.unmount?.(); } finally { host.remove(); }
		}, 0);
	};

	app = createEduEdgeInstructorAssignmentCapabilityApp({
		item,
		onBusy,
		onComplete,
		onClosed: cleanup,
	});
	app.mount(host);
	return { app, host, close: cleanup };
}

async function loadCapabilityStates(proxy) {
	const assignments = proxy.data?.assignments || [];
	if (!assignments.length || !proxy.canManage) return;
	try {
		const response = await frappe.call(ADMIN_STATE_METHOD, {
			names: JSON.stringify(assignments.map((item) => item.name)),
		});
		const states = response.message?.states || {};
		proxy.data.assignments = assignments.map((item) => ({
			...item,
			...(states[item.name] || {
				can_manage_capabilities: false,
				capabilities: {},
				capability_version: "",
			}),
		}));
	} catch (error) {
		console.error("Instructor Assignment capability state could not load", error);
		proxy.data.assignments = assignments.map((item) => ({
			...item,
			can_manage_capabilities: false,
			capabilities: {},
			capability_version: "",
			capability_state_unavailable: true,
		}));
	}
}

function syncCapabilityActions(proxy) {
	if (!proxy?.loaded) return;
	const root = document.querySelector(".eduedge-instructor-assignments-root");
	if (!root) return;
	const cards = root.querySelectorAll(".register-list > article");
	const assignments = proxy.data?.assignments || [];
	cards.forEach((card, index) => {
		const item = assignments[index];
		if (!item) return;
		const actions = card.querySelector(":scope > .assignment-actions");
		if (!actions) return;

		let button = actions.querySelector("[data-eduedge-assignment-capabilities]");
		const allowed = Boolean(proxy.canManage && item.can_manage_capabilities && item.capability_version);
		if (!allowed) {
			button?.remove();
			return;
		}
		if (!button) {
			button = document.createElement("button");
			button.type = "button";
			button.className = "edge-button";
			button.dataset.eduedgeAssignmentCapabilities = "1";
			const openButton = actions.querySelector("button:last-of-type");
			if (openButton) actions.insertBefore(button, openButton);
			else actions.appendChild(button);
			button.addEventListener("click", () => {
				const currentItem = (proxy.data?.assignments || []).find((row) => row.name === item.name);
				if (!currentItem?.can_manage_capabilities || !currentItem?.capability_version) return;
				openCapabilityDialog({
					item: currentItem,
					onBusy: (name) => {
						capabilityBusy.set(proxy, name || "");
						syncCapabilityActions(proxy);
					},
					onComplete: async () => {
						await proxy.load?.();
					},
				});
			});
		}
		const busy = capabilityBusy.get(proxy) === item.name;
		button.disabled = busy;
		const count = capabilityCount(item);
		button.textContent = busy ? __("Saving capabilities...") : count ? `Capabilities (${count})` : __("Capabilities");
	});
}

function install(component) {
	if (!component || component.__eduedgeAssignmentCapabilitiesInstalled) return;
	component.__eduedgeAssignmentCapabilitiesInstalled = true;
	const methods = component.methods || (component.methods = {});
	const existingLoad = methods.load;
	if (typeof existingLoad !== "function") return;

	methods.load = async function (...args) {
		const result = await existingLoad.apply(this, args);
		await loadCapabilityStates(this);
		await this.$nextTick?.();
		syncCapabilityActions(this);
		return result;
	};
}

export function installInstructorAssignmentCapabilities(component = window.EduEdgeInstructorAssignments) {
	install(component);
}

installInstructorAssignmentCapabilities(window.EduEdgeInstructorAssignments);
window.createEduEdgeInstructorAssignmentCapabilityApp = createEduEdgeInstructorAssignmentCapabilityApp;
window.installInstructorAssignmentCapabilities = installInstructorAssignmentCapabilities;
