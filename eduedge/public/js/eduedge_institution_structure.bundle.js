import EduEdgeInstitutionStructure from "./eduedge_institution_structure/EduEdgeInstitutionStructure.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

window.EduEdgeInstitutionStructure = EduEdgeInstitutionStructure;
window.createEduEdgeInstitutionStructureApp = function createEduEdgeInstitutionStructureApp(props = {}) {
	return createEduEdgeApp(EduEdgeInstitutionStructure, props);
};
