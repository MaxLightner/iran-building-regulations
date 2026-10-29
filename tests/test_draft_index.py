"""Phase 3-1 provenance and search index structural checks."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_draft_index as b


class DraftIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs=b.build()
        cls.manifest=json.loads((ROOT/"frontend/data/draft/manifest.json").read_text(encoding="utf-8"))

    def test_m04_is_indexed_without_843_clutter_records(self):
        docs={d["id"]:d for d in self.docs}
        self.assertIn("m04",docs)
        self.assertIn("m04-security-1403",docs)
        self.assertEqual(docs["m04"]["pages"],128)
        self.assertEqual(docs["m04-security-1403"]["pages"],49)
        draft=json.loads((ROOT/"frontend/data/draft/m04.json").read_text(encoding="utf-8"))
        self.assertEqual(len(draft["pages"]),128)
        self.assertTrue(all(x["id"].startswith("m04-p") for x in draft["pages"]))
        self.assertTrue(all(x["pdf_page"]>=1 for x in draft["pages"]))
        self.assertEqual(draft["status"],"unverified_pdf_transcription")

    def test_every_present_batch_chapter_has_exact_page_coverage(self):
        for chapter in (3,5,15):
            folder=ROOT/f"data/extracted/m{chapter:02d}/pages"
            if not folder.is_dir():
                continue
            docs={d["id"]:d for d in self.docs}
            docid=f"m{chapter:02d}"
            self.assertIn(docid,docs)
            indexed=json.loads((ROOT/f"frontend/data/draft/{docid}.json").read_text(encoding="utf-8"))
            self.assertEqual(len(indexed["pages"]),len(list(folder.glob("*.json"))))
            self.assertEqual([p["pdf_page"] for p in indexed["pages"]],
                             list(range(1,len(indexed["pages"])+1)))

    def test_normalize_persian(self):
        self.assertEqual(b.norm("كلمه  ي"),"کلمه ی")
        self.assertEqual(b.norm("راه‌پله"),"راه پله")

    def test_index_contains_only_source_pages(self):
        self.assertEqual(self.manifest["indexed_pages"],sum(d["pages"] for d in self.docs))
        for doc in self.docs:
            self.assertTrue(doc["pdf_url"].startswith(
                "https://raw.githubusercontent.com/MaxLightner/iran-building-regulations/main/sources/pdfs/"))
            self.assertEqual(doc["status"],"unverified_pdf_transcription")


if __name__=="__main__":
    unittest.main()
