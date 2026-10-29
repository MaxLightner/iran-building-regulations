import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"frontend/m04-preview/data/rules.json"

class M04PreviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(P.read_text(encoding="utf-8"))

    def test_rule_db_is_substantive(self):
        self.assertEqual(self.data["status"],"preview_rules_not_legally_validated")
        self.assertGreaterEqual(self.data["rule_count"],80)
        self.assertEqual(self.data["rule_count"],len(self.data["rules"]))

    def test_rules_have_real_clause_provenance(self):
        for r in self.data["rules"]:
            self.assertTrue(r["locator"])
            self.assertGreaterEqual(r["page"],1)
            self.assertLessEqual(r["page"],128)
            self.assertGreater(len(r["statement"]),20)
            self.assertTrue(r["topics"])
            self.assertNotEqual(r["title"].strip(),"مبحث چهارم")

    def test_preview_is_rule_not_page_dump(self):
        raw=sum(len(r["source_text"]) for r in self.data["rules"])
        answers=sum(len(r["statement"]) for r in self.data["rules"])
        self.assertLess(answers,raw)
        self.assertTrue(any(r["facts"] for r in self.data["rules"]))
        self.assertTrue(any(r["conditions"] for r in self.data["rules"]))

if __name__=="__main__":unittest.main()
