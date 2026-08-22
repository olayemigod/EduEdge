<template>
	<EdgeModal
		:open="open"
		title="New Teaching Schedule"
		:subtitle="`Create one governed Course Schedule for ${branchName || 'the selected Branch'}.`"
		size="lg"
		:busy="saving || savingRoom"
		@close="close"
	>
		<div class="teaching-schedule-form">
			<label>
				<span>Branch / Campus</span>
				<input :value="branchName || branch" type="text" class="form-control" readonly />
			</label>

			<label>
				<span>Schedule Date *</span>
				<input v-model="draft.reference_date" type="date" class="form-control" :disabled="saving || savingRoom" @change="dateChanged" />
			</label>

			<label class="wide">
				<span>Class / Programme Offering *</span>
				<EdgeLinkField
					:model-value="draft.program_offering"
					:selected-label="labels.program_offering"
					placeholder="Search Class / Programme Offering"
					:searcher="searchOfferings"
					:open-on-focus="true"
					:disabled="saving || savingRoom || !branch || !draft.reference_date"
					@update:model-value="updateOffering"
					@select="selectOffering"
					@clear="clearOffering"
				/>
				<small>Only active Classes in the Academic Session covering the selected date are available.</small>
			</label>

			<label class="wide">
				<span>Class Arm *</span>
				<EdgeLinkField
					:model-value="draft.student_group"
					:selected-label="labels.student_group"
					placeholder="Search Class Arm"
					:searcher="searchClassArms"
					:open-on-focus="true"
					:disabled="saving || savingRoom || !draft.program_offering"
					@update:model-value="updateStudentGroup"
					@select="selectStudentGroup"
					@clear="clearStudentGroup"
				/>
			</label>

			<label class="wide">
				<span>Subject *</span>
				<EdgeLinkField
					:model-value="draft.course"
					:selected-label="labels.course"
					placeholder="Search Subject"
					:searcher="searchCourses"
					:open-on-focus="true"
					:disabled="saving || savingRoom || !draft.program_offering || !draft.student_group"
					@update:model-value="updateCourse"
					@select="selectCourse"
					@clear="clearCourse"
				/>
				<small>Only Subjects configured on the selected Class curriculum are shown.</small>
			</label>

			<label class="wide">
				<span>Instructor *</span>
				<EdgeLinkField
					:model-value="draft.instructor"
					:selected-label="labels.instructor"
					placeholder="Search assigned Instructor"
					:searcher="searchInstructors"
					:open-on-focus="true"
					:disabled="saving || savingRoom || !draft.student_group || !draft.course || !draft.reference_date"
					@update:model-value="updateInstructor"
					@select="selectInstructor"
					@clear="clearInstructor"
				/>
				<small>Only an Instructor with a valid teaching responsibility for this Class Arm, Subject and date can be selected.</small>
			</label>

			<div class="wide teaching-schedule-field">
				<span>Room *</span>
				<EdgeLinkField
					:model-value="draft.room"
					:selected-label="labels.room"
					placeholder="Search Room"
					:searcher="searchRooms"
					:open-on-focus="true"
					:disabled="saving || savingRoom || !branch"
					@update:model-value="updateRoom"
					@select="selectRoom"
					@clear="clearRoom"
				/>
				<div class="room-field-help">
					<small>Rooms are restricted to the selected Branch / Campus.</small>
					<button
						type="button"
						class="edge-button edge-button--sm"
						:disabled="saving || savingRoom || !branch"
						@click="roomQuickCreateOpen = !roomQuickCreateOpen"
					>
						{{ roomQuickCreateOpen ? 'Cancel New Room' : 'Create New Room' }}
					</button>
				</div>
			</div>

			<div v-if="roomQuickCreateOpen" class="wide room-quick-create">
				<div class="room-quick-create__heading">
					<div>
						<strong>New Room for {{ branchName || branch }}</strong>
						<small>The Branch / Campus is inherited automatically.</small>
					</div>
				</div>
				<div class="room-quick-create__grid">
					<label>
						<span>Room Name *</span>
						<input v-model="roomDraft.room_name" type="text" class="form-control" :disabled="savingRoom" placeholder="e.g. JSS Block Room 2" />
					</label>
					<label>
						<span>Room Number</span>
						<input v-model="roomDraft.room_number" type="text" class="form-control" :disabled="savingRoom" placeholder="Optional" />
					</label>
					<label>
						<span>Seating Capacity</span>
						<input v-model="roomDraft.seating_capacity" type="number" min="0" class="form-control" :disabled="savingRoom" placeholder="Optional" />
					</label>
				</div>
				<div class="room-quick-create__actions">
					<button type="button" class="edge-button" :disabled="savingRoom" @click="cancelRoomQuickCreate">Cancel</button>
					<button
						type="button"
						class="edge-button edge-button--primary"
						:disabled="savingRoom || !roomDraft.room_name.trim()"
						@click="createRoom"
					>
						{{ savingRoom ? 'Creating Room...' : 'Create & Select Room' }}
					</button>
				</div>
			</div>

			<label>
				<span>From Time *</span>
				<input v-model="draft.from_time" type="time" class="form-control" :disabled="saving || savingRoom" />
			</label>

			<label>
				<span>To Time *</span>
				<input v-model="draft.to_time" type="time" class="form-control" :disabled="saving || savingRoom" />
			</label>
		</div>

		<div class="schedule-safety-note">
			<strong>Conflict-safe save</strong>
			<span>Frappe Education remains authoritative and will block overlapping Class Arm, Instructor, Room or Assessment schedules.</span>
		</div>
		<p v-if="error" class="schedule-create-error" role="alert">{{ error }}</p>

		<template #footer>
			<button type="button" class="edge-button" :disabled="saving || savingRoom" @click="close">Cancel</button>
			<button type="button" class="edge-button edge-button--primary" :disabled="saving || savingRoom || !canSave" @click="save">
				{{ saving ? 'Saving Schedule...' : 'Create Schedule' }}
			</button>
		</template>
	</EdgeModal>
</template>

<script>
async function call(method, args = {}) {
	const response = await frappe.call(method, args);
	return response.message || [];
}

function emptyLabels() {
	return { program_offering: "", student_group: "", course: "", instructor: "", room: "" };
}

function emptyRoomDraft() {
	return { room_name: "", room_number: "", seating_capacity: "" };
}

export default {
	name: "TeachingScheduleCreateDialog",
	props: {
		open: { type: Boolean, default: false },
		branch: { type: String, default: "" },
		branchName: { type: String, default: "" },
		referenceDate: { type: String, default: "" },
	},
	emits: ["close", "saved"],
	data() {
		return {
			saving: false,
			savingRoom: false,
			roomQuickCreateOpen: false,
			error: "",
			draft: this.emptyDraft(),
			roomDraft: emptyRoomDraft(),
			labels: emptyLabels(),
		};
	},
	computed: {
		canSave() {
			return Boolean(
				this.branch
				&& this.draft.reference_date
				&& this.draft.program_offering
				&& this.draft.student_group
				&& this.draft.course
				&& this.draft.instructor
				&& this.draft.room
				&& this.draft.from_time
				&& this.draft.to_time
			);
		},
	},
	watch: {
		open(value) { if (value) this.reset(); },
		branch() { if (this.open) this.reset(); },
		referenceDate(value) {
			if (this.open && value && value !== this.draft.reference_date) {
				this.draft.reference_date = value;
				this.clearOffering();
			}
		},
	},
	methods: {
		emptyDraft() {
			return {
				reference_date: this.referenceDate || frappe.datetime?.get_today?.() || new Date().toISOString().slice(0, 10),
				program_offering: "",
				student_group: "",
				course: "",
				instructor: "",
				room: "",
				from_time: "",
				to_time: "",
			};
		},
		reset() {
			this.error = "";
			this.saving = false;
			this.savingRoom = false;
			this.roomQuickCreateOpen = false;
			this.draft = this.emptyDraft();
			this.roomDraft = emptyRoomDraft();
			this.labels = emptyLabels();
		},
		close() {
			if (!this.saving && !this.savingRoom) this.$emit("close");
		},
		dateChanged() {
			this.error = "";
			this.clearOffering();
		},
		updateOffering(value) {
			if (!value && this.draft.program_offering) this.clearOffering();
			else this.draft.program_offering = value || "";
		},
		selectOffering(option) {
			this.draft.program_offering = option?.value || "";
			this.labels.program_offering = option?.label || option?.value || "";
			this.clearStudentGroup();
		},
		clearOffering() {
			this.draft.program_offering = "";
			this.labels.program_offering = "";
			this.clearStudentGroup();
		},
		updateStudentGroup(value) {
			if (!value && this.draft.student_group) this.clearStudentGroup();
			else this.draft.student_group = value || "";
		},
		selectStudentGroup(option) {
			this.draft.student_group = option?.value || "";
			this.labels.student_group = option?.label || option?.value || "";
			this.clearCourse();
		},
		clearStudentGroup() {
			this.draft.student_group = "";
			this.labels.student_group = "";
			this.clearCourse();
		},
		updateCourse(value) {
			if (!value && this.draft.course) this.clearCourse();
			else this.draft.course = value || "";
		},
		selectCourse(option) {
			this.draft.course = option?.value || "";
			this.labels.course = option?.label || option?.value || "";
			this.clearInstructor();
		},
		clearCourse() {
			this.draft.course = "";
			this.labels.course = "";
			this.clearInstructor();
		},
		updateInstructor(value) { this.draft.instructor = value || ""; },
		selectInstructor(option) {
			this.draft.instructor = option?.value || "";
			this.labels.instructor = option?.label || option?.value || "";
		},
		clearInstructor() {
			this.draft.instructor = "";
			this.labels.instructor = "";
		},
		updateRoom(value) { this.draft.room = value || ""; },
		selectRoom(option) {
			this.draft.room = option?.value || "";
			this.labels.room = option?.label || option?.value || "";
		},
		clearRoom() {
			this.draft.room = "";
			this.labels.room = "";
		},
		cancelRoomQuickCreate() {
			if (this.savingRoom) return;
			this.roomQuickCreateOpen = false;
			this.roomDraft = emptyRoomDraft();
		},
		async createRoom() {
			if (this.savingRoom || !this.branch || !this.roomDraft.room_name.trim()) return;
			this.savingRoom = true;
			this.error = "";
			try {
				const room = await call("eduedge.api.teaching_schedule_rooms.create_teaching_schedule_room", {
					branch: this.branch,
					room_name: this.roomDraft.room_name,
					room_number: this.roomDraft.room_number,
					seating_capacity: this.roomDraft.seating_capacity,
				});
				this.draft.room = room?.value || room?.name || "";
				this.labels.room = room?.label || room?.room_name || this.draft.room;
				this.roomQuickCreateOpen = false;
				this.roomDraft = emptyRoomDraft();
				frappe.show_alert?.({
					message: room?.created === false ? __("Existing Branch Room selected") : __("Room created and selected"),
					indicator: "green",
				});
			} catch (error) {
				this.error = error?.message || __("The Room could not be created.");
			} finally {
				this.savingRoom = false;
			}
		},
		searchOfferings(query) {
			if (!this.branch || !this.draft.reference_date) return [];
			return call("eduedge.api.teaching_schedule.search_teaching_schedule_offerings", {
				branch: this.branch,
				reference_date: this.draft.reference_date,
				query: query || "",
				page_length: 20,
			});
		},
		searchClassArms(query) {
			if (!this.branch || !this.draft.program_offering || !this.draft.reference_date) return [];
			return call("eduedge.api.teaching_schedule.search_teaching_schedule_class_arms", {
				branch: this.branch,
				program_offering: this.draft.program_offering,
				reference_date: this.draft.reference_date,
				query: query || "",
				page_length: 20,
			});
		},
		searchCourses(query) {
			if (!this.branch || !this.draft.program_offering || !this.draft.reference_date) return [];
			return call("eduedge.api.teaching_schedule.search_teaching_schedule_courses", {
				branch: this.branch,
				program_offering: this.draft.program_offering,
				reference_date: this.draft.reference_date,
				query: query || "",
				page_length: 20,
			});
		},
		searchInstructors(query) {
			if (!this.branch || !this.draft.program_offering || !this.draft.student_group || !this.draft.course || !this.draft.reference_date) return [];
			return call("eduedge.api.teaching_schedule.search_teaching_schedule_instructors", {
				branch: this.branch,
				program_offering: this.draft.program_offering,
				student_group: this.draft.student_group,
				course: this.draft.course,
				reference_date: this.draft.reference_date,
				query: query || "",
				page_length: 20,
			});
		},
		searchRooms(query) {
			if (!this.branch) return [];
			return call("eduedge.api.teaching_schedule.search_teaching_schedule_rooms", {
				branch: this.branch,
				query: query || "",
				page_length: 20,
			});
		},
		async save() {
			if (!this.canSave || this.saving || this.savingRoom) return;
			this.saving = true;
			this.error = "";
			try {
				const result = await call("eduedge.api.teaching_schedule.create_teaching_schedule", {
					branch: this.branch,
					reference_date: this.draft.reference_date,
					program_offering: this.draft.program_offering,
					student_group: this.draft.student_group,
					course: this.draft.course,
					instructor: this.draft.instructor,
					room: this.draft.room,
					from_time: this.draft.from_time,
					to_time: this.draft.to_time,
				});
				this.$emit("saved", result);
			} catch (error) {
				this.error = error?.message || __("The Teaching Schedule could not be created.");
			} finally {
				this.saving = false;
			}
		},
	},
};
</script>

<style scoped>
.teaching-schedule-form {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: .85rem;
}
.teaching-schedule-form label,
.teaching-schedule-field { display: grid; gap: .35rem; min-width: 0; font-weight: 650; }
.teaching-schedule-form label > span,
.teaching-schedule-field > span { font-size: .78rem; }
.teaching-schedule-form label > small,
.teaching-schedule-field small { color: var(--edge-color-ink-500, var(--text-muted)); font-size: .72rem; font-weight: 400; }
.teaching-schedule-form .wide { grid-column: 1 / -1; }
.room-field-help {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: .75rem;
	flex-wrap: wrap;
}
.room-quick-create {
	display: grid;
	gap: .75rem;
	padding: .8rem;
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-md, 8px);
	background: var(--edge-color-surface-subtle, var(--control-bg));
}
.room-quick-create__heading > div { display: grid; gap: .2rem; }
.room-quick-create__heading small { color: var(--edge-color-ink-500, var(--text-muted)); font-size: .72rem; font-weight: 400; }
.room-quick-create__grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: .75rem;
}
.room-quick-create__actions { display: flex; justify-content: flex-end; gap: .5rem; }
.schedule-safety-note {
	display: grid;
	gap: .2rem;
	margin-top: 1rem;
	padding: .75rem .85rem;
	border: 1px solid var(--edge-color-border, var(--border-color));
	border-radius: var(--edge-radius-md, 8px);
	background: var(--edge-color-surface-subtle, var(--control-bg));
}
.schedule-safety-note span { color: var(--edge-color-ink-500, var(--text-muted)); font-size: .76rem; }
.schedule-create-error {
	margin: .75rem 0 0;
	padding: .7rem .8rem;
	border-radius: var(--edge-radius-md, 8px);
	background: var(--edge-color-danger-50, #fff1f0);
	color: var(--edge-color-danger-700, #b42318);
	font-size: .8rem;
}
@media (max-width: 700px) {
	.teaching-schedule-form,
	.room-quick-create__grid { grid-template-columns: 1fr; }
	.teaching-schedule-form .wide { grid-column: auto; }
}
</style>