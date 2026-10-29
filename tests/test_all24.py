"""Final phase-3 corpus acceptance: all 24 chapters must exist in page and knowledge indexes."""
import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class All24Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft=read(ROOT/"frontend/data/draft/manifest.json")
        cls.knowledge=read(ROOT/"frontend/data/knowledge/manifest.json")
        cls.draft_docs={d["id"]:d for d in cls.draft["documents"]}
        cls.knowledge_docs={d["id"]:d for d in cls.knowledge["documents"]}

    def test_all_24_regulation_chapters_present(self):
        expected={f"m{i:02d}" for i in range(1,25)}
        self.assertTrue(expected.issubset(self.draft_docs))
        self.assertTrue(expected.issubset(self.knowledge_docs))
        self.assertEqual(len(expected),24)

    def test_each_chapter_has_full_page_extraction_and_knowledge(self):
        for chapter in range(1,25):
            docid=f"m{chapter:02d}"
            with self.subTest(chapter=chapter):
                quality=read(ROOT/f"data/analysis/{docid}-quality.json")
                self.assertEqual(quality["extracted_pages"],quality["total_pages"])
                self.assertEqual(self.draft_docs[docid]["pages"],quality["total_pages"])
                self.assertGreater(self.draft_docs[docid]["nonempty_pages"],0)
                self.assertGreater(self.knowledge_docs[docid]["records"],0)

    def test_no_page_gaps_in_any_chapter_shard(self):
        for chapter in range(1,25):
            docid=f"m{chapter:02d}"
            shard=read(ROOT/f"frontend/data/draft/{docid}.json")
            pages=[p["pdf_page"] for p in shard["pages"]]
            self.assertEqual(pages,list(range(1,len(pages)+1)),docid)

    def test_knowledge_is_primary_search_corpus(self):
        self.assertEqual(self.knowledge["documents_indexed"],len(self.knowledge["documents"]))
        self.assertGreater(self.knowledge["records"],self.draft["documents_indexed"])
        self.assertGreater(self.knowledge["facts"],0)
        self.assertGreater(self.knowledge["conditions"],0)

if __name__=="__main__":
    unittest.main()
