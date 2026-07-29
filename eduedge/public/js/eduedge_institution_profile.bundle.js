import EduEdgeInstitutionProfile from "./eduedge_institution_profile/EduEdgeInstitutionProfile.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeInstitutionProfileApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstitutionProfile, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstitutionProfile = EduEdgeInstitutionProfile;
	window.createEduEdgeInstitutionProfileApp = createEduEdgeInstitutionProfileApp;
}

export default EduEdgeInstitutionProfile;
