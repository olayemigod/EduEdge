import EduEdgeProgrammes from "./eduedge_programmes/EduEdgeProgrammes.vue";
import { installProgrammeCurriculumGovernance } from "./eduedge_programmes/curriculum_governance";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeProgrammesApp(rootProps = null) {
	const app = createEduEdgeApp(EduEdgeProgrammes, rootProps);
	const originalMount = app.mount.bind(app);
	app.mount = (root) => {
		const result = originalMount(root);
		installProgrammeCurriculumGovernance(app, root);
		return result;
	};
	return app;
}

if (typeof window !== "undefined") {
	window.EduEdgeProgrammes = EduEdgeProgrammes;
	window.createEduEdgeProgrammesApp = createEduEdgeProgrammesApp;
}

export default EduEdgeProgrammes;
