const COURSE_SCHEDULE_CREATE_ROUTE = "/app/course-schedule/new-course-schedule";

export function installAcademicOperationsScheduleAction(component) {
	if (!component || component.__eduedgeScheduleActionInstalled) return;
	component.__eduedgeScheduleActionInstalled = true;

	const computed = component.computed || (component.computed = {});
	computed.canCreateCourseSchedule = function () {
		return Boolean(this.permissions?.can_create_course_schedule);
	};

	const methods = component.methods || (component.methods = {});
	const originalOpenRoute = methods.openRoute;
	methods.openRoute = function (route, ...args) {
		if (String(route || "") === COURSE_SCHEDULE_CREATE_ROUTE && !this.calendarReady) {
			const calendar = this.context?.academic_calendar || {};
			const message =
				calendar.blocking_issue ||
				(calendar.calendar_gap
					? __("The selected date is outside a configured Term / Semester. Review the Institution Academic Calendar before adding a Schedule.")
					: __("Configure the Institution Academic Session and Term / Semester for the selected date before adding a Schedule."));
			frappe.msgprint({
				title: __("Academic Calendar required"),
				message,
				indicator: "orange",
			});
			return;
		}
		if (typeof originalOpenRoute === "function") return originalOpenRoute.call(this, route, ...args);
		window.location.href = route;
	};
}
