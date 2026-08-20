<template>
	<div class="instructor-record-selector">
		<EdgeLinkField
			:model-value="modelValue"
			:selected-label="selectedLabel"
			placeholder="Search Instructor"
			:searcher="searchInstructors"
			:open-on-focus="true"
			:disabled="busy"
			@update:modelValue="updateValue"
			@select="selectInstructor"
			@clear="clearInstructor"
		/>
	</div>
</template>

<script>
const SEARCH_METHOD = "eduedge.api.instructor_assignment_link_search.search_instructors";

export default {
	name: "InstructorRecordSelector",
	props: {
		controller: { type: Object, required: true },
	},
	computed: {
		modelValue() { return this.controller?.instructor || ""; },
		selectedLabel() {
			const selected = this.controller?.data?.selected_instructor;
			if (selected?.name === this.modelValue) return selected.instructor_name || selected.name;
			const cached = (this.controller?.data?.instructors || []).find((row) => row.name === this.modelValue);
			return cached?.instructor_name || "";
		},
		busy() { return Boolean(this.controller?.loading || this.controller?.registerFilterLoading); },
	},
	methods: {
		async searchInstructors(query) {
			const response = await frappe.call(SEARCH_METHOD, {
				query: query || "",
				page_length: 20,
			});
			return response.message || [];
		},
		updateValue(value) {
			if (this.controller) this.controller.instructor = value || "";
		},
		async selectInstructor(option) {
			if (typeof this.controller?.instructorSelected === "function") {
				await this.controller.instructorSelected(option);
				return;
			}
			this.updateValue(option?.value || "");
			await this.controller?.load?.();
		},
		async clearInstructor() {
			if (typeof this.controller?.instructorCleared === "function") {
				await this.controller.instructorCleared();
				return;
			}
			this.updateValue("");
			await this.controller?.load?.();
		},
	},
};
</script>

<style scoped>
.instructor-record-selector{min-width:16rem;width:min(28rem,100%)}
</style>
