from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _

APP_ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROOT = APP_ROOT / "docs" / "training" / "eduedge"
TRAINING_MANIFESTS = (
	TRAINING_ROOT / "training_modules.json",
	TRAINING_ROOT / "training_modules_school_operations.json",
)

AUDIENCES = {
	"shared": {
		"label": "All Users",
		"description": "Navigation, profile, support, and safe-use basics shared across EduEdge.",
		"roles": set(),
		"order": 0,
	},
	"student": {
		"label": "Students",
		"description": "Access learning activities, CBT, results, report cards and support safely.",
		"roles": {"Student"},
		"order": 10,
	},
	"parent": {
		"label": "Parents / Guardians",
		"description": "Use the Parent Portal, linked-child records, notices, fees, results and pickup controls safely.",
		"roles": {"EduEdge Parent"},
		"order": 15,
	},
	"teacher": {
		"label": "Teachers",
		"description": "Run classes, attendance, assessments, result entry and report-card handoffs.",
		"roles": {"Teacher", "Instructor"},
		"order": 20,
	},
	"registrar": {
		"label": "Registrar / Admissions",
		"description": "Manage admissions, applicants, student identity, guardians, enrolment and record lifecycle.",
		"roles": {"Registrar", "Admission Officer"},
		"order": 25,
	},
	"finance": {
		"label": "Bursary / Accounts",
		"description": "Operate fees, receipts, allocations, reconciliation, payables and financial reporting safely.",
		"roles": {"Bursar", "Accounts User", "Accounts Manager"},
		"order": 30,
	},
	"people_ops": {
		"label": "HR / People Operations",
		"description": "Manage staff records, onboarding, leave, attendance, payroll and separation when HRMS is installed.",
		"roles": {"HR User", "HR Manager", "School HR Officer"},
		"order": 35,
	},
	"procurement_assets": {
		"label": "Procurement, Stores and Assets",
		"description": "Control school purchasing, receiving, stores, inventory, assets and custody evidence.",
		"roles": {
			"Purchase User",
			"Purchase Manager",
			"Stock User",
			"Stock Manager",
			"Asset User",
			"Asset Manager",
			"Procurement Officer",
		},
		"order": 40,
	},
	"school_operations": {
		"label": "School Operations and Management",
		"description": "Coordinate facilities, communications, approvals, reports, incidents and cross-functional follow-up.",
		"roles": {"School Operations Manager", "School Administrator"},
		"order": 45,
	},
	"cbt_ops": {
		"label": "CBT Operations",
		"description": "Prepare examinations, verify candidates, monitor integrity and resolve pending answer sync.",
		"roles": {"CBT Invigilator"},
		"order": 50,
	},
	"student_safety": {
		"label": "Student Safety and Pickup",
		"description": "Control student release, school-bus handoffs, incidents and parent notification evidence.",
		"roles": {"Student Safety Officer"},
		"order": 55,
	},
	"school_admin": {
		"label": "Academic and School Administration",
		"description": "Configure branches, programmes, staff access and daily academic operations.",
		"roles": {"School Administrator", "Academic Administrator"},
		"order": 60,
	},
	"school_owner": {
		"label": "School Owners / System Managers",
		"description": "Govern access, readiness, approvals, reporting and platform accountability.",
		"roles": {"System Manager", "EduEdge Administrator"},
		"order": 70,
	},
	"processedge_staff": {
		"label": "ProcessEdge Super Administrators",
		"description": "Provision, activate, support, upgrade, diagnose and hand over EduEdge tenants safely.",
		"roles": {"EduEdge Super Administrator"},
		"order": 80,
	},
}

VIDEO_STATUSES = {"Not Recorded", "Recorded", "Published", "Needs Review"}
ALLOWED_YOUTUBE_HOSTS = {
	"youtube.com",
	"www.youtube.com",
	"youtu.be",
	"www.youtu.be",
	"youtube-nocookie.com",
	"www.youtube-nocookie.com",
}
YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def user_roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def allowed_audience_keys(user: str | None = None) -> list[str]:
	roles = user_roles(user)
	if "EduEdge Super Administrator" in roles:
		return list(AUDIENCES)
	if roles & AUDIENCES["school_owner"]["roles"]:
		return [key for key in AUDIENCES if key != "processedge_staff"]
	allowed = ["shared"]
	for key, config in AUDIENCES.items():
		if key != "shared" and roles & config["roles"]:
			allowed.append(key)
	return allowed


def primary_audience(user: str | None = None) -> str:
	allowed = allowed_audience_keys(user)
	for key in (
		"processedge_staff",
		"school_owner",
		"school_admin",
		"school_operations",
		"finance",
		"registrar",
		"people_ops",
		"procurement_assets",
		"cbt_ops",
		"student_safety",
		"teacher",
		"parent",
		"student",
	):
		if key in allowed:
			return key
	return "shared"


def _read_manifest(path: Path) -> list[dict]:
	if not path.exists():
		frappe.throw(
			_("EduEdge training module setup was not found: {0}").format(path.name),
			frappe.DoesNotExistError,
		)
	try:
		raw = json.loads(path.read_text(encoding="utf-8"))
	except json.JSONDecodeError as error:
		frappe.throw(_("EduEdge training module setup is invalid in {0}: {1}").format(path.name, error))
	if not isinstance(raw, list):
		frappe.throw(_("EduEdge training module setup must contain a list: {0}").format(path.name))
	return raw


def load_manifest() -> list[dict]:
	raw_modules = []
	for manifest_path in TRAINING_MANIFESTS:
		raw_modules.extend(_read_manifest(manifest_path))
	modules = [normalize_module(row) for row in raw_modules]
	seen: set[str] = set()
	for module in modules:
		if module["module_id"] in seen:
			frappe.throw(_("Duplicate training module ID: {0}").format(module["module_id"]))
		seen.add(module["module_id"])
	return sorted(
		modules,
		key=lambda row: (AUDIENCES[row["audience"]]["order"], row["order"], row["title"]),
	)


def normalize_module(row: dict) -> dict:
	if not isinstance(row, dict):
		frappe.throw(_("EduEdge training module setup contains an invalid row."))
	for fieldname in (
		"module_id",
		"title",
		"audience",
		"category",
		"short_description",
		"markdown_path",
		"status",
		"order",
		"estimated_minutes",
		"content_version",
		"steps",
	):
		if row.get(fieldname) is None:
			frappe.throw(_("Training module is missing {0}.").format(fieldname))
	module_id = str(row["module_id"]).strip()
	if not ID_RE.match(module_id):
		frappe.throw(_("Training module ID {0} is invalid.").format(module_id))
	audience = str(row["audience"]).strip()
	if audience not in AUDIENCES:
		frappe.throw(_("Training module {0} has an unknown audience.").format(module_id))
	video_status = str(row.get("video_status") or "Not Recorded").strip()
	if video_status not in VIDEO_STATUSES:
		frappe.throw(_("Training module {0} has an invalid video status.").format(module_id))
	module = {
		"module_id": module_id,
		"title": str(row["title"]).strip(),
		"audience": audience,
		"role_group": AUDIENCES[audience]["label"],
		"category": str(row["category"]).strip(),
		"short_description": str(row["short_description"]).strip(),
		"markdown_path": str(row["markdown_path"]).strip(),
		"youtube_url": str(row.get("youtube_url") or "").strip(),
		"video_title": str(row.get("video_title") or row["title"]).strip(),
		"video_status": video_status,
		"status": str(row["status"]).strip(),
		"order": int(row["order"] or 0),
		"estimated_minutes": max(1, int(row["estimated_minutes"] or 1)),
		"content_version": max(1, int(row["content_version"] or 1)),
		"prerequisites": [str(item).strip() for item in row.get("prerequisites") or [] if str(item).strip()],
		"required_apps": [str(item).strip().lower() for item in row.get("required_apps") or [] if str(item).strip()],
		"required_doctypes": [str(item).strip() for item in row.get("required_doctypes") or [] if str(item).strip()],
		"steps": normalize_steps(row["steps"], module_id),
	}
	module["video_embed_url"] = safe_youtube_embed_url(module["youtube_url"])
	module["has_video"] = bool(module["video_embed_url"])
	module["video_display_status"] = video_display_status(module["youtube_url"], video_status)
	resolve_markdown_path(module)
	return module


def normalize_steps(rows, module_id: str) -> list[dict]:
	if not isinstance(rows, list) or not rows:
		frappe.throw(_("Training module {0} requires guided steps.").format(module_id))
	result = []
	seen: set[str] = set()
	for index, row in enumerate(rows, start=1):
		if not isinstance(row, dict):
			frappe.throw(_("Training module {0} contains an invalid step.").format(module_id))
		step_id = str(row.get("step_id") or "").strip()
		if not ID_RE.match(step_id) or step_id in seen:
			frappe.throw(_("Training module {0} contains an invalid or duplicate step ID.").format(module_id))
		seen.add(step_id)
		result.append(
			{
				"step_id": step_id,
				"title": str(row.get("title") or "").strip(),
				"description": str(row.get("description") or "").strip(),
				"action_label": str(row.get("action_label") or "").strip(),
				"action_route": str(row.get("action_route") or "").strip(),
				"order": int(row.get("order") or index),
			}
		)
	return sorted(result, key=lambda item: item["order"])


def resolve_markdown_path(module: dict) -> Path:
	path = Path(module.get("markdown_path") or "")
	if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".md":
		frappe.throw(_("Training module path is not allowed."))
	resolved = (APP_ROOT / path).resolve()
	if not resolved.is_relative_to(TRAINING_ROOT.resolve()):
		frappe.throw(_("Training module path is outside the approved training folder."))
	return resolved


def read_markdown(module: dict) -> str:
	path = resolve_markdown_path(module)
	if not path.exists():
		frappe.throw(_("Training guide was not found: {0}").format(path.name), frappe.DoesNotExistError)
	return path.read_text(encoding="utf-8")


def safe_youtube_embed_url(url: str | None) -> str:
	url = str(url or "").strip()
	if not url:
		return ""
	parsed = urlparse(url)
	if parsed.scheme != "https" or (parsed.netloc or "").lower() not in ALLOWED_YOUTUBE_HOSTS:
		return ""
	host = parsed.netloc.lower()
	video_id = ""
	if host in {"youtu.be", "www.youtu.be"}:
		video_id = parsed.path.strip("/").split("/")[0]
	elif parsed.path.startswith("/watch"):
		video_id = parse_qs(parsed.query).get("v", [""])[0]
	elif parsed.path.startswith("/embed/"):
		video_id = parsed.path.split("/embed/", 1)[1].split("/")[0]
	if not video_id or not YOUTUBE_ID_RE.match(video_id):
		return ""
	return f"https://www.youtube-nocookie.com/embed/{video_id}"


def video_display_status(url: str | None, status: str | None = None) -> str:
	if not url:
		return "Video coming soon"
	if safe_youtube_embed_url(url):
		return "Video available" if status != "Needs Review" else "Video link needs review"
	return "Video link needs review"


def module_by_id(module_id: str) -> dict:
	module_id = str(module_id or "").strip()
	for module in load_manifest():
		if module["module_id"] == module_id:
			return module
	frappe.throw(_("Training module was not found."), frappe.DoesNotExistError)


def module_availability(module: dict) -> dict:
	installed = {str(app).lower() for app in frappe.get_installed_apps()}
	missing_apps = [app for app in module.get("required_apps") or [] if app not in installed]
	missing_doctypes = [
		doctype
		for doctype in module.get("required_doctypes") or []
		if not frappe.db.exists("DocType", doctype)
	]
	available = not missing_apps and not missing_doctypes
	parts = []
	if missing_apps:
		parts.append(_("Install app(s): {0}").format(", ".join(missing_apps)))
	if missing_doctypes:
		parts.append(_("Required module records are unavailable: {0}").format(", ".join(missing_doctypes)))
	return {
		"available": available,
		"missing_apps": missing_apps,
		"missing_doctypes": missing_doctypes,
		"availability_message": " ".join(parts),
	}


def can_view_module(module: dict, user: str | None = None) -> bool:
	return module.get("status") == "Published" and module.get("audience") in allowed_audience_keys(user)


def visible_modules(user: str | None = None) -> list[dict]:
	allowed = set(allowed_audience_keys(user))
	return [
		module
		for module in load_manifest()
		if module["status"] == "Published" and module["audience"] in allowed
	]


def extract_heading_section(markdown: str, headings: set[str]) -> str:
	lines = (markdown or "").splitlines()
	start = None
	level = 0
	for index, line in enumerate(lines):
		match = re.match(r"^(#{2,6})\s+(.+?)\s*$", line)
		if match and match.group(2).strip().lower() in headings:
			start = index
			level = len(match.group(1))
			break
	if start is None:
		return ""
	end = len(lines)
	for index in range(start + 1, len(lines)):
		match = re.match(r"^(#{2,6})\s+", lines[index])
		if match and len(match.group(1)) <= level:
			end = index
			break
	return "\n".join(lines[start:end]).strip()


def screenshot_references(markdown: str) -> list[dict]:
	return [
		{"alt": alt.strip(), "path": path.strip()}
		for alt, path in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", markdown or "")
	]
