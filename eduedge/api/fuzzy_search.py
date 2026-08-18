from __future__ import annotations

from typing import Any

CANDIDATE_LIMIT = 100


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
