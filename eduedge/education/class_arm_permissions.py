from __future__ import annotations

from eduedge.education.permissions import _branch_condition, has_school_branch_permission


def class_arm_query(user: str | None = None) -> str:
	return _branch_condition("EduEdge Class Arm", user, fieldname="school_branch")


def has_class_arm_permission(doc, user=None, permission_type=None) -> bool:
	return has_school_branch_permission(doc, user, permission_type)
