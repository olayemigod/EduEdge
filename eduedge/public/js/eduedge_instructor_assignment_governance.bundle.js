import InstructorAssignmentGovernanceDialog from "./eduedge_ui/components/InstructorAssignmentGovernanceDialog.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

const GOVERNANCE_STATE_METHOD = "eduedge.api.instructor_assignment_governance.get_instructor_assignment_governance_states";
const governanceBusy = new WeakMap();

export function createEduEdgeInstructorAssignmentGovernanceApp(rootProps = null) {
	return createEduEdgeApp(InstructorAssignmentGovernanceDialog, rootProps);
}

function openGovernanceDialog({ item, mode, onBusy, onComplete }) {
	if (!item?.name) return null;
	const host = document.createElement("div");
	host.className = "eduedge-instructor-assignment-governance-host";
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

	app = createEduEdgeInstructorAssignmentGovernanceApp({
		item,
		mode,
		onBusy,
		onComplete,
		onClosed: cleanup,
	});
	app.mount(host);
	return { app, host, close: cleanup };
}

async function loadGovernanceStates(proxy) {
	const assignments = proxy.data?.assignments || [];
	if (!assignments.length || !proxy.canManage) return;
	try {
		const response = await frappe.call(GOVERNANCE_STATE_METHOD, {
			names: JSON.stringify(assignments.map((item) => item.name)),
		});
		const states = response.message?.states || {};
		proxy.data.assignments = assignments.map((item) => ({
			...item,
			...(states[item.name] || {
				can_disable: false,
				can_reenable: false,
				can_delete_unused: false,
			}),
		}));
	} catch (error) {
		console.error("Instructor Assignment governance state could not load", error);
		proxy.data.assignments = assignments.map((item) => ({
			...item,
			can_disable: false,
			can_reenable: false,
			can_delete_unused: false,
			governance_unavailable: true,
		}));
	}
}

function actionButton(actions, selector, label, onClick, beforeOpen = true) {
	let button = actions.querySelector(selector);
	if (!button) {
		button = document.createElement("button");
		button.type = "button";
		button.className = "edge-button";
		button.dataset.eduedgeAssignmentGovernance = "1";
		if (selector.includes("disable")) button.dataset.eduedgeDisableAssignment = "1";
		if (selector.includes("reenable")) button.dataset.eduedgeReenableAssignment = "1";
		if (selector.includes("delete")) button.dataset.eduedgeDeleteUnusedAssignment = "1";
		if (beforeOpen) {
			const openButton = actions.querySelector("button:last-of-type");
			if (openButton) actions.insertBefore(button, openButton);
			else actions.appendChild(button);
		} else {
			actions.appendChild(button);
		}
		button.addEventListener("click", onClick);
	}
	button.textContent = label;
	return button;
}

function removeAction(actions, selector) {
	actions.querySelector(selector)?.remove();
}

function openAction(proxy, itemName, mode) {
	const currentItem = (proxy.data?.assignments || []).find((row) => row.name === itemName);
	if (!currentItem) return;
	const allowed = {
		disable: currentItem.can_disable,
		reenable: currentItem.can_reenable,
		delete: currentItem.can_delete_unused,
	};
	if (!allowed[mode]) return;
	openGovernanceDialog({
		item: currentItem,
		mode,
		onBusy: (name) => {
			governanceBusy.set(proxy, name || "");
			syncGovernanceActions(proxy);
		},
		onComplete: async () => {
			await proxy.load?.();
		},
	});
}

function syncGovernanceActions(proxy) {
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
		const busy = governanceBusy.get(proxy) === item.name;

		if (proxy.canManage && item.can_disable) {
			const button = actionButton(
				actions,
				"[data-eduedge-disable-assignment]",
				busy ? __("Updating...") : __("Disable"),
				() => openAction(proxy, item.name, "disable"),
			);
			button.disabled = busy;
		} else {
			removeAction(actions, "[data-eduedge-disable-assignment]");
		}

		if (proxy.canManage && item.can_reenable) {
			const button = actionButton(
				actions,
				"[data-eduedge-reenable-assignment]",
				busy ? __("Updating...") : __("Re-enable"),
				() => openAction(proxy, item.name, "reenable"),
			);
			button.disabled = busy;
		} else {
			removeAction(actions, "[data-eduedge-reenable-assignment]");
		}

		if (proxy.canManage && item.can_delete_unused) {
			const button = actionButton(
				actions,
				"[data-eduedge-delete-unused-assignment]",
				busy ? __("Checking...") : __("Delete Unused"),
				() => openAction(proxy, item.name, "delete"),
			);
			button.disabled = busy;
		} else {
			removeAction(actions, "[data-eduedge-delete-unused-assignment]");
		}
	});
}

function install(component) {
	if (!component || component.__eduedgeAssignmentGovernanceInstalled) return;
	component.__eduedgeAssignmentGovernanceInstalled = true;
	const methods = component.methods || (component.methods = {});
	const existingLoad = methods.load;
	if (typeof existingLoad !== "function") return;

	methods.load = async function (...args) {
		const result = await existingLoad.apply(this, args);
		await loadGovernanceStates(this);
		await this.$nextTick?.();
		syncGovernanceActions(this);
		return result;
	};
}

export function installInstructorAssignmentGovernance(component = window.EduEdgeInstructorAssignments) {
	install(component);
}

installInstructorAssignmentGovernance(window.EduEdgeInstructorAssignments);
window.createEduEdgeInstructorAssignmentGovernanceApp = createEduEdgeInstructorAssignmentGovernanceApp;
window.installInstructorAssignmentGovernance = installInstructorAssignmentGovernance;
