<template>
	<div class="assignment-search-fields">
		<label v-if="showInstructor" class="assignment-search-field">
			<span>Instructor *</span>
			<EdgeLinkField
				:model-value="instructor"
				placeholder="Search Instructor"
				:searcher="searchInstructors"
				@update:modelValue="$emit('update:instructor', $event)"
				@select="$emit('instructor-select', $event)"
				@clear="$emit('instructor-clear')"
			/>
		</label>

		<label v-if="row && row.assignment_scope !== branchOnlyScope" class="assignment-search-field wide">
			<span>Class / Programme Offering *</span>
			<EdgeLinkField
				:model-value="row.program_offering"
				placeholder="Search Class / Programme Offering"
				:disabled="!row.branch"
				:context="{ branch: row.branch }"
				:searcher="(query) => searchOfferings(row, query)"
				@update:modelValue="$emit('update:offering', $event)"
				@select="$emit('offering-select', $event)"
				@clear="$emit('offering-clear')"
			/>
		</label>

		<label v-if="row && row.assignment_scope === classArmScope" class="assignment-search-field wide">
			<span>Class Arms *</span>
			<EduEdgeMultiLinkField
				:model-value="row.student_groups"
				placeholder="Search Class Arms"
				:disabled="!row.program_offering"
				:context="{ branch: row.branch, program_offering: row.program_offering }"
				:searcher="(query) => searchClassArms(row, query)"
				@update:modelValue="$emit('update:class-arms', $event)"
				@change="$emit('class-arms-change', $event)"
			/>
			<small>Select one or several Class Arms that should receive the same responsibility.</small>
		</label>

		<label v-if="row && requiresSubjects" class="assignment-search-field wide">
			<span>{{ subjectLabel }} *</span>
			<EduEdgeMultiLinkField
				:model-value="row.courses"
				:placeholder="`Search ${subjectLabel}`"
				:disabled="!row.program_offering"
				:context="{ branch: row.branch, program_offering: row.program_offering }"
				:searcher="(query) => searchCourses(row, query)"
				@update:modelValue="$emit('update:courses', $event)"
				@change="$emit('courses-change', $event)"
			/>
		</label>
	</div>
</template>

<script>
async function call(method, args = {}) {
	const response = await frappe.call(method, args);
	return response.message || [];
}

export default {
	name: "InstructorAssignmentSearchFields",
	props: {
		instructor: { type: String, default: "" },
		row: { type: Object, default: null },
		showInstructor: { type: Boolean, default: false },
		branchOnlyScope: { type: String, required: true },
		classArmScope: { type: String, required: true },
		requiresSubjects: { type: Boolean, default: false },
		subjectLabel: { type: String, default: "Subjects / Courses" },
	},
	emits: [
		"update:instructor",
		"instructor-select",
		"instructor-clear",
		"update:offering",
		"offering-select",
		"offering-clear",
		"update:class-arms",
		"class-arms-change",
		"update:courses",
		"courses-change",
	],
	methods: {
		searchInstructors(query) {
			return call("eduedge.api.instructor_assignment_link_search.search_instructors", {
				query: query || "",
				page_length: 20,
			});
		},
		searchOfferings(row, query) {
			if (!row?.branch) return [];
			return call("eduedge.api.instructor_assignment_link_search.search_assignment_offerings", {
				branch: row.branch,
				query: query || "",
				page_length: 20,
			});
		},
		searchClassArms(row, query) {
			if (!row?.branch || !row?.program_offering) return [];
			return call("eduedge.api.instructor_assignment_link_search.search_assignment_class_arms", {
				branch: row.branch,
				program_offering: row.program_offering,
				query: query || "",
				page_length: 20,
			});
		},
		searchCourses(row, query) {
			if (!row?.branch || !row?.program_offering) return [];
			return call("eduedge.api.instructor_assignment_link_search.search_assignment_courses", {
				branch: row.branch,
				program_offering: row.program_offering,
				query: query || "",
				page_length: 20,
			});
		},
	},
};
</script>

<style scoped>
.assignment-search-fields { display: contents; }
.assignment-search-field { display: grid; gap: .35rem; font-weight: 600; }
.assignment-search-field.wide { grid-column: 1 / -1; }
.assignment-search-field small { color: var(--text-muted); font-weight: 400; }
</style>
