app_name = "eduedge"
app_title = "EduEdge"
app_publisher = "ProcessEdge Solutions Limited"
app_description = "Education management and school intelligence for African schools"
app_email = "support@processedge.com.ng"
app_license = "mit"

required_apps = ["erpnext", "education", "edgesuite_ui"]

after_install = "eduedge.install.after_install"
after_migrate = "eduedge.install.after_migrate"

add_to_apps_screen = [
	{
		"name": "eduedge",
		"logo": "/assets/eduedge/images/eduedge-mark.svg",
		"title": "EduEdge",
		"route": "/app/eduedge-home",
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
}

permission_query_conditions = {
	"Student Admission": "eduedge.education.permissions.student_admission_query",
	"Student Applicant": "eduedge.education.permissions.student_applicant_query",
	"Student": "eduedge.education.permissions.student_query",
	"Program Enrollment": "eduedge.education.permissions.program_enrollment_query",
	"Student Group": "eduedge.education.permissions.student_group_query",
	"Room": "eduedge.education.permissions.room_query",
	"Course Schedule": "eduedge.education.permissions.course_schedule_query",
	"Student Attendance": "eduedge.education.permissions.student_attendance_query",
	"Guardian": "eduedge.education.permissions.guardian_query",
	"EduEdge Program Offering": "eduedge.education.permissions.program_offering_query",
	"EduEdge Instructor Branch Assignment": "eduedge.education.permissions.instructor_assignment_query",
}

has_permission = {
	"Student Admission": "eduedge.education.permissions.has_education_branch_permission",
	"Student Applicant": "eduedge.education.permissions.has_education_branch_permission",
	"Student": "eduedge.education.permissions.has_education_branch_permission",
	"Program Enrollment": "eduedge.education.permissions.has_education_branch_permission",
	"Student Group": "eduedge.education.permissions.has_education_branch_permission",
	"Room": "eduedge.education.permissions.has_education_branch_permission",
	"Course Schedule": "eduedge.education.permissions.has_education_branch_permission",
	"Student Attendance": "eduedge.education.permissions.has_education_branch_permission",
	"Guardian": "eduedge.education.permissions.has_education_branch_permission",
	"EduEdge Program Offering": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Instructor Branch Assignment": "eduedge.education.permissions.has_school_branch_permission",
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
