"""Acceptance tests for conservative project relevance signal index."""
import json,sys,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_applicability as a

def read(path): return json.loads(path.read_text(encoding="utf-8"))

class ApplicabilityIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a.build()
        cls.manifest=read(ROOT/"frontend/data/applicability/manifest.json")
        cls.knowledge=read(ROOT/"frontend/data/knowledge/manifest.json")

    def test_covers_every_knowledge_document_and_record(self):
        self.assertEqual(
            {d["id"] for d in self.manifest["documents"]},
            {d["id"] for d in self.knowledge["documents"]}
        )
        self.assertEqual(self.manifest["counts"]["records"],self.knowledge["records"])
        for d in self.manifest["documents"]:
            shard=read(ROOT/f"frontend/data/applicability/{d['id']}.json")
            self.assertEqual(len(shard["records"]),d["records"])
            self.assertEqual(shard["status"],"project_relevance_signals_not_legal_applicability")

    def test_rules_are_conservative_and_well_formed(self):
        allowed_fields={"area","floors","basements"}
        allowed_ops={"gt","gte","lt","lte","eq"}
        for d in self.manifest["documents"]:
            shard=read(ROOT/f"frontend/data/applicability/{d['id']}.json")
            for r in shard["records"]:
                self.assertEqual(r["status"],"project_relevance_signals_not_legal_applicability")
                self.assertIn("mentions",r)
                for c in r["numeric_conditions"]:
                    self.assertIn(c["field"],allowed_fields)
                    self.assertIn(c["operator"],allowed_ops)
                    self.assertGreaterEqual(c["value"],0)
                    self.assertEqual(c["confidence"],"candidate")
                    self.assertTrue(c["evidence"])

    def test_known_stage_defaults_exist(self):
        m12=read(ROOT/"frontend/data/applicability/m12.json")
        m22=read(ROOT/"frontend/data/applicability/m22.json")
        self.assertTrue(any("اجرا" in r["mentions"]["stages"] for r in m12["records"]))
        self.assertTrue(any("بهره‌برداری" in r["mentions"]["stages"] for r in m22["records"]))

    def test_city_is_not_used_as_false_filter(self):
        self.assertEqual(self.manifest["city_policy"],"neutral_national_regulations")
        self.assertIn("city",self.manifest["project_fields"])

if __name__=="__main__":
    unittest.main()
