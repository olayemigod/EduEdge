import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
DOCTYPE_ROOT = ROOT / "eduedge" / "eduedge" / "doctype"
FRAPPE_SEARCH_FIELDS_MAX_LENGTH = 140


class TestDocTypeSearchFieldsMetadataContract(unittest.TestCase):
    def test_all_eduedge_doctype_search_fields_fit_frappe_metadata_limit(self):
        violations = []
        for path in sorted(DOCTYPE_ROOT.glob("*/*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("doctype") != "DocType":
                continue
            search_fields = str(data.get("search_fields") or "")
            if len(search_fields) > FRAPPE_SEARCH_FIELDS_MAX_LENGTH:
                violations.append(
                    f"{data.get('name') or path.stem}: {len(search_fields)} chars -> {search_fields}"
                )
        self.assertFalse(
            violations,
            "DocType search_fields exceeds Frappe's 140-character metadata limit:\n"
            + "\n".join(violations),
        )

    def test_scheme_delivery_search_uses_readable_business_fields(self):
        path = (
            DOCTYPE_ROOT
            / "eduedge_scheme_delivery_log"
            / "eduedge_scheme_delivery_log.json"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        search_fields = data.get("search_fields") or ""
        self.assertLessEqual(len(search_fields), FRAPPE_SEARCH_FIELDS_MAX_LENGTH)
        for fieldname in (
            "scheme_title_snapshot",
            "course_name_snapshot",
            "offering_title_snapshot",
            "topic_name_snapshot",
            "instructor",
            "school_branch",
        ):
            self.assertIn(fieldname, search_fields.split(","))
        self.assertNotIn("scheme_item_reference", search_fields)


if __name__ == "__main__":
    unittest.main()
