import EduEdgeMyProfile from "./eduedge_my_profile/EduEdgeMyProfile.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeMyProfileApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeMyProfile, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeMyProfile = EduEdgeMyProfile;
	window.createEduEdgeMyProfileApp = createEduEdgeMyProfileApp;
}

export default EduEdgeMyProfile;
