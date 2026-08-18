<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="activeContext.institution_name || ''"
		:branch-name="activeContext.branch_name || 'Academic Session Launch'"
		:menu-items="menuItems"
		active-route="/app/eduedge-academic-sessions"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<EduEdgeSessionLaunchPanel />
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import EduEdgeSessionLaunchPanel from "../eduedge_ui/components/EduEdgeSessionLaunchPanel.vue";
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeSessionLaunch",
	components: { EduEdgeSessionLaunchPanel },
	data() {
		return {
			menuItems: EDUEDGE_MENU_ITEMS,
		};
	},
	computed: {
		activeContext() {
			return frappe.boot?.eduedge_institution_context || {};
		},
	},
	methods: {
		openRoute: openEduEdgeRoute,
	},
};
</script>
