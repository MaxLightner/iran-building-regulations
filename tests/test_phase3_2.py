"""Validate the 3-2 batch against its physical PDF files and search shards."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_draft_index as builder
CHAPTERS=(6,7,9,10)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Phase32Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder.build()
        cls.manifest=read(ROOT/"frontend/data/draft/manifest.json")
        cls.docs={d["id"]:d for d in cls.manifest["documents"]}

    def test_all_four_present_complete_and_hash_matched(self):
        for chapter in CHAPTERS:
            key=f"m{chapter:02d}"
            with self.subTest(chapter=chapter):
                info=read(ROOT/f"data/analysis/{key}-quality.json")
                pages=sorted((ROOT/f"data/extracted/{key}/pages").glob("*.json"))
                self.assertEqual(len(pages),info["total_pages"])
                self.assertEqual(info["extracted_pages"],info["total_pages"])
                self.assertEqual(info["status"],"full_page_extraction_complete_unverified")
                digest=hashlib.sha256((ROOT/f"sources/pdfs/reference-{key}.pdf").read_bytes()).hexdigest()
                self.assertEqual(info["source_sha256"],digest)
                shard=read(ROOT/f"frontend/data/draft/{key}.json")
                self.assertEqual(shard["pdf_sha256"],digest)
                self.assertEqual(shard["status"],"unverified_pdf_transcription")
                self.assertEqual(len(shard["pages"]),info["total_pages"])
                self.assertEqual([p["pdf_page"] for p in shard["pages"]],
                                 list(range(1,info["total_pages"]+1)))
                self.assertEqual(self.docs[key]["pages"],info["total_pages"])
                self.assertGreater(info["nonempty_pages"],0)

    def test_no_unknown_or_approved_claims(self):
        self.assertGreater(self.manifest["indexed_pages"],794)
        for chapter in CHAPTERS:
            shard=read(ROOT/f"frontend/data/draft/m{chapter:02d}.json")
            for page in shard["pages"]:
                self.assertIsInstance(page["text"],str)
                self.assertIsInstance(page["search_text"],str)
                self.assertTrue(page["id"].startswith(f"m{chapter:02d}-p"))
                self.assertLessEqual(len(page["topics"]),4)
                self.assertGreaterEqual(len(page["topics"]),1)


if __name__=="__main__":
    unittest.main()
