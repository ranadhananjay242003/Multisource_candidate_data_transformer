import json
import tempfile
import unittest
from pathlib import Path

from src.transformer import merge_records, normalize_phone, normalize_skill, run


ROOT = Path(__file__).resolve().parents[1]


class TransformerTests(unittest.TestCase):
    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("(415) 555-0198"), "+14155550198")
        self.assertEqual(normalize_phone("+91 98765 43210", "IN"), "+919876543210")
        self.assertIsNone(normalize_phone("no phone here"))

    def test_skill_aliases(self):
        self.assertEqual(normalize_skill("JS"), "javascript")
        self.assertEqual(normalize_skill("Node.js"), "javascript")
        self.assertEqual(normalize_skill("Postgres"), "postgresql")

    def test_default_run_merges_csv_and_notes(self):
        records = run([ROOT / "samples/recruiter_export.csv", ROOT / "samples/recruiter_notes.txt"])
        self.assertEqual(len(records), 2)
        anaya = next(r for r in records if r["full_name"] == "Anaya Rao")
        self.assertEqual(anaya["phones"][0], "+14155550198")
        self.assertEqual(anaya["location"]["country"], "US")
        self.assertIn("provenance", anaya)
        self.assertTrue(any(s["name"] == "machine learning" for s in anaya["skills"]))

    def test_custom_projection(self):
        records = run(
            [ROOT / "samples/recruiter_export.csv", ROOT / "samples/recruiter_notes.txt"],
            ROOT / "samples/custom_config.json",
        )
        self.assertIn("primary_email", records[0])
        self.assertIn("overall_confidence", records[0])
        self.assertNotIn("emails", records[0])

    def test_missing_required_can_error(self):
        config = {
            "fields": [{"path": "missing", "from": "does_not_exist", "type": "string", "required": True}],
            "on_missing": "error",
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(config, handle)
            config_path = Path(handle.name)
        try:
            with self.assertRaises(ValueError):
                run([ROOT / "samples/recruiter_export.csv"], config_path)
        finally:
            config_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
