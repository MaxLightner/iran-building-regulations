# موتور مقررات ملی ساختمان ایران

MVP مستقل برای جست‌وجو و اولویت‌بندی مقررات ملی ساختمان بر اساس مشخصات پروژه.

**نسخه آنلاین:** https://maxlightner.github.io/iran-building-regulations/

## وضعیت فعلی

- ۲۴ مبحث اصلی + پیوست حفاظتی انتظامی مبحث ۴
- ۴۹۰۴ صفحه PDF ایندکس‌شده
- ۱۵۰۱۷ رکورد دانش ساختاریافته
- ۲۶۶۲ فاکتور عددی استخراج‌شده
- ۱۵۶۲۵ شرط/قید متنی
- موتور پروژه بر اساس کاربری، سازه، زیربنا، طبقات، زیرزمین و مرحله پروژه
- جست‌وجوی فارسی روی Knowledge Index، نه صرفاً PDF
- PDF و شماره صفحه به‌عنوان provenance هر نتیجه حفظ می‌شوند
- بدون مدل زبانی در زمان اجرا و بدون ثبت‌نام
- Benchmark نهایی: **۲۰/۲۰ موضوع** و **۱۴/۱۴ مبحث هدف** در محدوده نتایج مورد انتظار

## جریان محصول

```
مشخصات پروژه
    ↓
موضوعات اولویت‌دار
    ↓
جست‌وجوی دانش ساختاریافته
    ↓
بند / خلاصه / اعداد / شروط / دلیل ارتباط با پروژه
    ↓
مبحث + صفحه PDF + منبع
```

مشخصات پروژه برای **رتبه‌بندی و توضیح ارتباط** استفاده می‌شوند. تشخیص نامطمئن باعث حذف قطعی یک بند نمی‌شود.

## داده و اعتبار

PDFهای فعلی آرشیو مرجع پروژه‌اند و متن آن‌ها به‌صورت خودکار استخراج و ساختاربندی شده است. این MVP هنوز ادعا نمی‌کند که هر PDF آخرین ویرایش لازم‌الاجرا یا از نظر حقوقی/علمی تأیید نهایی شده است.

OCR و استخراج ساختار نیز می‌توانند خطا داشته باشند؛ به همین دلیل مبحث و صفحه منبع برای کنترل نهایی کنار نتیجه باقی می‌ماند.

## معماری داده

```
PDF
 → page extraction
 → clause-like records
 → topics / ontology
 → numeric facts
 → conditions
 → cross-topic relations
 → project relevance signals
 → search ranking
 → static web app
```

فایل‌های اصلی:

- `frontend/data/knowledge/` — دانش ساختاریافته
- `frontend/data/applicability/` — سیگنال‌های ارتباط با پروژه
- `frontend/data/draft/` — متن صفحه‌ای خام برای debug/provenance
- `scripts/build_knowledge.py`
- `scripts/build_applicability.py`
- `benchmarks/search-cases.json`
- `tests/search-benchmark.test.cjs`

## به‌روزرسانی یک مبحث

Workflow دستی **Rebuild one regulation chapter** یک مبحث ۱ تا ۲۴ را دوباره استخراج می‌کند، سپس کل Knowledge Index و project relevance index را بازسازی و benchmark را اجرا می‌کند.

راهنما: `docs/updating-regulations.md`

## کنترل کیفیت و انتشار

انتشار GitHub Pages فقط بعد از موفقیت این مراحل انجام می‌شود:

1. ساخت مجدد همه ایندکس‌ها
2. تست پوشش ۲۴ مبحث
3. تست provenance و ساختار دانش
4. تست موتور پروژه
5. تست JavaScript
6. benchmark چندموضوعی جست‌وجو
7. deploy به GitHub Pages

اجرای انتشار موفق MVP:

https://github.com/MaxLightner/iran-building-regulations/actions/runs/40914547950

## مستندات مراحل

- `docs/phase3-complete.md` — تکمیل دانش ۲۴ مبحث
- `docs/phase4-complete.md` — موتور پروژه
- `docs/knowledge-layer.md` — ساختار Knowledge Index
- `docs/updating-regulations.md` — pipeline به‌روزرسانی

## خارج از MVP فعلی

API برای کمچه، حساب کاربری، ذخیره پروژه، LLM/Voice، نسخه Pro و اعتبارسنجی رسمی آخرین ویرایش مقررات در این نسخه پیاده‌سازی نشده‌اند.
