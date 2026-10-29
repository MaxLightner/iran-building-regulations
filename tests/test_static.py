"""Gate checks for the static frontend and the structured data publication rules."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_static as builder


class StaticPhaseOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder.main()
        cls.public = ROOT / "frontend" / "data"

    def test_catalog_complete_but_unverified(self):
        data = json.loads((self.public / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["items"]), 24)
        self.assertEqual(data["status"], "unverified_catalog_only")

    def test_demo_is_not_mixed_with_approved(self):
        approved=json.loads((self.public/"records.json").read_text(encoding="utf-8"))
        demo=json.loads((self.public/"demo.json").read_text(encoding="utf-8"))
        self.assertEqual(approved["items"],[])
        self.assertEqual(len(demo["items"]),3)
        self.assertTrue(all(x["review"]["status"]=="demo" for x in demo["items"]))

    def test_fail_closed_publication(self):
        demo=json.loads((self.public/"demo.json").read_text(encoding="utf-8"))["items"][0]
        self.assertFalse(builder.publishable(demo))
        r=copy.deepcopy(demo)
        r["review"]={"status":"approved","reviewer":"reviewer","reviewed_at":"2026-10-29"}
        self.assertFalse(builder.publishable(r))
        r["source"].update({"authority":"official","publication_rights":"approved",
            "sha256":"a"*64,"pdf_page":1,"official_page_url":"https://inbr.ir/example"})
        r["version"].update({"status":"current","effective_evidence":"official-notice"})
        self.assertTrue(builder.publishable(r))
        r["source"]["publication_rights"]="unverified"
        self.assertFalse(builder.publishable(r))

    def test_text_normalization(self):
        self.assertEqual(builder.normalize("كاربري  ساختمان"),"کاربری ساختمان")
        self.assertEqual(builder.normalize("پله‌"),"پله")

    def test_static_assets_use_relative_urls(self):
        html=(ROOT/"frontend"/"index.html").read_text(encoding="utf-8")
        self.assertIn('src="./app.js"',html)
        self.assertIn('href="./styles.css"',html)
        self.assertNotIn('src="/app.js"',html)

    def test_no_pdf_or_source_manifest_in_published_site(self):
        self.assertFalse(list((ROOT/"frontend").rglob("*.pdf")))
        self.assertFalse((ROOT/"frontend"/"sources"/"manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
