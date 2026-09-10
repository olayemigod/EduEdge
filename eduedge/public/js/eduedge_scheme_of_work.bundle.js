import EduEdgeSchemeOfWork from "./eduedge_scheme_of_work/EduEdgeSchemeOfWork.vue";
import { installSchemeSessionContext } from "./eduedge_scheme_of_work/session_context";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

installSchemeSessionContext(EduEdgeSchemeOfWork);

export function createEduEdgeSchemeOfWorkApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeSchemeOfWork, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeSchemeOfWork = EduEdgeSchemeOfWork;
	window.createEduEdgeSchemeOfWorkApp = createEduEdgeSchemeOfWorkApp;
}

export default EduEdgeSchemeOfWork;
