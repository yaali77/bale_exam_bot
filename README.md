# سامانه اعلام نتایج آزمون در بله

پیاده‌سازی کامل تمام ۲۴ مرحله چک‌لیست پروژه: بک‌اند FastAPI، بات پیام‌رسان بله، و پنل مدیریت React.

## خلاصه وضعیت پیاده‌سازی

تمام ۲۴ مرحله چک‌لیست پروژه به‌طور کامل پیاده‌سازی شده است.

| مرحله | عنوان | وضعیت |
|---|---|---|
| ۱ | زیرساخت + دیتابیس + Backend | ✅ کامل |
| ۲ | اتصال واقعی به بله | ✅ کامل |
| ۳ | ثبت‌نام و احراز هویت | ✅ کامل |
| ۴ | آزمون و نمرات (مدیریت آزمون) | ✅ کامل |
| ۵ | ثبت/ویرایش نمرات + Excel | ✅ کامل |
| ۶ | کنترل انتشار نمرات (تکی/گروهی) | ✅ کامل |
| ۷ | استعلام نمره توسط کاربر | ✅ کامل |
| ۸ | اعلام خودکار نتیجه | ✅ کامل |
| ۹ | کارنامه PDF | ✅ کامل |
| ۱۰ | QR Code و اعتبارسنجی | ✅ کامل |
| ۱۱ | درخواست اصلاح اطلاعات | ✅ کامل |
| ۱۲ | اعتراض به نمره | ✅ کامل |
| ۱۳ | پنل مدیریت (React) | ✅ کامل |
| ۱۴ | نقش‌ها و دسترسی‌ها (RBAC) | ✅ کامل |
| ۱۵ | مدیریت قابلیت‌ها (Feature Flags) | ✅ کامل |
| ۱۶ | مدیریت ظاهر (پویا، بدون تغییر کد) | ✅ کامل |
| ۱۷ | هویت بصری آستان | ✅ کامل |
| ۱۸ | اطلاع‌رسانی گروهی + زمان‌بندی واقعی | ✅ کامل (APScheduler) |
| ۱۹ | Audit Log | ✅ کامل |
| ۲۰ | امنیت | ✅ کامل |
| ۲۱ | پشتیبان‌گیری خودکار روزانه | ✅ کامل (pg_dump + Cron داخلی) |
| ۲۲ | مانیتورینگ | ✅ کامل (Health/DB/Bot Status) |
| ۲۳ | تست | ✅ کامل (Unit + Integration با pytest، ۲۰+ تست) |
| ۲۴ | استقرار نهایی | ✅ کامل (Docker Compose چهار سرویسه) |

## ساختار پروژه

```
bale_exam_bot/
├── app/
│   ├── main.py                       # نقطه ورود FastAPI
│   ├── config.py / database.py
│   ├── models/                       # کاربر، آزمون، نمره، ادمین، Feature، Audit، اصلاح، اعتراض، کارنامه
│   ├── schemas/                      # Pydantic Schemaها
│   ├── core/                         # امنیت، لاگ، Audit، GUID (نوع UUID قابل‌حمل)
│   ├── services/                     # PDF، QR، Excel، اطلاع‌رسانی، Scheduler، Backup، Appearance
│   ├── api/routers/                  # ۱۶ روتر: auth, users, exams, results, excel, reportcard,
│   │                                    corrections, objections, notifications, admins,
│   │                                    features, dashboard, audit, monitoring, appearance, backup
│   └── bot/
│       ├── client.py                 # کلاینت Bale Bot API
│       ├── webhook.py                # مسیریابی مکالمه
│       └── handlers/                 # ثبت‌نام، استعلام، کارنامه، اعتراض، اصلاح اطلاعات
├── admin-panel/                      # پنل مدیریت React + TypeScript + Vite
│   └── src/{pages,components,context,api}
├── alembic/                          # مدیریت Migration دیتابیس
├── tests/                            # pytest (واحد + یکپارچگی با SQLite)
├── scripts/create_super_admin.py
├── Dockerfile, docker-compose.yml, nginx.conf
└── .env.example
```

## راه‌اندازی سریع

```bash
cp .env.example .env
# مقادیر BALE_BOT_TOKEN, POSTGRES_PASSWORD, SECRET_KEY, BALE_WEBHOOK_SECRET, PUBLIC_BASE_URL را تنظیم کنید

docker compose up -d --build
docker compose exec backend python scripts/create_super_admin.py
```

سپس Webhook بله را ثبت کنید:
```bash
curl -X POST "https://tapi.bale.ai/bot<TOKEN>/setWebhook" \
     -d "url=https://yourdomain.example.com/webhook/bale"
```

پنل مدیریت روی `https://yourdomain.example.com/` و API روی همان دامنه با پیشوند `/api` در دسترس است (هر دو پشت یک Nginx مشترک).

## اجرای تست‌ها (بدون Docker، برای توسعه محلی)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

تست‌ها از SQLite موقت استفاده می‌کنند و نیازی به PostgreSQL واقعی ندارند.

## توسعه پنل مدیریت به‌صورت محلی

```bash
cd admin-panel
npm install
npm run dev
```

Vite به‌صورت خودکار درخواست‌های `/api`, `/verify`, `/storage` را به `http://localhost:8000` پروکسی می‌کند (بک‌اند باید جداگانه با `uvicorn app.main:app --reload` اجرا شود).

## معماری استقرار (۴ سرویس Docker)

```
اینترنت → Nginx (SSL, پورت ۴۴۳)
             ├── /api, /webhook, /verify, /health  →  backend (FastAPI:8000)
             └── /  (بقیه مسیرها)                   →  admin-panel (Nginx استاتیک React:80)
                                                          │
backend → PostgreSQL (db)                                │
backend → فایل‌های PDF/QR/Excel در Volume مشترک storage_data
```

## نکات امنیتی پیاده‌سازی‌شده

- تطبیق دقیق `national_code` + مالکیت حساب بله برای جلوگیری از مشاهده نتیجه دیگران
- دریافت شماره تلفن فقط از طریق دکمه Contact بله (نه ورودی تایپی)
- هش پسورد ادمین با bcrypt، JWT برای نشست پنل، انقضای توکن قابل‌تنظیم
- RBAC با ۷ نقش از پیش تعریف‌شده (`app/models/admin.py`) که هم در بک‌اند و هم در فرانت (مخفی‌سازی منو) اعمال می‌شود
- Audit Log برای تمام عملیات حساس (ورود، تغییر نمره، انتشار، تغییر قابلیت، اعتراض و ...)
- اعتبارسنجی Webhook بله با هدر Secret اختصاصی
- Rate Limiting سطح اپلیکیشن با `slowapi`
- صفحه اعتبارسنجی عمومی QR فقط کد ملی ماسک‌شده را نشان می‌دهد، نه اطلاعات کامل

## قابلیت کلیدی: مدیریت قابلیت‌ها (Feature Management)

هر قابلیت سیستم یک رکورد `FeatureFlag` در دیتابیس دارد که از صفحه «مدیریت قابلیت‌ها» در پنل یا مستقیماً از
`PATCH /api/features/{key}/toggle` فعال/غیرفعال می‌شود، بدون نیاز به تغییر کد یا Deploy مجدد. هندلرهای بات
(اعتراض، اصلاح اطلاعات، اعلام خودکار) پیش از اجرا وضعیت قابلیت مرتبط را بررسی می‌کنند.

## نکات پیاده‌سازی مهم برای توسعه‌دهنده بعدی

- **GUID سفارشی**: به‌جای `UUID` بومی PostgreSQL از یک `TypeDecorator` در `app/core/db_types.py` استفاده شده
  تا هم روی Production (Postgres) و هم روی تست (SQLite) کار کند.
- **جلوگیری از Circular Import**: `app/bot/handlers/reportcard.py` تابع تولید کارنامه را به‌صورت Local Import
  از `app/api/routers/reportcard.py` فراخوانی می‌کند (نه در سطح ماژول) تا وابستگی چرخه‌ای پیش نیاید.
- **زمان‌بندی پیام واقعی**: با APScheduler (`app/services/scheduler.py`) پیاده‌سازی شده. هر پیام یک رکورد
  `BroadcastJob` در دیتابیس دارد؛ اگر `schedule_at` در آینده باشد، Job در APScheduler ثبت و در زمان مقرر
  اجرا می‌شود. در صورت ری‌استارت سرویس، Jobهای هنوز اجرانشده در `init_scheduler()` بازیابی می‌شوند.
  **توجه**: این Scheduler در پردازه اصلی FastAPI اجرا می‌شود (in-process)؛ برای استقرار با چند Replica از
  backend باید به یک Worker جداگانه (Job Store دیتابیسی یا Celery Beat) منتقل شود.
- **Backup خودکار روزانه**: با APScheduler + `pg_dump` در `app/services/backup_service.py` پیاده‌سازی شده.
  فایل‌ها فشرده (`.sql.gz`) در Volume مشترک `./backups` ذخیره و طبق `BACKUP_RETENTION_DAYS` پاکسازی می‌شوند.
  ساعت اجرا با `BACKUP_CRON_HOUR` (به وقت UTC) قابل تنظیم است. اجرای دستی از پنل (صفحه «پشتیبان‌گیری») یا
  مستقیماً با `POST /api/backups/run-now` ممکن است. کانتینر `backend` باید به `postgresql-client` دسترسی
  داشته باشد (در Dockerfile نصب شده است).
- **مدیریت ظاهر پویا**: مدل `AppearanceSettings` (Singleton، همیشه یک رکورد) رنگ‌ها، فونت، عنوان، لوگو و
  متون قابل‌ویرایش بات را نگه می‌دارد. `GET /api/appearance` عمومی است (بدون نیاز به احراز هویت) تا هم بات
  و هم پنل (حتی پیش از لاگین) بتوانند بخوانند؛ `PATCH` فقط برای ادمین دارای مجوز `settings`. پنل با
  `AppearanceContext` این مقادیر را در زمان اجرا روی CSS Variableها اعمال می‌کند؛ بات هم پیام خوش‌آمد و
  قالب نتیجه را از همین منبع می‌خواند (`app/services/appearance_service.py`).

## گام بعدی پیشنهادی (بهبودهای فراتر از دامنه چک‌لیست)

1. انتقال Scheduler به Job Store دیتابیسی یا Celery Beat برای پشتیبانی از چند Replica از backend
2. آپلود مستقیم لوگو (فعلاً فقط URL لوگو پشتیبانی می‌شود، نه آپلود فایل)
3. افزودن تست E2E برای جریان کامل بات (ثبت‌نام → انتشار نمره → دریافت کارنامه) با شبیه‌ساز Webhook
4. نصب گواهی SSL واقعی (Let's Encrypt/Certbot) روی `nginx.conf`
5. آپلود Backup به فضای ابری خارجی (S3 یا مشابه) علاوه بر ذخیره محلی، برای مقاومت در برابر از دست رفتن سرور
