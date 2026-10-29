"""Generate a non-authoritative QC queue for every OCR candidate in m04."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/analysis"
COND=re.compile(r"(?:در\s+صورتی\s+که|چنانچه|اگر|به\s+شرط|حداقل|حداکثر|بیش\s+از|کمتر\s+از|نباید|الزامی|باید)")
CROSS=re.compile(r"(?:مبحث|استاندارد)\s+[\w۰-۹\-‌]{2,40}")
TABLE=re.compile(r"(?:جدول|شکل|نمودار|تصویر|نقشه|دیاگرام)")
LATIN=re.compile(r"[A-Za-z]{2,}")
NUMERIC=re.compile(r"(?<!\\w)[\\d۰-۹٠-٩]+(?:[/.٫][\\d۰-۹٠-٩]+)?")

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def main():
    sources=[
       ("m04","data/records/m04.json","data/extracted/m04/pages","data/analysis/m04-quality.json"),
       ("m04-security-1403","data/records/m04-security-1403.json",
        "data/extracted/m04-security-1403/pages","data/analysis/m04-security-quality.json")]
    all_items=[];audit=[];total_pages=0;stats=Counter()
    for label,records_path,pages_path,quality_path in sources:
        records=load(records_path)["records"]
        pages=sorted((ROOT/pages_path).glob("*.json"))
        q=load(quality_path);total_pages+=len(pages)
        page_quality={}
        table_pages=[]
        for path in pages:
            p=json.loads(path.read_text(encoding="utf-8"))
            number=p["pdf_page"]
            original=p.get("ocr_text","")
            caption_matches=TABLE.findall(original)
            if caption_matches:
                table_pages.append({"pdf_page":number,"keyword_hits":len(caption_matches),
                                    "status":"needs_visual_table_figure_check"})
            page_quality[number]={"low_text":len(original.strip())<100,
                "image_review_required":True}
        for r in records:
            text=r["original_text"]
            loc=r["source"]["pdf_page"]
            condition_lines=[line[:220] for line in text.splitlines() if COND.search(line)]
            crossreferences=[x.group() for x in CROSS.finditer(text)]
            # Section locators contain digits by definition; exclude the OCR locator
            # before detecting numerical values in the provision body.
            body=text.replace(r.get("locator",""),"",1)
            numeric=NUMERIC.findall(body)[:50]
            flags=[]
            if numeric: flags.append("numbers_need_page_comparison")
            if condition_lines: flags.append("conditional_rule_needs_parsing")
            if LATIN.findall(text): flags.append("possible_ocr_latin_noise")
            if page_quality.get(loc,{}).get("low_text"): flags.append("low_density_source_page")
            if any(TABLE.search(x) for x in text.splitlines()): flags.append("possible_table_or_figure_reference")
            if crossreferences: flags.append("cross_reference_needs_verification")
            if not r.get("summary"): flags.append("summary_not_written")
            if r["applicability"]["status"]!="reviewed": flags.append("applicability_not_verified")
            for f in flags:stats[f]+=1
            score=(4 if "low_density_source_page" in flags else 0)+\
                  (2 if numeric else 0)+(2 if "possible_ocr_latin_noise" in flags else 0)+\
                  (2 if "possible_table_or_figure_reference" in flags else 0)+\
                  (1 if condition_lines else 0)
            audit.append({"id":r["id"],"document_id":label,
                "locator_ocr":r["locator"],"pdf_page":loc,
                "title_ocr":r["title"][:90],"topic_heuristic":r["topic"],
                "risk_score":score,"flags":flags,
                "numeric_candidates_preview":numeric[:15],
                "conditional_lines_preview":condition_lines[:5],
                "cross_reference_candidates":crossreferences[:6],
                "status":"pending_manual_review"})
        all_items.append({"document_id":label,"pages":len(pages),"candidate_records":len(records),
          "pages_with_table_or_figure_keywords":table_pages,
          "empty_ocr_pages":[int(x.stem) for x in pages if not json.loads(x.read_text(encoding="utf-8")).get("ocr_text","").strip()],
          "source_sha256":q.get("pdf_sha256") or q.get("source_sha256")})
    audit.sort(key=lambda x:(-x["risk_score"],x["document_id"],x["pdf_page"]))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"m04-review-queue.json").write_text(json.dumps({
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "warning":"OCR and derived topic/condition/number hints are not verified or official.",
        "status":"review_pending",
        "items":audit
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"m04-audit-summary.json").write_text(json.dumps({
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "documents":all_items,
        "total_pdf_pages":total_pages,"total_candidate_records":len(audit),
        "flags_per_record":dict(stats),
        "records_with_condition_cues":stats["conditional_rule_needs_parsing"],
        "records_with_numeric_candidates":stats["numbers_need_page_comparison"],
        "records_needing_summary":stats["summary_not_written"],
        "verified_rules":0,
        "review_complete":False,
        "pending_work":["Correct OCR against PDF, including empty and table pages",
                        "Validate clause numbering, table cells, numeric values and references",
                        "Write reviewed summaries, tags and project applicability conditions",
                        "Verify edition, addendum scope and legal effective dates"]
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Review queue",len(audit),"pages",total_pages,flush=True)

if __name__=="__main__":main()
