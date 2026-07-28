from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.platform.access import require_eduedge_access
from eduedge.services.institution_context import get_effective_institution_context


MAX_ROWS = 500
MAX_PERIOD_ROWS = 2000


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


@frappe.whitelist()
def get_academic_foundation() -> dict:
	_require_login()
	institutions = []
	if frappe.has_permission("EduEdge Institution", "read"):
		institutions = frappe.get_list(
			"EduEdge Institution",
			filters={"enabled": 1},
			fields=["name", "institution_name", "institution_code", "institution_type", "company"],
			order_by="institution_name asc",
			limit_page_length=MAX_ROWS,
		)
	sections = _safe_list(
		"EduEdge Academic Section",
		["name", "section_name", "section_code", "institution", "sequence", "enabled", "description"],
		"institution asc, sequence asc, section_name asc",
	)
	levels = _safe_list(
		"EduEdge Academic Level",
		[
			"name",
			"level_name",
			"level_code",
			"institution",
			"academic_section",
			"sequence",
			"next_level",
			"enabled",
			"description",
		],
		"institution asc, sequence asc, level_name asc",
	)
	calendars = [
		dict(row)
		for row in _safe_list(
			"EduEdge Institution Academic Calendar",
			[
				"name",
				"institution",
				"academic_year",
				"is_current",
				"enabled",
				"start_date",
				"end_date",
				"notes",
				"modified",
			],
			"institution asc, is_current desc, start_date desc",
		)
	]
	_attach_calendar_periods(calendars)
	progression = _build_progression(levels, sections)
	readiness = _build_readiness(institutions, sections, levels, calendars, progression)

	return {
		"active_context": get_effective_institution_context(),
		"institutions": institutions,
		"sections": sections,
		"levels": levels,
		"calendars": calendars,
		"progression": progression,
		"readiness": readiness,
		"today": nowdate(),
		"permissions": {
			"can_create_section": bool(frappe.has_permission("EduEdge Academic Section", "create")),
			"can_write_section": bool(frappe.has_permission("EduEdge Academic Section", "write")),
			"can_create_level": bool(frappe.has_permission("EduEdge Academic Level", "create")),
			"can_write_level": bool(frappe.has_permission("EduEdge Academic Level", "write")),
			"can_create_calendar": bool(
				frappe.has_permission("EduEdge Institution Academic Calendar", "create")
			),
			"can_write_calendar": bool(
				frappe.has_permission("EduEdge Institution Academic Calendar", "write")
			),
		},
	}


def _safe_list(doctype: str, fields: list[str], order_by: str) -> list[dict]:
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return []
	return frappe.get_list(
		doctype,
		fields=fields,
		order_by=order_by,
		limit_page_length=MAX_ROWS,
	)


def _attach_calendar_periods(calendars: list[dict]) -> None:
	if not calendars or not frappe.db.exists("DocType", "EduEdge Academic Calendar Period"):
		return

	calendar_names = [row.get("name") for row in calendars if row.get("name")]
	periods = frappe.get_all(
		"EduEdge Academic Calendar Period",
		filters={
			"parent": ["in", calendar_names],
			"parenttype": "EduEdge Institution Academic Calendar",
		},
		fields=[
			"name",
			"parent",
			"academic_term",
			"start_date",
			"end_date",
			"sequence",
			"result_publication_date",
		],
		order_by="parent asc, sequence asc, start_date asc",
		limit_page_length=MAX_PERIOD_ROWS,
	)
	by_calendar: dict[str, list[dict]] = defaultdict(list)
	for row in periods:
		by_calendar[row.parent].append(dict(row))

	today = getdate(nowdate())
	for calendar in calendars:
		rows = by_calendar.get(calendar["name"], [])
		current_period = next(
			(
				row
				for row in rows
				if row.get("start_date")
				and row.get("end_date")
				and getdate(row["start_date"]) <= today <= getdate(row["end_date"])
			),
			None,
		)
		calendar["periods"] = rows
		calendar["period_count"] = len(rows)
		calendar["current_period"] = current_period
		calendar["contains_today"] = bool(
			calendar.get("start_date")
			and calendar.get("end_date")
			and getdate(calendar["start_date"]) <= today <= getdate(calendar["end_date"])
		)
		calendar["has_calendar_gap_today"] = bool(
			calendar.get("enabled") and calendar["contains_today"] and not current_period
		)


def _build_progression(levels: list[dict], sections: list[dict]) -> dict[str, dict]:
	section_names = {row.name: row.section_name for row in sections}
	by_institution: dict[str, list[dict]] = defaultdict(list)
	for row in levels:
		if cint(row.enabled):
			by_institution[row.institution].append(dict(row))

	result: dict[str, dict] = {}
	for institution, institution_levels in by_institution.items():
		ordered = sorted(
			institution_levels,
			key=lambda row: (cint(row.get("sequence")) or 10, row.get("level_name") or ""),
		)
		by_name = {row["name"]: row for row in ordered}
		incoming = {name: 0 for name in by_name}
		gaps = []
		for row in ordered:
			target = row.get("next_level")
			if not target:
				continue
			if target in by_name:
				incoming[target] += 1
			else:
				gaps.append(
					{
						"level": row["name"],
						"level_name": row.get("level_name"),
						"next_level": target,
						"reason": _("Next level is missing or disabled."),
					}
				)

		roots = [row for row in ordered if incoming[row["name"]] == 0]
		chains = []
		visited: set[str] = set()
		for root in roots:
			chain = _walk_progression_chain(root, by_name, visited, section_names)
			if chain:
				chains.append(chain)
		for row in ordered:
			if row["name"] not in visited:
				chain = _walk_progression_chain(row, by_name, visited, section_names)
				if chain:
					chains.append(chain)

		result[institution] = {
			"chains": chains,
			"gaps": gaps,
			"enabled_level_count": len(ordered),
			"terminal_level_count": sum(1 for row in ordered if not row.get("next_level")),
		}
	return result


def _walk_progression_chain(
	root: dict,
	by_name: dict[str, dict],
	visited: set[str],
	section_names: dict[str, str],
) -> dict | None:
	if root["name"] in visited:
		return None

	levels = []
	current = root
	local_seen: set[str] = set()
	while current and current["name"] not in local_seen:
		local_seen.add(current["name"])
		visited.add(current["name"])
		levels.append(
			{
				"name": current["name"],
				"level_name": current.get("level_name"),
				"level_code": current.get("level_code"),
				"academic_section": current.get("academic_section"),
				"academic_section_name": section_names.get(current.get("academic_section")),
				"sequence": current.get("sequence"),
				"next_level": current.get("next_level"),
			}
		)
		current = by_name.get(current.get("next_level"))

	return {
		"root": root["name"],
		"section": root.get("academic_section"),
		"section_name": section_names.get(root.get("academic_section")),
		"levels": levels,
	}


def _build_readiness(
	institutions: list[dict],
	sections: list[dict],
	levels: list[dict],
	calendars: list[dict],
	progression: dict[str, dict],
) -> list[dict]:
	sections_by_institution: dict[str, list[dict]] = defaultdict(list)
	levels_by_institution: dict[str, list[dict]] = defaultdict(list)
	calendars_by_institution: dict[str, list[dict]] = defaultdict(list)
	for row in sections:
		if cint(row.enabled):
			sections_by_institution[row.institution].append(row)
	for row in levels:
		if cint(row.enabled):
			levels_by_institution[row.institution].append(row)
	for row in calendars:
		if cint(row.get("enabled")):
			calendars_by_institution[row["institution"]].append(row)

	result = []
	for institution in institutions:
		name = institution.name
		enabled_sections = sections_by_institution.get(name, [])
		enabled_levels = levels_by_institution.get(name, [])
		enabled_calendars = calendars_by_institution.get(name, [])
		current_calendar = next(
			(row for row in enabled_calendars if cint(row.get("is_current"))),
			None,
		)
		issues = []
		if not enabled_sections:
			issues.append(
				{
					"code": "no_sections",
					"severity": "warning",
					"message": _("No enabled Academic Section is configured."),
				}
			)
		if not enabled_levels:
			issues.append(
				{
					"code": "no_levels",
					"severity": "danger",
					"message": _("No enabled Academic Level is configured."),
				}
			)
		if not current_calendar:
			issues.append(
				{
					"code": "no_current_calendar",
					"severity": "danger",
					"message": _("No enabled current Institution Academic Calendar is configured."),
				}
			)
		else:
			if not current_calendar.get("period_count"):
				issues.append(
					{
						"code": "calendar_without_periods",
						"severity": "danger",
						"message": _("The current calendar has no Academic Periods."),
					}
				)
			if current_calendar.get("has_calendar_gap_today"):
				issues.append(
					{
						"code": "calendar_gap",
						"severity": "warning",
						"message": _("Today falls inside the calendar but outside every configured Academic Period."),
					}
				)

		levels_without_section = [
			row for row in enabled_levels if enabled_sections and not row.get("academic_section")
		]
		if levels_without_section:
			issues.append(
				{
					"code": "levels_without_section",
					"severity": "warning",
					"message": _("{0} enabled Academic Level(s) are not assigned to an Academic Section.").format(
						len(levels_without_section)
					),
				}
			)
		progression_gaps = progression.get(name, {}).get("gaps", [])
		if progression_gaps:
			issues.append(
				{
					"code": "progression_gap",
					"severity": "danger",
					"message": _("{0} progression link(s) point to missing or disabled Levels.").format(
						len(progression_gaps)
					),
				}
			)

		result.append(
			{
				"institution": name,
				"ready": not any(issue["severity"] == "danger" for issue in issues),
				"issues": issues,
				"enabled_sections": len(enabled_sections),
				"enabled_levels": len(enabled_levels),
				"enabled_calendars": len(enabled_calendars),
				"current_calendar": current_calendar.get("name") if current_calendar else None,
			}
		)
	return result


@frappe.whitelist()
def save_academic_section(
	institution: str,
	section_name: str,
	section_code: str,
	section: str | None = None,
	sequence: int | str = 10,
	enabled: int | str = 1,
	description: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_academic_section")
	if section:
		doc = frappe.get_doc("EduEdge Academic Section", section)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("EduEdge Academic Section", "create"):
			frappe.throw(_("You are not permitted to create Academic Sections."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge Academic Section")
	doc.update(
		{
			"institution": institution,
			"section_name": str(section_name or "").strip(),
			"section_code": str(section_code or "").strip(),
			"sequence": cint(sequence) or 10,
			"enabled": cint(enabled),
			"description": description or "",
		}
	)
	doc.save()
	return {"name": doc.name, "section_name": doc.section_name}


@frappe.whitelist()
def save_academic_level(
	institution: str,
	level_name: str,
	level_code: str,
	level: str | None = None,
	academic_section: str | None = None,
	sequence: int | str = 10,
	next_level: str | None = None,
	enabled: int | str = 1,
	description: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_academic_level")
	if level:
		doc = frappe.get_doc("EduEdge Academic Level", level)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("EduEdge Academic Level", "create"):
			frappe.throw(_("You are not permitted to create Academic Levels."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge Academic Level")
	doc.update(
		{
			"institution": institution,
			"level_name": str(level_name or "").strip(),
			"level_code": str(level_code or "").strip(),
			"academic_section": academic_section or None,
			"sequence": cint(sequence) or 10,
			"next_level": next_level or None,
			"enabled": cint(enabled),
			"description": description or "",
		}
	)
	doc.save()
	return {"name": doc.name, "level_name": doc.level_name}
