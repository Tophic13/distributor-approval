# Distributor Approval (تسجيل الموزعين مع مراجعة يدوية)

تطبيق Frappe/ERPNext يضيف:

- حقول **NIF / RC / NIS** وصور الوثائق في سجل العميل (Customer)
- حالة الموزع: `Pending Review` ← `Approved` / `Rejected` (مع سبب الرفض)
- صفحة تسجيل جاهزة: `/distributor-register`
- API للتسجيل: `POST /api/method/distributor_approval.api.register_distributor`
- API للتحقق من إظهار الأسعار: `distributor_approval.api.can_view_prices`
- بريد تلقائي للموزع عند القبول أو الرفض، وبريد للمدير عند وصول طلب جديد
- منع أي مستخدم لا يملك دور مراجع من تغيير الحالة (System Manager / Sales Manager)

> لم يُختبر هذا الكود على نظام حي. اختبره أولاً على النسخة التجريبية.

## النشر

1. أنشئ مستودعاً على GitHub وارفع محتوى هذا المجلد (الملف `pyproject.toml` في الجذر).
2. في كونسول Managely: **Custom Apps** ← أضف رابط المستودع والفرع ← انشر.
3. بعد النشر، تُنشأ الحقول ومجموعة العملاء `Distributor` تلقائياً.
   إن لم تظهر، شغّل Migrate من **Server Commands** أو اطلب ذلك من الدعم.

## الاستخدام

- افتح `https://YOUR-SITE/distributor-register` وجرّب التسجيل.
- في النظام: **Customer** ← فلتر `Distributor Status = Pending Review` ← افتح السجل،
  راجع الوثائق، غيّر الحالة إلى `Approved` أو `Rejected` (مع السبب) ثم احفظ.
- العملاء الموجودون قبل التطبيق حالتهم فارغة، وهم **لا** يرون الأسعار افتراضياً.
  إما اجعلهم `Approved` من قائمة العملاء، أو غيّر `BLANK_STATUS_COUNTS_AS_APPROVED` في `utils.py`.

## إخفاء الأسعار في المتجر

التطبيق يوفر القرار (`can_view_prices`) لكن **لا يستطيع وحده إخفاء الأسعار** في واجهة
المتجر، لأن كود واجهة E Store غير معروف لي. الخيارات:

1. إعداد جاهز في E Store (إن وُجد) لإخفاء الأسعار عن غير المسجلين.
2. تعديل واجهة المتجر لاستدعاء `can_view_prices` قبل عرض السعر.
3. طلب ذلك من دعم Managely.

## تعديلات شائعة

| ما تريد | أين |
|---|---|
| جعل وثيقة NIS إلزامية | `REQUIRED_DOCUMENTS` في `api.py` |
| تغيير شروط طول NIF/NIS | `register_distributor` في `api.py` |
| عدم إرسال رابط كلمة المرور | `SEND_PASSWORD_SETUP_EMAIL = False` |
| إضافة أدوار مراجعة | `REVIEW_ROLES` في `utils.py` |

ملاحظة: إن كان نظامك Frappe v14 أو v16 فقد تحتاج تعديلاً بسيطاً في ملفات التغليف.
