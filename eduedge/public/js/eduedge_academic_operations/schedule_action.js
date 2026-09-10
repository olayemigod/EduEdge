const COURSE_SCHEDULE_CREATE_ROUTE = "/app/course-schedule/new-course-schedule";

function clientCanCreateCourseSchedule() {
	try {
		if (typeof frappe?.model?.can_create === "function") {
			return Boolean(frappe.model.can_create("Course Schedule"));
		}
	} catch (error) {
		console.warn("Unable to resolve client Course Schedule create permission", error);
	}
	return false;
}

export function installAcademicOperationsScheduleAction(component) {
	if (!component || component.__eduedgeScheduleActionInstalled) return;
	component.__eduedgeScheduleActionInstalled = true;

	const computed = component.computed || (component.computed = {});
	computed.canCreateCourseSchedule = function () {
		// The operations-context permission remains the normal source of truth for
		// visibility. Frappe boot permissions are a safe UI fallback when a stale or
		// partial context payload omits/misstates the flag; the native DocType route
		// and server permission checks still govern actual creation.
		return Boolean(
			this.permissions?.can_create_course_schedule || clientCanCreateCourseSchedule(),
		);
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
