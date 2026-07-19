app_name = "eduedge"
app_title = "EduEdge"
app_publisher = "ProcessEdge Solutions Limited"
app_description = "Education management and school intelligence for African schools"
app_email = "support@processedge.com.ng"
app_license = "mit"

required_apps = ["erpnext", "education", "edgesuite_ui"]
app_include_css = ["/assets/eduedge/css/eduedge_shell_identity.css"]
app_include_js = [
	"eduedge_product_menu.bundle.js",
	"eduedge_shell_identity.bundle.js",
	"eduedge_resource_page_loader.bundle.js",
]

after_install = "eduedge.install.after_install"
after_migrate = "eduedge.install.after_migrate"
extend_bootinfo = "eduedge.boot.extend_bootinfo"

override_whitelisted_methods = {
	"eduedge.api.resource_center.get_resource_page": "eduedge.api.resource_center_safe.get_resource_page",
	"eduedge.api.resource_center.get_resource_editor": "eduedge.api.resource_center_safe.get_resource_editor",
	"eduedge.api.resource_center.save_resource_record": "eduedge.api.resource_center_safe.save_resource_record",
}

add_to_apps_screen = [
	{
		"name": "eduedge",
		"logo": "/assets/eduedge/images/eduedge-mark.svg",
		"title": "EduEdge",
		# Frappe v16 recognises /desk routes as internal Desk apps. Using the
		# legacy /app alias makes the launcher treat EduEdge as an external app.
		"route": "/desk/eduedge-home",
	}
]

doctype_js = {
	"Student Admission": "public/js/education/student_admission.js",
	"Student Applicant": "public/js/education/student_applicant.js",
	"Student": "public/js/education/student.js",
	"Program Enrollment": "public/js/education/program_enrollment.js",
	"Student Group": "public/js/education/student_group.js",
	"Room": "public/js/education/room.js",
	"Course Schedule": "public/js/education/course_schedule.js",
	"Student Attendance": "public/js/education/student_attendance.js",
	"Assessment Plan": "public/js/education/assessment_plan.js",
	"Assessment Result": "public/js/education/assessment_result.js",
}

doc_events = {
	"Student Admission": {
		"before_naming": "eduedge.education.branching.before_naming_student_admission",
		"before_validate": "eduedge.education.branching.before_validate_student_admission",
	},
	"Student Applicant": {
		"before_validate": "eduedge.education.branching.before_validate_student_applicant",
	},
	"Student": {
		"before_validate": "eduedge.education.branching.before_validate_student",
	},
	"Program Enrollment": {
		"before_validate": "eduedge.education.branching.before_validate_program_enrollment",
	},
	"Student Group": {
		"before_validate": "eduedge.education.branching.before_validate_student_group",
	},
	"Room": {
		"before_validate": "eduedge.education.branching.before_validate_room",
	},
	"Course Schedule": {
		"before_validate": "eduedge.education.branching.before_validate_course_schedule",
	},
	"Student Attendance": {
		"before_validate": "eduedge.education.branching.before_validate_student_attendance",
	},
	"Assessment Plan": {
		"before_validate": "eduedge.education.assessment_operations.before_validate_assessment_plan",
	},
	"Assessment Result": {
		"before_validate": "eduedge.education.assessment_operations.before_validate_assessment_result",
	},
}

permission_query_conditions = {
	"EduEdge School Branch": "eduedge.education.permissions.school_branch_query",
	"Student Admission": "eduedge.education.permissions.student_admission_query",
	"Student Applicant": "eduedge.education.permissions.student_applicant_query",
	"Student": "eduedge.education.permissions.student_query",
	"Program Enrollment": "eduedge.education.permissions.program_enrollment_query",
	"Student Group": "eduedge.education.permissions.student_group_query",
	"Room": "eduedge.education.permissions.room_query",
	"Course Schedule": "eduedge.education.permissions.course_schedule_query",
	"Student Attendance": "eduedge.education.permissions.student_attendance_query",
	"Assessment Plan": "eduedge.education.permissions.assessment_plan_query",
	"Assessment Result": "eduedge.education.permissions.assessment_result_query",
	"Guardian": "eduedge.education.permissions.guardian_query",
	"EduEdge Program Offering": "eduedge.education.permissions.program_offering_query",
	"EduEdge Instructor Branch Assignment": "eduedge.education.permissions.instructor_assignment_query",
	"EduEdge Result Publication": "eduedge.education.permissions.result_publication_query",
	"EduEdge Result Publication Log": "eduedge.education.permissions.result_publication_log_query",
	"EduEdge Report Card Review": "eduedge.education.permissions.report_card_review_query",
}

has_permission = {
	"EduEdge School Branch": "eduedge.education.permissions.has_school_branch_record_permission",
	"Student Admission": "eduedge.education.permissions.has_education_branch_permission",
	"Student Applicant": "eduedge.education.permissions.has_education_branch_permission",
	"Student": "eduedge.education.permissions.has_education_branch_permission",
	"Program Enrollment": "eduedge.education.permissions.has_education_branch_permission",
	"Student Group": "eduedge.education.permissions.has_education_branch_permission",
	"Room": "eduedge.education.permissions.has_education_branch_permission",
	"Course Schedule": "eduedge.education.permissions.has_education_branch_permission",
	"Student Attendance": "eduedge.education.permissions.has_education_branch_permission",
	"Assessment Plan": "eduedge.education.permissions.has_education_branch_permission",
	"Assessment Result": "eduedge.education.permissions.has_education_branch_permission",
	"Guardian": "eduedge.education.permissions.has_education_branch_permission",
	"EduEdge Program Offering": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Instructor Branch Assignment": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Result Publication": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Result Publication Log": "eduedge.education.permissions.has_result_publication_log_permission",
	"EduEdge Report Card Review": "eduedge.education.permissions.has_school_branch_permission",
}

fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				[
					"EduEdge Administrator",
					"School Administrator",
					"Academic Administrator",
					"Bursar",
					"Teacher",
					"CBT Invigilator",
					"Student Safety Officer",
				],
			]
		],
	}
]
