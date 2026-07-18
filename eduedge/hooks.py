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
