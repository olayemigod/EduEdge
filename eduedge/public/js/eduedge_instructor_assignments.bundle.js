import EduEdgeInstructorAssignments from "./eduedge_instructor_assignments/EduEdgeInstructorAssignments.vue";
import { openInstructorAssignmentReplacementDialog } from "./eduedge_instructor_assignments/replacement_dialog";
import { openInstructorAssignmentTransferDialog } from "./eduedge_instructor_assignments/transfer_dialog";
import { installInstructorAssignmentVisualStyles } from "./eduedge_instructor_assignments/assignment_visual_styles";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

let promotedRowSequence = 0;
const replacementBusy = new WeakMap();
const transferBusy = new WeakMap();

function uniquePromotedRowId() {
	promotedRowSequence += 1;
	return `assignment-row-${Date.now()}-promoted-${promotedRowSequence}`;
}

function keepNewestAssignmentRowOnTop(methodName) {
	const methods = EduEdgeInstructorAssignments.methods || {};
	const original = methods[methodName];
	if (typeof original !== "function") return;

	methods[methodName] = function (...args) {
		const existingIds = new Set((this.rows || []).map((row) => row.row_id));
		const previousLength = (this.rows || []).length;
		const result = original.apply(this, args);
		if ((this.rows || []).length > previousLength) {
			const [newest] = this.rows.splice(this.rows.length - 1, 1);
			if (!newest.row_id || existingIds.has(newest.row_id)) {
				newest.row_id = uniquePromotedRowId();
			}
			this.rows.unshift(newest);
		}
		this.$nextTick?.(() => {
			document.querySelector(".rows-stack .assignment-row")?.scrollIntoView({
				behavior: "smooth",
				block: "start",
			});
		});
		return result;
	};
}

function labelInstitutionSubjectsByClassMembership() {
	const methods = EduEdgeInstructorAssignments.methods || {};
	const original = methods.coursesFor;
	if (typeof original !== "function") return;

	methods.coursesFor = function (row) {
		const courses = original.call(this, row) || [];
		const offering = this.offeringRecord?.(row?.program_offering);
		const configured = new Set(
			this.data?.configured_course_map?.[offering?.program] || [],
		);
		return courses.map((course) => {
			const isConfigured = configured.has(course.name);
			const name = course.course_name || course.name;
			return {
				...course,
				eduedge_configured_in_class: isConfigured,
				course_name: isConfigured
					? name
					: `${name} · Add to Class curriculum`,
			};
		});
	};
}

function enforceReadableReferenceLabels() {
	const methods = EduEdgeInstructorAssignments.methods || {};
	methods.branchLabel = function (name) {
		if (!name) return __("Branch / Campus");
		return this.branchRecord?.(name)?.branch_name || __("Selected Branch / Campus");
	};
	methods.institutionForBranch = function (name) {
		const row = this.branchRecord?.(name);
		return row?.institution_name || __("Institution");
	};
	methods.offeringLabel = function (name) {
		if (!name) return __("Class / Programme Offering");
		const row = this.offeringRecord?.(name);
		if (!row) return __("Selected Class / Programme Offering");
		return row.offering_title || row.program || __("Class / Programme Offering");
	};
	methods.courseName = function (name) {
		if (!name) return "";
		const row = (this.data?.courses || []).find((course) => course.name === name);
		return row?.course_name || __("Selected Subject / Course");
	};
}

function addLifecycleStatuses() {
	const methods = EduEdgeInstructorAssignments.methods || {};
	const original = methods.assignmentStatus;
	if (typeof original !== "function") return;
	methods.assignmentStatus = function (item) {
		if (item?.lifecycle_status === "Replaced") {
			return { label: "Replaced", status: "replaced", tone: "neutral" };
		}
		if (item?.lifecycle_status === "Transferred") {
			return { label: "Transferred", status: "transferred", tone: "neutral" };
		}
		return original.call(this, item);
	};
}

function relationText(item) {
	if (item?.transferred_to_assignment) {
		const relation = item.transferred_to || {};
		return {
			label: `Transferred to ${relation.assignment_title || __("destination responsibility")}`,
			name: relation.name || item.transferred_to_assignment,
		};
	}
	if (item?.transferred_from_assignment) {
		const relation = item.transferred_from || {};
		return {
			label: `Transferred from ${relation.assignment_title || __("previous responsibility")}`,
			name: relation.name || item.transferred_from_assignment,
		};
	}
	if (item?.replaced_by_assignment) {
		const relation = item.replaced_by || {};
		const person = relation.instructor_name || relation.instructor || __("Successor Instructor");
		return {
			label: `Replaced by ${person}`,
			name: relation.name || item.replaced_by_assignment,
		};
	}
	if (item?.replaces_assignment) {
		const relation = item.replaces || {};
		const person = relation.instructor_name || relation.instructor || __("Previous Instructor");
		return {
			label: `Replaces ${person}`,
			name: relation.name || item.replaces_assignment,
		};
	}
	return null;
}

function syncLifecycleRegister(proxy) {
	if (!proxy?.loaded) return;
	const root = document.querySelector(".eduedge-instructor-assignments-root");
	if (!root) return;
	const cards = root.querySelectorAll(".register-list > article");
	const assignments = proxy.data?.assignments || [];
	cards.forEach((card, index) => {
		const item = assignments[index];
		if (!item) return;

		const details = card.querySelector(":scope > span");
		let relation = details?.querySelector("[data-eduedge-lifecycle-relation], [data-eduedge-replacement-relation]");
		const relationInfo = relationText(item);
		if (relationInfo && details) {
			if (!relation) {
				relation = document.createElement("small");
				details.appendChild(relation);
			}
			relation.dataset.eduedgeLifecycleRelation = "1";
			relation.dataset.eduedgeReplacementRelation = "1";
			relation.replaceChildren();
			const text = document.createElement("span");
			text.textContent = relationInfo.label;
			relation.appendChild(text);
			if (relationInfo.name) {
				const open = document.createElement("button");
				open.type = "button";
				open.className = "btn btn-link btn-xs p-0 ml-1";
				open.textContent = __("Open linked assignment");
				open.addEventListener("click", () => proxy.openAssignment?.(relationInfo.name));
				relation.appendChild(document.createTextNode(" · "));
				relation.appendChild(open);
			}
		} else {
			relation?.remove();
		}

		const actions = card.querySelector(":scope > .assignment-actions");
		if (!actions) return;

		let replacementButton = actions.querySelector("[data-eduedge-replace-assignment]");
		const canReplace = Boolean(proxy.canManage && item.can_replace);
		if (!canReplace) {
			replacementButton?.remove();
		} else {
			if (!replacementButton) {
				replacementButton = document.createElement("button");
				replacementButton.type = "button";
				replacementButton.className = "edge-button";
				replacementButton.dataset.eduedgeReplaceAssignment = "1";
				const openButton = actions.querySelector("button:last-of-type");
				if (openButton) actions.insertBefore(replacementButton, openButton);
				else actions.appendChild(replacementButton);
				replacementButton.addEventListener("click", () => {
					const currentItem = (proxy.data?.assignments || []).find((row) => row.name === item.name);
					if (!currentItem?.can_replace) return;
					openInstructorAssignmentReplacementDialog({
						item: { ...currentItem, instructor: currentItem.instructor || proxy.instructor },
						instructors: proxy.data?.instructors || [],
						displayContext: proxy.data || {},
						onBusy: (name) => {
							replacementBusy.set(proxy, name || "");
							syncLifecycleRegister(proxy);
						},
						onComplete: async () => {
							await proxy.load?.();
						},
					});
				});
			}
			const busy = replacementBusy.get(proxy) === item.name;
			replacementButton.disabled = busy;
			replacementButton.textContent = busy ? __("Checking handover...") : __("Replace / Handover");
		}

		let transferButton = actions.querySelector("[data-eduedge-transfer-assignment]");
		const canTransfer = Boolean(proxy.canManage && item.can_transfer);
		if (!canTransfer) {
			transferButton?.remove();
		} else {
			if (!transferButton) {
				transferButton = document.createElement("button");
				transferButton.type = "button";
				transferButton.className = "edge-button";
				transferButton.dataset.eduedgeTransferAssignment = "1";
				const openButton = actions.querySelector("button:last-of-type");
				if (openButton) actions.insertBefore(transferButton, openButton);
				else actions.appendChild(transferButton);
				transferButton.addEventListener("click", () => {
					const currentItem = (proxy.data?.assignments || []).find((row) => row.name === item.name);
					if (!currentItem?.can_transfer) return;
					openInstructorAssignmentTransferDialog({
						item: { ...currentItem, instructor: currentItem.instructor || proxy.instructor },
						displayContext: proxy.data || {},
						onBusy: (name) => {
							transferBusy.set(proxy, name || "");
							syncLifecycleRegister(proxy);
						},
						onComplete: async () => {
							await proxy.load?.();
						},
					});
				});
			}
			const busy = transferBusy.get(proxy) === item.name;
			transferButton.disabled = busy;
			transferButton.textContent = busy ? __("Checking transfer...") : __("Transfer");
		}
	});
}

function syncReplacementRegister(proxy) {
	syncLifecycleRegister(proxy);
}

function installLifecycleRegisterEnhancer() {
	const methods = EduEdgeInstructorAssignments.methods || {};
	const originalLoad = methods.load;
	if (typeof originalLoad === "function") {
		methods.load = async function (...args) {
			const result = await originalLoad.apply(this, args);
			await this.$nextTick?.();
			syncReplacementRegister(this);
			return result;
		};
	}

	const originalMounted = EduEdgeInstructorAssignments.mounted;
	EduEdgeInstructorAssignments.mounted = function (...args) {
		const result = typeof originalMounted === "function" ? originalMounted.apply(this, args) : undefined;
		this.$nextTick?.(() => syncReplacementRegister(this));
		return result;
	};
}

function installReplacementRegisterEnhancer() {
	installLifecycleRegisterEnhancer();
}

installInstructorAssignmentVisualStyles();
keepNewestAssignmentRowOnTop("addAcademicRow");
keepNewestAssignmentRowOnTop("addBranchAccessRow");
keepNewestAssignmentRowOnTop("duplicateRow");
labelInstitutionSubjectsByClassMembership();
enforceReadableReferenceLabels();
addLifecycleStatuses();
installReplacementRegisterEnhancer();

export function createEduEdgeInstructorAssignmentsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstructorAssignments, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstructorAssignments = EduEdgeInstructorAssignments;
	window.createEduEdgeInstructorAssignmentsApp = createEduEdgeInstructorAssignmentsApp;
}

export default EduEdgeInstructorAssignments;