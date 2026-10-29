# موتور مقررات ملی ساختمان ایران

پروژه مستقل `iran-building-regulations`، فاز صفر. کمچه در آینده فقط از API استفاده می‌کند. این نسخه هیچ بند مقرراتی، مقدار مهندسی یا تشخیص کاربردپذیری ساختگی ندارد.

## اجرای فوری بدون نصب وابستگی

در پوشه ریشه پروژه، با Python 3.11 یا جدیدتر:

```powershell
python -m backend.server
```

رابط فارسی: http://127.0.0.1:8765 — سلامت: `/health` — قرارداد API: `/openapi.json`.
در محیط فعلی به‌جای alias خراب WindowsApps از Python موجود استفاده کنید:

```powershell
& 'C:/Users/Mayram/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m backend.server
```

در ترمینال دوم:

```powershell
python scripts/smoke.py
python -m unittest discover -s tests -v
```

سرور صرفاً محلی و توسعه‌ای است. توقف: Ctrl+C. فایل .env خودکار خوانده نمی‌شود؛ متغیرهای `.env.example` را در محیط فرایند تنظیم کنید. پوشه frontend را جدا با file:// باز نکنید؛ به API همان سرور نیاز دارد.

## اتصال PostgreSQL

PostgreSQL 16+ و درایور psycopg لازم‌اند. هیچ نرم‌افزار یا وابستگی در این تحویل نصب نشده است. پس از تأیید نصب از سوی مالک محیط:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
$env:DATABASE_URL='postgresql://regulations:YOUR_PASSWORD@localhost:5432/regulations'
.venv/Scripts/python scripts/database.py migrate
.venv/Scripts/python scripts/database.py import-catalog
.venv/Scripts/python -m backend.server
```

پایگاه و کاربر PostgreSQL را از قبل در محیط توسعه بسازید؛ این دستورات سرویس پایگاه داده نصب نمی‌کنند. migrationها تراکنشی، قفل‌شده و دارای کنترل checksum هستند. import-catalog فقط metadata شناسایی و pending وارد می‌کند. اجرای دوباره آن رکورد موجود را بازنویسی نمی‌کند؛ تغییر نسخه و وضعیت با بازبینی در فاز بعد مدیریت می‌شود.

بدون DATABASE_URL فهرست manifest با برچسب catalog_only دیده می‌شود؛ topics و search خالی‌اند. با اتصال خراب پاسخ 503 برمی‌گردد. PostgreSQL در این محیط موجود نبود و migration روی سرور واقعی اجرا نشده است.

## بررسی منابع رسمی

```powershell
python scripts/check_sources.py
# Download only after setting a private directory OUTSIDE the repository:
$env:SOURCE_CACHE_DIR='C:/path/to/private/regulations-pdfs'
python scripts/check_sources.py --download --asset m2-pdf
# Optional: persist a selected JSONL run into source_checks after catalog import:
python scripts/database.py import-checks --checks-file sources/checks/RUN_ID.jsonl
```

فهرست URLهای رسمی در sources/manifest.json است. اجرای check_sources با خطای شبکه exit code=1 می‌دهد، خطا را ثبت می‌کند و هش موفق قبلی را پاک نمی‌کند. فایل جدید با نام هش نگهداری می‌شود؛ هیچ وضعیت اعتبار یا محتوای عملیاتی خودکار تغییر نمی‌کند. در کنار PDFها صفحات فهرست نیز بررسی می‌شوند؛ تغییر هش HTML فقط نیاز بررسی را نشان می‌دهد. تشخیص اضافه‌شدن لینک تازه و تحلیل معنایی هنوز TODO هستند.

## ساختار

```text
frontend/          رابط فارسی RTL بدون build
backend/           API نسخه‌دار + adapter PostgreSQL
db/migrations/     ساختار و تاریخچه داده
scripts/           اجرا، migration، import، بررسی منابع و smoke
sources/manifest.json  فهرست شناسایی و وضعیت دریافت؛ بدون متن مقررات
docs/              قرارداد API، تصمیم‌ها، مجوز و TODO استخراج
tests/             بررسی اعتبارسنجی، صداقت حالت خالی و هش
```

## وضعیت تحویل

اسکلت محلی قابل اجرا است. مخزن خصوصی GitHub در https://github.com/MaxLightner/iran-building-regulations ایجاد شده است. دمو عمومی deploy نشده است. مجوز کد هنوز تعیین نشده است. اکنون ۲۴ PDF مرجع اولیه و **تأییدنشده** (از پایگاه ثانویه qsce.ir) در مخزن خصوصی داخل `sources/pdfs/reference-m01.pdf` تا `reference-m24.pdf` قرار دارد. این نسخه‌ها برای استفاده به‌عنوان ضابطه جاری تا زمان تطبیق با سند رسمی، شناسنامه و اصلاحیه‌ها معتبرسازی نشده‌اند. گزارش دریافت در `sources/reference-mirror-report.json` است. لینک‌های PDF رسمی inbr.ir در اجرای خودکار همچنان HTTP 403 برگردانده‌اند. گزارش تفصیلی در docs/delivery-report.md، طرح توسعه در docs/extraction-workflow.md و سیاست مجوز در docs/licensing.md است.


## آرشیو PDF مرجع اولیه (۱۴۰۵/۰۸/۰۷)

۲۴ فایل PDF از آرشیو ثانویه qsce.ir فقط در همین مخزن **خصوصی** ذخیره شده‌اند. وجود فایل، هش SHA-256 و حجم آن در `sources/reference-mirror-report.json` ثبت شده است. فایل‌ها به‌عنوان نسخه رسمی جاری **تأیید نشده‌اند** و برای تصمیم‌گیری مهندسی یا نمایش به‌عنوان حکم معتبر در API مجاز نیستند. قبل از انتشار عمومی یا استفاده تجاری حقوق نشر و مجوز استفاده بررسی شود. فایل‌های اصلی از inbr.ir در اجرای اخیر قابل دریافت نبودند (HTTP 403).
