from __future__ import annotations

from collections import defaultdict

import frappe

QUESTION_DOCTYPE = "EduEdge CBT Question"


def execute() -> None:
	"""Convert legacy free-text question topics into Course-linked Topic masters."""
	if not frappe.db.table_exists(QUESTION_DOCTYPE):
		return
	if not frappe.db.exists("DocType", "Topic") or not frappe.db.exists("DocType", "Course Topic"):
		return

	questions = frappe.get_all(
		QUESTION_DOCTYPE,
		filters={"topic": ["not in", ["", None]]},
		fields=["name", "course", "topic"],
		limit_page_length=0,
	)
	course_topics: dict[str, set[str]] = defaultdict(set)

	for question in questions:
		course = (question.course or "").strip()
		legacy_topic = (question.topic or "").strip()
		if not course or not legacy_topic or not frappe.db.exists("Course", course):
			continue

		topic = frappe.db.get_value("Topic", {"topic_name": legacy_topic}, "name")
		if not topic:
			topic_doc = frappe.get_doc(
				{
					"doctype": "Topic",
					"topic_name": legacy_topic,
					"description": "Created from an existing EduEdge CBT Question during topic-master migration.",
				}
			).insert(ignore_permissions=True)
			topic = topic_doc.name

		if question.topic != topic:
			frappe.db.set_value(
				QUESTION_DOCTYPE,
				question.name,
				"topic",
				topic,
				update_modified=False,
			)
		course_topics[course].add(topic)

	for course, topics in course_topics.items():
		course_doc = frappe.get_doc("Course", course)
		existing = {row.topic for row in (course_doc.get("topics") or []) if row.topic}
		changed = False
		for topic in sorted(topics):
			if topic in existing:
				continue
			course_doc.append("topics", {"topic": topic})
			existing.add(topic)
			changed = True
		if changed:
			course_doc.save(ignore_permissions=True)
