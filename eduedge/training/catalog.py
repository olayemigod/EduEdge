from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _

APP_ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROOT = APP_ROOT / "docs" / "training" / "eduedge"
TRAINING_MANIFEST = TRAINING_ROOT / "training_modules.json"

AUDIENCES = {
	"shared": {
		"label": "All Users",
		"description": "Navigation, profile, support, and safe-use basics shared across EduEdge.",
		"roles": set(),
		"order": 0,
	},
	"student": {
		"label": "Students",
		"description": "Learn how to access learning activities, CBT, results, and support safely.",
		"roles": {"Student"},
		"order": 10,
	},
	"teacher": {
		"label": "Teachers",
		"description": "Run classes, attendance, assessments, result entry, and report-card handoffs.",
		"roles": {"Teacher"},
		"order": 20,
	},
	"school_admin": {
		"label": "School Administration",
		"description": "Configure branches, programmes, admissions, staff access, and daily school operations.",
		"roles": {
			"School Administrator",
			"Academic Administrator",
			"Bursar",
			"CBT Invigilator",
			"Student Safety Officer",
		},
		"order": 30,
	},
	"school_owner": {
		"label": "School Owners / System Managers",
		"description": "Govern access, readiness, approvals, reporting, and platform access.",
		"roles": {"System Manager", "EduEdge Administrator"},
		"order": 40,
	},
	"processedge_staff": {
		"label": "ProcessEdge Super Administrators",
		"description": "Provision, activate, support, upgrade, diagnose, and hand over EduEdge tenants safely.",
		"roles": {"EduEdge Super Administrator"},
		"order": 50,
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
		return ["shared", "student", "teacher", "school_admin", "school_owner"]
	allowed = ["shared"]
	for key, config in AUDIENCES.items():
		if key != "shared" and roles & config["roles"]:
			allowed.append(key)
	return allowed


def primary_audience(user: str | None = None) -> str:
	allowed = allowed_audience_keys(user)
	for key in ("processedge_staff", "school_owner", "school_admin", "teacher", "student"):
		if key in allowed:
			return key
	return "shared"


def load_manifest() -> list[dict]:
	if not TRAINING_MANIFEST.exists():
		frappe.throw(_("EduEdge training module setup was not found."), frappe.DoesNotExistError)
	try:
		raw = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
	except json.JSONDecodeError as error:
		frappe.throw(_("EduEdge training module setup is invalid: {0}").format(error))
	if not isinstance(raw, list):
		frappe.throw(_("EduEdge training module setup must contain a list."))
	modules = [normalize_module(row) for row in raw]
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
