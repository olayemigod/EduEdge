import EduEdgeBranchGovernance from "./eduedge_branch_governance/EduEdgeBranchGovernance.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeBranchGovernanceApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeBranchGovernance, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeBranchGovernance = EduEdgeBranchGovernance;
	window.createEduEdgeBranchGovernanceApp = createEduEdgeBranchGovernanceApp;
}

export default EduEdgeBranchGovernance;
