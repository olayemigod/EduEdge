from __future__ import annotations

import re
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt

COMPONENT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

METRIC_KEYS = {
	"Class Highest",
	"Class Lowest",
	"Class Average",
	"Pass Rate",
	"Subject Position",
	"Percentile",
	"Student Percentage",
}
METRIC_BASES = {
	"Current Term Raw Score",
	"Current Term Percentage",
	"Year-to-Date Cumulative Raw Score",
	"Annual Cumulative Raw Score",
	"Annual Average Percentage",
}
METRIC_DISPLAY_TYPES = {"Raw Score", "Percentage", "Number", "Grade"}
ANNUAL_AGGREGATION_METHODS = {
	"Equal Average of Eligible Terms",
	"Weighted Average",
	"Raw Cumulative",
}
MISSING_RESULT_POLICIES = {"Block Publication", "Exclude from Denominator"}
ABSENCE_POLICIES = {"Block Publication", "Exclude from Denominator", "Treat as Zero"}


def validate_result_profile(doc) -> None:
	_validate_scope(doc)
	_validate_calculation_settings(doc)
	_validate_components(doc)
	_validate_sources(doc)
	_validate_metrics(doc)
	_validate_default(doc)


def validate_publication_profile(doc) -> None:
	"""Validate optional V1 result-profile context without breaking historical publications."""
	if not doc.get("result_profile"):
		return

	profile = frappe.get_doc("EduEdge Result Profile", doc.result_profile)
	if not profile.is_active:
		frappe.throw(_("Select an active Result Profile."), frappe.ValidationError)

	branch = frappe.db.get_value(
		"EduEdge School Branch",
		doc.school_branch,
		["institution", "enabled"],
		as_dict=True,
	)
	if not branch or not branch.enabled:
		frappe.throw(_("Result Publication requires an enabled School Branch / Campus."), frappe.ValidationError)
	if profile.institution != branch.institution:
		frappe.throw(
			_("Result Profile must belong to the same Institution as the Result Publication."),
			frappe.ValidationError,
		)
	if profile.school_branch and profile.school_branch != doc.school_branch:
		frappe.throw(
			_("This Result Profile is restricted to a different School Branch / Campus."),
			frappe.ValidationError,
		)

	result_mode = doc.get("result_mode") or "Terminal"
	if result_mode == "Annual" and doc.academic_term:
		frappe.throw(
			_("Annual Result Publications must use the Academic Year scope without a single Academic Term."),
			frappe.ValidationError,
		)


def get_result_profile_config(name: str) -> dict:
	doc = frappe.get_doc("EduEdge Result Profile", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"profile_name": doc.profile_name,
		"institution": doc.institution,
		"school_branch": doc.school_branch,
		"grading_scale": doc.grading_scale,
		"score_precision": cint(doc.score_precision),
		"annual_aggregation_method": doc.annual_aggregation_method,
		"minimum_eligible_periods": cint(doc.minimum_eligible_periods),
		"missing_result_policy": doc.missing_result_policy,
		"absence_policy": doc.absence_policy,
		"components": [
			{
				"component_key": row.component_key,
				"component_label": row.component_label,
				"target_maximum_score": flt(row.target_maximum_score),
				"sequence": cint(row.sequence),
				"show_on_terminal": bool(row.show_on_terminal),
				"show_on_annual": bool(row.show_on_annual),
			}
			for row in sorted(doc.components, key=lambda row: (cint(row.sequence), row.idx))
		],
		"component_sources": [
			{
				"component_key": row.component_key,
				"assessment_group": row.assessment_group,
				"sequence": cint(row.sequence),
				"leaf_assessment_groups": resolve_assessment_group_leaves(row.assessment_group),
			}
			for row in sorted(doc.component_sources, key=lambda row: (cint(row.sequence), row.idx))
		],
		"metrics": [
			{
				"metric_key": row.metric_key,
				"display_label": row.display_label,
				"calculation_basis": row.calculation_basis,
				"display_as": row.display_as,
				"decimal_places": cint(row.decimal_places),
				"sequence": cint(row.sequence),
				"show_on_terminal": bool(row.show_on_terminal),
				"show_on_annual": bool(row.show_on_annual),
			}
			for row in sorted(doc.metrics, key=lambda row: (cint(row.sequence), row.idx))
		],
	}


def resolve_assessment_group_leaves(assessment_group: str) -> list[str]:
	"""Resolve all leaf Assessment Groups recursively.

	Frappe Education's report helper is intentionally not used here because the
	EduEdge result engine must support nested Assessment Group trees of arbitrary
	depth without forcing schools to flatten their assessment structures.
	"""
	if not assessment_group:
		return []
	group = frappe.db.get_value(
		"Assessment Group",
		assessment_group,
		["name", "is_group", "lft", "rgt"],
		as_dict=True,
	)
	if not group:
		frappe.throw(
			_("Assessment Group {0} does not exist.").format(assessment_group),
			frappe.DoesNotExistError,
		)
	if not group.is_group:
		return [group.name]

	return frappe.get_all(
		"Assessment Group",
		filters={
			"lft": [">", group.lft],
			"rgt": ["<", group.rgt],
			"is_group": 0,
		},
		pluck="name",
		order_by="lft asc",
	)


def get_component_source_index(profile: str | dict) -> dict[str, str]:
	config = get_result_profile_config(profile) if isinstance(profile, str) else profile
	index: dict[str, str] = {}
	for source in config.get("component_sources") or []:
		for leaf in source.get("leaf_assessment_groups") or []:
			existing = index.get(leaf)
			if existing and existing != source["component_key"]:
				frappe.throw(
					_("Assessment Group {0} is mapped to more than one Result Component.").format(leaf),
					frappe.ValidationError,
				)
			index[leaf] = source["component_key"]
	return index


def _validate_scope(doc) -> None:
	institution = frappe.db.get_value(
		"EduEdge Institution",
		doc.institution,
		["name", "enabled"],
		as_dict=True,
	)
	if not institution or not institution.enabled:
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)

	if doc.school_branch:
		branch = frappe.db.get_value(
			"EduEdge School Branch",
			doc.school_branch,
			["institution", "enabled"],
			as_dict=True,
		)
		if not branch or not branch.enabled:
			frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
		if branch.institution != doc.institution:
			frappe.throw(
				_("Result Profile Branch / Campus must belong to the selected Institution."),
				frappe.ValidationError,
			)


def _validate_calculation_settings(doc) -> None:
	if doc.annual_aggregation_method not in ANNUAL_AGGREGATION_METHODS:
		frappe.throw(_("Invalid annual aggregation method."), frappe.ValidationError)
	if doc.missing_result_policy not in MISSING_RESULT_POLICIES:
		frappe.throw(_("Invalid missing-result policy."), frappe.ValidationError)
	if doc.absence_policy not in ABSENCE_POLICIES:
		frappe.throw(_("Invalid absence policy."), frappe.ValidationError)
	if cint(doc.minimum_eligible_periods) < 1:
		frappe.throw(_("Minimum Eligible Periods must be at least 1."), frappe.ValidationError)
	if not 0 <= cint(doc.score_precision) <= 6:
		frappe.throw(_("Score Precision must be between 0 and 6."), frappe.ValidationError)


def _validate_components(doc) -> None:
	if not doc.components:
		frappe.throw(_("Add at least one Result Component."), frappe.ValidationError)

	keys: set[str] = set()
	for row in doc.components:
		key = (row.component_key or "").strip().lower()
		if not COMPONENT_KEY_PATTERN.fullmatch(key):
			frappe.throw(
				_("Component Key {0} must use lowercase letters, numbers and underscores only.").format(
					row.component_key or _("(blank)")
				),
				frappe.ValidationError,
			)
		row.component_key = key
		if key in keys:
			frappe.throw(
				_("Result Component {0} appears more than once.").format(key),
				frappe.ValidationError,
			)
		keys.add(key)
		if flt(row.target_maximum_score) < 0:
			frappe.throw(_("Target Maximum Score cannot be negative."), frappe.ValidationError)


def _validate_sources(doc) -> None:
	component_keys = {row.component_key for row in doc.components}
	seen_groups: set[str] = set()
	if not doc.component_sources:
		frappe.throw(_("Map at least one Assessment Group to a Result Component."), frappe.ValidationError)

	for row in doc.component_sources:
		row.component_key = (row.component_key or "").strip().lower()
		if row.component_key not in component_keys:
			frappe.throw(
				_("Assessment source Component Key {0} is not defined in Result Components.").format(
					row.component_key or _("(blank)")
				),
				frappe.ValidationError,
			)
		if row.assessment_group in seen_groups:
			frappe.throw(
				_("Assessment Group {0} is mapped more than once.").format(row.assessment_group),
				frappe.ValidationError,
			)
		seen_groups.add(row.assessment_group)
		resolve_assessment_group_leaves(row.assessment_group)

	leaf_owners: dict[str, str] = {}
	for row in doc.component_sources:
		for leaf in resolve_assessment_group_leaves(row.assessment_group):
			owner = leaf_owners.get(leaf)
			if owner and owner != row.component_key:
				frappe.throw(
					_("Assessment Group leaf {0} resolves into multiple Result Components.").format(leaf),
					frappe.ValidationError,
				)
			leaf_owners[leaf] = row.component_key


def _validate_metrics(doc) -> None:
	seen: set[tuple[str, str]] = set()
	for row in doc.metrics:
		if row.metric_key not in METRIC_KEYS:
			frappe.throw(_("Invalid report statistic."), frappe.ValidationError)
		if row.calculation_basis not in METRIC_BASES:
			frappe.throw(_("Invalid statistic calculation basis."), frappe.ValidationError)
		if row.display_as not in METRIC_DISPLAY_TYPES:
			frappe.throw(_("Invalid statistic display type."), frappe.ValidationError)
		if not (row.display_label or "").strip():
			frappe.throw(_("Every enabled report statistic needs a Display Label."), frappe.ValidationError)
		if not 0 <= cint(row.decimal_places) <= 6:
			frappe.throw(_("Metric decimal places must be between 0 and 6."), frappe.ValidationError)
		key = (row.metric_key, row.calculation_basis)
		if key in seen:
			frappe.throw(
				_("Statistic {0} with basis {1} appears more than once.").format(*key),
				frappe.ValidationError,
			)
		seen.add(key)


def _validate_default(doc) -> None:
	if not doc.is_default or not doc.is_active:
		return
	filters = {
		"name": ["!=", doc.name],
		"institution": doc.institution,
		"school_branch": doc.school_branch or "",
		"is_default": 1,
		"is_active": 1,
	}
	duplicate = frappe.db.exists("EduEdge Result Profile", filters)
	if duplicate:
		frappe.throw(
			_("Result Profile {0} is already the active default for this scope.").format(duplicate),
			frappe.DuplicateEntryError,
		)
