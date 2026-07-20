import EduEdgeSettingsCenter from "./eduedge_settings_center/EduEdgeSettingsCenter.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

window.EduEdgeSettingsCenter = EduEdgeSettingsCenter;
window.createEduEdgeSettingsCenterApp = function createEduEdgeSettingsCenterApp(props = {}) {
	return createEduEdgeApp(EduEdgeSettingsCenter, props);
};
