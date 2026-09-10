from __future__ import annotations

from typing import Any

import frappe

CANDIDATE_LIMIT = 100
MAX_ANCHORS = 4


def query_anchors(query: str) -> tuple[str, ...]:
	term = " ".join(str(query or "").strip().casefold().split())
	if not term:
		return ()
	anchors = [term]
	for token in term.split():
		if len(token) >= 3:
			anchors.append(token[:3])
		if len(token) >= 2:
			anchors.append(token[-2:])
	unique: list[str] = []
	for anchor in anchors:
		if anchor and anchor not in unique:
			unique.append(anchor)
		if len(unique) >= MAX_ANCHORS:
			break
	return tuple(unique)


def get_bounded_candidates(
	doctype: str,
	*,
	filters: dict[str, Any] | None,
	fields: list[str],
	query: str,
	search_fields: tuple[str, ...],
	order_by: str,
	candidate_limit: int = CANDIDATE_LIMIT,
) -> list[dict[str, Any]]:
	"""Query the full permission-filtered scope with bounded lexical anchors."""
	candidate_limit = min(max(int(candidate_limit or CANDIDATE_LIMIT), 1), CANDIDATE_LIMIT)
	search_text = str(query or "").strip()
	if not search_text:
		return [
			dict(row)
			for row in frappe.get_list(
				doctype,
				filters=filters or {},
				fields=fields,
				order_by=order_by,
				page_length=candidate_limit,
			)
		]

	meta = frappe.get_meta(doctype)
	available_search = tuple(
		fieldname
		for fieldname in dict.fromkeys(("name", *search_fields))
		if fieldname == "name" or meta.has_field(fieldname)
	)
	rows: list[dict[str, Any]] = []
	seen: set[str] = set()

	exact = frappe.get_list(
		doctype,
		filters=filters or {},
		or_filters={fieldname: search_text for fieldname in available_search},
		fields=fields,
		order_by=order_by,
		page_length=candidate_limit,
	)
	for source in exact:
		row = dict(source)
		name = str(row.get("name") or "")
		if name and name not in seen:
			seen.add(name)
			rows.append(row)

	for anchor in query_anchors(search_text):
		remaining = candidate_limit - len(rows)
		if remaining <= 0:
			break
		matches = frappe.get_list(
			doctype,
			filters=filters or {},
			or_filters={fieldname: ["like", f"%{anchor}%"] for fieldname in available_search},
			fields=fields,
			order_by=order_by,
			page_length=remaining,
		)
		for source in matches:
			row = dict(source)
			name = str(row.get("name") or "")
			if not name or name in seen:
				continue
			seen.add(name)
			rows.append(row)
			if len(rows) >= candidate_limit:
				break

	return rows


def rank_link_candidates(
	rows: list[dict[str, Any]],
	query: str,
	*,
	exact_fields: tuple[str, ...] = ("value",),
	search_fields: tuple[str, ...] = ("label", "description"),
	limit: int = CANDIDATE_LIMIT,
) -> list[dict[str, Any]]:
	"""Rank an already permission-scoped candidate set with EdgeSuite when available."""
	limit = min(max(int(limit or CANDIDATE_LIMIT), 1), CANDIDATE_LIMIT)
	try:
		from edgesuite_ui.search_ranking import rank_search_records
	except (ImportError, ModuleNotFoundError):
		return rows[:limit]

	return list(
		rank_search_records(
			rows,
			query or "",
			exact_fields=exact_fields,
			search_fields=search_fields,
			limit=limit,
		)
	)


def rank_link_rows(
	rows: list[dict[str, Any]],
	query: str,
	*,
	exact_fields: tuple[str, ...] = ("value",),
	search_fields: tuple[str, ...] = ("label", "description"),
	start: int = 0,
	page_length: int = 20,
) -> list[dict[str, Any]]:
	"""Rank and page an already permission-scoped candidate set."""
	start = max(int(start or 0), 0)
	page_length = min(max(int(page_length or 20), 1), 50)
	ranked = rank_link_candidates(
		rows,
		query,
		exact_fields=exact_fields,
		search_fields=search_fields,
	)
	return ranked[start : start + page_length]
