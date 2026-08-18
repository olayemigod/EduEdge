import EduEdgeInstitutionOperationsSettings from "./eduedge_institution_operations_settings/EduEdgeInstitutionOperationsSettings.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeInstitutionOperationsSettingsApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeInstitutionOperationsSettings, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeInstitutionOperationsSettings = EduEdgeInstitutionOperationsSettings;
	window.createEduEdgeInstitutionOperationsSettingsApp = createEduEdgeInstitutionOperationsSettingsApp;
}

export default EduEdgeInstitutionOperationsSettings;
