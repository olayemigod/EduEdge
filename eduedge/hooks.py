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
		"route": "/app/eduedge",
	}
]

doctype_js = {
	"Student Admission": "public/js/education/student_admission.js",
	"Student Applicant": "public/js/education/student_applicant.js",
	"Student": "public/js/education/student.js",
	"Program Enrollment": "public/js/education/program_enrollment.js",
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
}

permission_query_conditions = {
	"Student Admission": "eduedge.education.permissions.student_admission_query",
	"Student Applicant": "eduedge.education.permissions.student_applicant_query",
	"Student": "eduedge.education.permissions.student_query",
	"Program Enrollment": "eduedge.education.permissions.program_enrollment_query",
	"Guardian": "eduedge.education.permissions.guardian_query",
	"EduEdge Program Offering": "eduedge.education.permissions.program_offering_query",
}

has_permission = {
	"Student Admission": "eduedge.education.permissions.has_education_branch_permission",
	"Student Applicant": "eduedge.education.permissions.has_education_branch_permission",
	"Student": "eduedge.education.permissions.has_education_branch_permission",
	"Program Enrollment": "eduedge.education.permissions.has_education_branch_permission",
	"Guardian": "eduedge.education.permissions.has_education_branch_permission",
	"EduEdge Program Offering": "eduedge.education.permissions.has_program_offering_permission",
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
