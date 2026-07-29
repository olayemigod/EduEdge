app_name = "eduedge"
app_title = "EduEdge"
app_publisher = "ProcessEdge Solutions Limited"
app_description = "Education management and school intelligence for African schools"
app_email = "support@processedge.com.ng"
app_license = "mit"

required_apps = ["erpnext", "education", "edgesuite_ui"]
app_include_css = []
app_include_js = [
	"eduedge_terminology.bundle.js",
	"eduedge_product_menu.bundle.js",
	"eduedge_resource_page_loader.bundle.js",
]

after_install = "eduedge.install.after_install"
after_migrate = "eduedge.install.after_migrate"
extend_bootinfo = "eduedge.boot.extend_bootinfo"

scheduler_events = {
	"hourly": [
		"eduedge.platform.runtime_context.refresh_cached_runtime_context",
	]
}

override_whitelisted_methods = {
	"eduedge.api.resource_center.get_resource_page": "eduedge.api.resource_center_safe.get_resource_page",
	"eduedge.api.resource_center.get_resource_editor": "eduedge.api.resource_center_safe.get_resource_editor",
	"eduedge.api.resource_center.search_resource_options": "eduedge.api.resource_center_safe.search_resource_options",
	"eduedge.api.resource_center.save_resource_record": "eduedge.api.resource_center_safe.save_resource_record",
	"eduedge.api.resource_center.delete_resource_record": "eduedge.api.resource_center_safe.delete_resource_record",
	"eduedge.api.modal_records.save_modal_record": "eduedge.api.modal_records_safe.save_modal_record",
	"eduedge.api.academic_operations.get_operations_context": "eduedge.api.academic_operations_safe.get_operations_context",
	"eduedge.api.academic_operations.get_attendance_register": "eduedge.api.academic_operations_safe.get_attendance_register",
	"eduedge.api.academic_operations.save_attendance_register": "eduedge.api.academic_operations_safe.save_attendance_register",
}

add_to_apps_screen = [
	{
		"name": "eduedge",
		"logo": "/assets/eduedge/images/eduedge-mark.svg",
		"title": "EduEdge",
		"route": "/desk/eduedge-home",
	}
]

doctype_js = {
	"Program": "public/js/education/program.js",
	"Course": "public/js/education/course.js",
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
	"Company": {
		"before_validate": "eduedge.education.institution_types.before_validate_company",
	},
	"Program": {
		"before_validate": "eduedge.education.academic_validation.before_validate_program",
	},
	"Course": {
		"before_validate": "eduedge.education.academic_validation.before_validate_course",
	},
	"Student Batch Name": {
		"before_validate": "eduedge.education.academic_validation.before_validate_institution_owned_master",
	},
	"Student House": {
		"before_validate": "eduedge.education.academic_validation.before_validate_institution_owned_master",
	},
	"Instructor": {
		"before_validate": "eduedge.education.academic_validation.before_validate_institution_owned_master",
	},
	"Assessment Group": {
		"before_validate": "eduedge.education.academic_validation.before_validate_institution_owned_master",
	},
	"Grading Scale": {
		"before_validate": "eduedge.education.academic_validation.before_validate_institution_owned_master",
	},
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
		"before_submit": "eduedge.education.enrollment_capacity.before_submit_program_enrollment",
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
	"Fee Structure": {
		"before_validate": "eduedge.education.academic_validation.before_validate_fee_structure",
	},
	"Fee Schedule": {
		"before_validate": "eduedge.education.academic_fee_context.before_validate_fee_schedule",
	},
	"Fees": {
		"before_validate": "eduedge.education.academic_validation.before_validate_fees",
	},
	"Student Leave Application": {
		"before_validate": "eduedge.education.academic_validation.before_validate_student_leave",
	},
	"Student Log": {
		"before_validate": "eduedge.education.academic_validation.before_validate_student_log",
	},
	"EduEdge CBT Question": {
		"validate": "eduedge.cbt.master_lifecycle.validate_master_docstatus",
		"before_submit": "eduedge.cbt.master_lifecycle.block_master_submit",
		"before_cancel": "eduedge.cbt.master_lifecycle.block_master_cancel",
	},
	"EduEdge CBT Exam Template": {
		"validate": "eduedge.cbt.master_lifecycle.validate_master_docstatus",
		"before_submit": "eduedge.cbt.master_lifecycle.block_master_submit",
		"before_cancel": "eduedge.cbt.master_lifecycle.block_master_cancel",
	},
}

permission_query_conditions = {
	"EduEdge Institution": "eduedge.education.institution_permissions.institution_query",
	"EduEdge Academic Section": "eduedge.education.academic_permissions.academic_section_query",
	"EduEdge Academic Level": "eduedge.education.academic_permissions.academic_level_query",
	"EduEdge Institution Academic Calendar": "eduedge.education.academic_permissions.academic_calendar_query",
	"Program": "eduedge.education.academic_permissions.program_query",
	"Course": "eduedge.education.academic_permissions.course_query",
	"Student Batch Name": "eduedge.education.academic_permissions.student_batch_query",
	"Student House": "eduedge.education.academic_permissions.student_house_query",
	"Instructor": "eduedge.education.academic_permissions.instructor_query",
	"Assessment Group": "eduedge.education.academic_permissions.assessment_group_query",
	"Grading Scale": "eduedge.education.academic_permissions.grading_scale_query",
	"Fee Structure": "eduedge.education.academic_permissions.fee_structure_query",
	"EduEdge Enrollment Status Log": "eduedge.education.academic_branch_permissions.enrollment_status_log_query",
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
	"EduEdge Training Progress": "eduedge.training.permissions.training_progress_query",
	"EduEdge Examination Centre": "eduedge.cbt.permissions.examination_centre_query",
	"EduEdge CBT Question": "eduedge.cbt.permissions.cbt_question_query",
	"EduEdge CBT Exam Template": "eduedge.cbt.permissions.cbt_exam_template_query",
	"EduEdge CBT Exam Schedule": "eduedge.cbt.permissions.cbt_exam_schedule_query",
	"EduEdge CBT Candidate Assignment": "eduedge.cbt.permissions.cbt_candidate_assignment_query",
	"EduEdge CBT Intervention Log": "eduedge.cbt.permissions.cbt_intervention_log_query",
}

has_permission = {
	"EduEdge Institution": "eduedge.education.institution_permissions.has_institution_permission",
	"EduEdge Academic Section": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"EduEdge Academic Level": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"EduEdge Institution Academic Calendar": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Program": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Course": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Student Batch Name": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Student House": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Instructor": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Assessment Group": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Grading Scale": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"Fee Structure": "eduedge.education.academic_permissions.has_academic_institution_permission",
	"EduEdge Enrollment Status Log": "eduedge.education.academic_branch_permissions.has_enrollment_status_log_permission",
	"EduEdge School Branch": "eduedge.education.permissions.has_school_branch_record_permission",
	"Student Admission": "eduedge.education.permissions.has_education_branch_permission",
	"Student Applicant": "eduedge.education.permissions.has_education_branch_permission",
	"Student": "eduedge.education.permissions.has_education_branch_permission",
	"Program Enrollment": "eduedge.education.permissions.has_education_branch_permission",
	"Student Group": "eduedge.education.permissions.has_education_branch_permission",
	"Room": "eduedge.education.permissions.has_education_branch_permission",
	"Course Schedule": "eduedge.education.permissions.has_course_schedule_permission",
	"Student Attendance": "eduedge.education.permissions.has_student_attendance_permission",
	"Assessment Plan": "eduedge.education.permissions.has_education_branch_permission",
	"Assessment Result": "eduedge.education.permissions.has_education_branch_permission",
	"Guardian": "eduedge.education.permissions.has_education_branch_permission",
	"EduEdge Program Offering": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Instructor Branch Assignment": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Result Publication": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Result Publication Log": "eduedge.education.permissions.has_result_publication_log_permission",
	"EduEdge Report Card Review": "eduedge.education.permissions.has_school_branch_permission",
	"EduEdge Training Progress": "eduedge.training.permissions.has_training_progress_permission",
	"EduEdge Examination Centre": "eduedge.cbt.permissions.has_school_branch_permission",
	"EduEdge CBT Question": "eduedge.cbt.permissions.has_school_branch_permission",
	"EduEdge CBT Exam Template": "eduedge.cbt.permissions.has_school_branch_permission",
	"EduEdge CBT Exam Schedule": "eduedge.cbt.permissions.has_school_branch_permission",
	"EduEdge CBT Candidate Assignment": "eduedge.cbt.permissions.has_school_branch_permission",
	"EduEdge CBT Intervention Log": "eduedge.cbt.permissions.has_school_branch_permission",
}

fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				[
					"EduEdge Super Administrator",
					"EduEdge Public Exam Administrator",
					"EduEdge Administrator",
					"School Administrator",
					"Academic Administrator",
					"Bursar",
					"Teacher",
					"CBT Invigilator",
					"Student Safety Officer",
					"Registrar",
					"Admission Officer",
					"School HR Officer",
					"Procurement Officer",
					"School Operations Manager",
					"EduEdge Parent",
				],
			]
		],
	},
]
