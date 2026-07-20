<template>
	<EdgeAppShell
		product="eduedge"
		title="EduEdge"
		:tenant-name="context.tenant_name || ''"
		:branch-name="activeBranchName"
		:user-name="context.user?.full_name || ''"
		:menu-items="menuItems"
		active-route="/app/eduedge-academic-operations"
		@navigate="openRoute"
	>
		<EdgePageLayout>
			<template #header>
				<EdgePageHeader
					eyebrow="Academic Operations"
					title="Classes, schedules and attendance"
					subtitle="Run daily academic activity inside the selected School Branch or Campus."
					action-label="New Class / Student Group"
					@action="openRoute('/app/student-group/new-student-group')"
				/>
			</template>

			<EdgeLoadingState v-if="loading" message="Loading academic operations..." :skeleton="true" />
			<EdgeErrorState
				v-else-if="error"
				title="Academic operations could not load"
				:message="error"
				action-label="Try again"
				@retry="loadContext"
			/>
			<template v-else>
				<EdgeFilterBar title="Operational context">
					<div class="eduedge-filter-grid">
						<label>
							<span>Branch / Campus</span>
							<select v-model="filters.branch" class="form-control" @change="changeBranch">
								<option
									v-for="branch in context.allowed_branches"
									:key="branch.name"
									:value="branch.name"
								>
									{{ branch.branch_name }}
								</option>
							</select>
						</label>
						<label>
							<span>Date</span>
							<input v-model="filters.date" type="date" class="form-control" @change="loadContext" />
						</label>
						<label>
							<span>Class / Student Group</span>
							<select v-model="filters.student_group" class="form-control" @change="groupChanged">
								<option value="">All classes</option>
								<option v-for="group in context.student_groups" :key="group.name" :value="group.name">
									{{ group.student_group_name }}
								</option>
							</select>
						</label>
					</div>
					<template #actions>
						<button type="button" class="edge-button edge-button--primary" @click="loadContext">
							Refresh
						</button>
					</template>
				</EdgeFilterBar>

				<EdgeDashboardLayout min-column-width="12rem">
					<EdgeStatCard label="Classes" :value="context.counts.student_groups" helper="Active groups in current session" />
					<EdgeStatCard label="Assigned Instructors" :value="context.counts.assigned_instructors" helper="Enabled branch assignments" />
					<EdgeStatCard label="Today's Schedules" :value="context.counts.schedules" helper="Filtered by selected date" />
					<EdgeStatCard label="Attendance Submitted" :value="context.counts.attendance_submitted" helper="Submitted student records" />
					<EdgeStatCard label="Present" :value="context.counts.present" tone="success" />
					<EdgeStatCard label="Absent" :value="context.counts.absent" tone="danger" />
				</EdgeDashboardLayout>

				<section class="eduedge-operations-grid">
					<article class="eduedge-panel">
						<div class="eduedge-panel-header">
							<div>
								<p class="edge-eyebrow">Schedule</p>
								<h2>Classes for {{ filters.date }}</h2>
							</div>
							<button type="button" class="edge-button" @click="openRoute('/app/course-schedule/new-course-schedule')">
								Add schedule
							</button>
						</div>
						<EdgeEmptyState
							v-if="!context.schedules.length"
							title="No classes scheduled"
							description="Create a Course Schedule or choose another date."
						/>
						<div v-else class="eduedge-schedule-list">
							<button
								v-for="schedule in context.schedules"
								:key="schedule.name"
								type="button"
								class="eduedge-schedule-card"
								@click="selectSchedule(schedule)"
							>
								<strong>{{ schedule.course }}</strong>
								<span>{{ schedule.student_group }}</span>
								<span>{{ schedule.instructor_name || schedule.instructor }}</span>
								<span>{{ formatTime(schedule.from_time) }} – {{ formatTime(schedule.to_time) }} · {{ schedule.room }}</span>
							</button>
						</div>
					</article>

					<article class="eduedge-panel">
						<div class="eduedge-panel-header">
							<div>
								<p class="edge-eyebrow">Attendance</p>
								<h2>Class register</h2>
							</div>
							<button
								type="button"
								class="edge-button"
								:disabled="!filters.student_group || registerLoading"
								@click="loadRegister"
							>
								Load register
							</button>
						</div>

						<EdgeLoadingState v-if="registerLoading" message="Loading class register..." />
						<EdgeErrorState
							v-else-if="registerError"
							title="Register could not load"
							:message="registerError"
							action-label="Try again"
							@retry="loadRegister"
						/>
						<EdgeEmptyState
							v-else-if="!register.students.length"
							title="Select a class"
							description="Choose a Class / Student Group or a schedule to mark attendance."
						/>
						<template v-else>
							<div class="eduedge-register-summary">
								<EdgeStatusBadge
									:label="`${register.submitted_count} submitted`"
									:status="register.submitted_count ? 'submitted' : 'none'"
									:tone="register.submitted_count ? 'success' : 'neutral'"
								/>
								<EdgeStatusBadge
									:label="`${register.pending_count} editable`"
									:status="register.pending_count ? 'pending' : 'complete'"
									:tone="register.pending_count ? 'warning' : 'success'"
								/>
							</div>
							<div class="eduedge-table-wrap">
								<table class="table table-bordered eduedge-register-table">
									<thead>
										<tr>
											<th>Roll No.</th>
											<th>Student</th>
											<th>Status</th>
											<th>Record</th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="student in register.students" :key="student.student">
											<td>{{ student.group_roll_number || "—" }}</td>
											<td>
												<strong>{{ student.student_name }}</strong>
												<div class="text-muted">{{ student.student }}</div>
											</td>
											<td>
												<select
													v-model="student.status"
													class="form-control input-sm"
													:disabled="student.locked || saving"
												>
													<option value="Present">Present</option>
													<option value="Absent">Absent</option>
													<option value="Leave">Leave</option>
												</select>
											</td>
											<td>
												<EdgeStatusBadge
													:label="student.locked ? 'Submitted' : student.attendance_name ? 'Draft' : 'New'"
													:status="student.locked ? 'submitted' : 'draft'"
													:tone="student.locked ? 'success' : 'neutral'"
												/>
											</td>
										</tr>
									</tbody>
								</table>
							</div>
							<EdgeActionBar label="Submitted attendance is immutable. Cancel or amend the record before changing it.">
								<template #actions>
									<button type="button" class="edge-button" :disabled="saving" @click="saveRegister(false)">
										Save Draft
									</button>
									<button type="button" class="edge-button edge-button--primary" :disabled="saving" @click="saveRegister(true)">
										Submit Attendance
									</button>
								</template>
							</EdgeActionBar>
						</template>
					</article>
				</section>
			</template>
		</EdgePageLayout>
	</EdgeAppShell>
</template>

<script>
import { EDUEDGE_MENU_ITEMS, openEduEdgeRoute } from "../eduedge_ui/navigation";

export default {
	name: "EduEdgeAcademicOperations",
	data() {
		const today = new Date().toISOString().slice(0, 10);
		return {
			loading: true,
			error: "",
			registerLoading: false,
			registerError: "",
			saving: false,
			menuItems: EDUEDGE_MENU_ITEMS,
			filters: {
				branch: "",
				date: today,
				student_group: "",
				course_schedule: "",
			},
			context: {
				user: {},
				current_branch: null,
				allowed_branches: [],
				counts: {
					student_groups: 0,
					assigned_instructors: 0,
					schedules: 0,
					attendance_submitted: 0,
					present: 0,
					absent: 0,
					leave: 0,
				},
				student_groups: [],
				schedules: [],
			},
			register: {
				students: [],
				submitted_count: 0,
				pending_count: 0,
			},
		};
	},
	computed: {
		activeBranchName() {
			const branch = this.context.allowed_branches.find((item) => item.name === this.filters.branch);
			return branch?.branch_name || this.context.current_branch?.branch_name || "";
		},
	},
	mounted() {
		this.loadContext();
	},
	methods: {
		openRoute: openEduEdgeRoute,
		formatTime(value) {
			return String(value || "").slice(0, 5);
		},
		async loadContext() {
			this.loading = true;
			this.error = "";
			try {
				const response = await frappe.call("eduedge.api.academic_operations.get_operations_context", {
					branch: this.filters.branch || undefined,
					date: this.filters.date,
					student_group: this.filters.student_group || undefined,
				});
				this.context = response.message || this.context;
				this.filters.branch = this.context.filters?.branch || this.filters.branch;
				this.filters.date = this.context.filters?.date || this.filters.date;
			} catch (error) {
				this.error = error?.message || "Academic operations context could not be loaded.";
			} finally {
				this.loading = false;
			}
		},
		async changeBranch() {
			if (!this.filters.branch) return;
			try {
				await frappe.call("eduedge.api.branch_context.switch_school_branch", {
					branch: this.filters.branch,
				});
				this.filters.student_group = "";
				this.filters.course_schedule = "";
				this.register = { students: [], submitted_count: 0, pending_count: 0 };
				await this.loadContext();
			} catch (error) {
				frappe.msgprint({
					title: __("Unable to switch branch"),
					message: error?.message || __("The selected branch could not be activated."),
					indicator: "red",
				});
			}
		},
		async groupChanged() {
			this.filters.course_schedule = "";
			this.register = { students: [], submitted_count: 0, pending_count: 0 };
			await this.loadContext();
		},
		selectSchedule(schedule) {
			this.filters.student_group = schedule.student_group;
			this.filters.course_schedule = schedule.name;
			this.loadRegister();
		},
		async loadRegister() {
			if (!this.filters.student_group) return;
			this.registerLoading = true;
			this.registerError = "";
			try {
				const response = await frappe.call("eduedge.api.academic_operations.get_attendance_register", {
					student_group: this.filters.student_group,
					date: this.filters.date,
					course_schedule: this.filters.course_schedule || undefined,
				});
				this.register = response.message || this.register;
			} catch (error) {
				this.registerError = error?.message || "The attendance register could not be loaded.";
			} finally {
				this.registerLoading = false;
			}
		},
		async saveRegister(submit) {
			if (!this.register.students.length) return;
			this.saving = true;
			try {
				const response = await frappe.call("eduedge.api.academic_operations.save_attendance_register", {
					student_group: this.filters.student_group,
					date: this.register.date || this.filters.date,
					course_schedule: this.filters.course_schedule || undefined,
					entries: this.register.students.map((row) => ({
						student: row.student,
						status: row.status,
					})),
					submit: submit ? 1 : 0,
				});
				const result = response.message || {};
				frappe.show_alert({
					message: submit
						? `${result.submitted || 0} attendance records submitted`
						: `${(result.created || 0) + (result.updated || 0)} draft records saved`,
					indicator: "green",
				});
				await this.loadRegister();
				await this.loadContext();
			} catch (error) {
				frappe.msgprint({
					title: __("Attendance could not be saved"),
					message: error?.message || __("Review the register and try again."),
					indicator: "red",
				});
			} finally {
				this.saving = false;
			}
		},
	},
};
</script>

<style scoped>
.eduedge-filter-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
	gap: 0.75rem;
	width: 100%;
}

.eduedge-filter-grid label {
	display: grid;
	gap: 0.35rem;
	font-weight: 600;
}

.eduedge-operations-grid {
	display: grid;
	grid-template-columns: minmax(18rem, 0.8fr) minmax(28rem, 1.5fr);
	gap: var(--edge-space-4, 1rem);
	margin-top: var(--edge-space-5, 1.25rem);
}

.eduedge-panel {
	padding: var(--edge-space-5, 1.25rem);
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-lg, 12px);
	background: var(--card-bg);
}

.eduedge-panel-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	margin-bottom: 1rem;
}

.eduedge-panel-header h2 {
	margin: 0.25rem 0 0;
}

.eduedge-schedule-list {
	display: grid;
	gap: 0.75rem;
}

.eduedge-schedule-card {
	display: grid;
	gap: 0.25rem;
	width: 100%;
	padding: 0.9rem;
	text-align: left;
	border: 1px solid var(--border-color);
	border-radius: var(--edge-radius-md, 8px);
	background: var(--control-bg);
}

.eduedge-schedule-card:hover {
	border-color: var(--primary);
}

.eduedge-schedule-card span {
	color: var(--text-muted);
}

.eduedge-register-summary {
	display: flex;
	flex-wrap: wrap;
	gap: 0.5rem;
	margin-bottom: 1rem;
}

.eduedge-table-wrap {
	overflow-x: auto;
}

.eduedge-register-table {
	min-width: 42rem;
}

@media (max-width: 960px) {
	.eduedge-operations-grid {
		grid-template-columns: 1fr;
	}
}
</style>
