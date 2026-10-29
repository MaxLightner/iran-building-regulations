"""Acceptance tests for the structured knowledge layer."""
import json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_knowledge as k

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

class KnowledgeLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        k.build()
        cls.manifest=read(ROOT/"frontend/data/knowledge/manifest.json")
        cls.ontology=read(ROOT/"frontend/data/knowledge/ontology.json")

    def test_all_current_documents_are_in_knowledge(self):
        draft=read(ROOT/"frontend/data/draft/manifest.json")
        self.assertEqual(
            {d["id"] for d in draft["documents"]},
            {d["id"] for d in self.manifest["documents"]}
        )
        self.assertEqual(self.manifest["documents_indexed"],len(draft["documents"]))
        self.assertGreater(self.manifest["records"],1000)
        self.assertGreater(self.manifest["facts"],100)
        self.assertGreater(self.manifest["conditions"],100)

    def test_every_record_has_source_topic_and_searchable_text(self):
        topics=set(self.ontology["topics"])
        count=0
        for doc in self.manifest["documents"]:
            shard=read(ROOT/f"frontend/data/knowledge/{doc['id']}.json")
            self.assertEqual(shard["status"],"unverified_structured_knowledge")
            self.assertEqual(len(shard["records"]),doc["records"])
            for r in shard["records"]:
                count+=1
                self.assertTrue(r["text"].strip())
                self.assertTrue(r["title"].strip())
                self.assertTrue(r["search_text"].strip())
                self.assertGreaterEqual(r["source"]["pdf_page"],1)
                self.assertTrue(r["source"]["pdf_url"].endswith(".pdf"))
                self.assertTrue(r["topics"])
                self.assertTrue(set(r["topics"]).issubset(topics))
                self.assertTrue(set(r["related_topics"]).issubset(topics))
                self.assertEqual(r["status"],"unverified_structured_from_pdf")
        self.assertEqual(count,self.manifest["records"])

    def test_ontology_relationships_are_valid(self):
        topics=self.ontology["topics"]
        for tid,t in topics.items():
            self.assertTrue(t["label"])
            self.assertTrue(t["aliases"])
            for target in t["related"]:
                self.assertIn(target,topics)
                self.assertNotEqual(target,tid)

    def test_known_concepts_exist_in_expected_chapters(self):
        expected={
            "m03":"fire",
            "m04":"stairs",
            "m06":"loads",
            "m07":"geotech",
            "m09":"concrete_steel",
            "m10":"concrete_steel",
            "m15":"elevator",
        }
        for docid,topic in expected.items():
            shard=read(ROOT/f"frontend/data/knowledge/{docid}.json")
            self.assertTrue(any(topic in r["topics"] for r in shard["records"]),
                            f"{topic} missing from {docid}")

if __name__=="__main__":
    unittest.main()
