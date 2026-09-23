import EduEdgeInstructorAssignments from "./EduEdgeInstructorAssignments.vue";

/*
 * Instructor Branch Eligibility is owned by Branch Governance.
 *
 * This module remains as a compatibility import for older loader/runtime bundles,
 * but it must not add Branch Eligibility authoring controls or mutate assignment
 * planner behavior. The Vue page and backend now consume governance directly.
 */
function install(component) {
	if (!component || component.__eduedgeBranchGovernanceConsumerInstalled) return;
	component.__eduedgeBranchGovernanceConsumerInstalled = true;
}

install(EduEdgeInstructorAssignments);

export function installInstructorBranchAlignment(component = EduEdgeInstructorAssignments) {
	install(component);
}
