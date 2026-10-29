"""Post-OCR coverage, provenance, and safety checks for the m04 extraction."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class TestM04(unittest.TestCase):
    def test_full_pdf_coverage_and_sha(self):
        q=load("data/analysis/m04-quality.json")
        self.assertEqual(q["pdf_pages"],128)
        self.assertEqual(q["ocr_pages"],128)
        self.assertEqual(len(list((ROOT/"data/extracted/m04/pages").glob("*.json"))),128)
        self.assertEqual(q["pdf_sha256"],
            hashlib.sha256((ROOT/"sources/pdfs/reference-m04.pdf").read_bytes()).hexdigest())
        for i in range(1,129):
            p=load("data/extracted/m04/pages/%04d.json"%i)
            self.assertEqual(p["pdf_page"],i)
            self.assertEqual(p["source_sha256"],q["pdf_sha256"])
            self.assertEqual(p["review_status"],"pending_manual_visual_comparison")

    def test_no_claimed_legal_approval(self):
        d=load("data/records/m04.json")
        self.assertEqual(d["workflow_status"],"OCR_COMPLETE_PENDING_VISUAL_LEGAL_REVIEW")
        self.assertGreater(len(d["records"]),20)
        ids=set()
        for r in d["records"]:
            self.assertNotIn(r["id"],ids)
            ids.add(r["id"])
            self.assertEqual(r["review"]["status"],"pending")
            self.assertEqual(r["version"]["status"],"unconfirmed")
            self.assertEqual(r["source"]["authority"],"secondary")
            self.assertEqual(r["source"]["publication_rights"],"unverified")
            self.assertEqual(r["applicability"]["status"],"not_evaluated")
            self.assertEqual(r["key_factors"],[])
            self.assertTrue(r["original_text"].strip())
            self.assertTrue(1<=r["source"]["pdf_page"]<=128)

    def test_unsafe_records_not_in_static_search(self):
        from sys import path as sys_path
        sys_path.insert(0,str(ROOT/"scripts"))
        from build_static import publishable
        for r in load("data/records/m04.json")["records"]:
            self.assertFalse(publishable(r))

if __name__=="__main__":
    unittest.main()
