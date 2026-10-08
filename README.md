# 📚 ДЗ Landau → Telegram

Бот с понедельника по пятницу сам заходит в родительский портал школы Landau (iSAMS), забирает домашние задания ваших детей **на два ближайших учебных дня** (в пятницу — сразу на понедельник и вторник) вместе с прикреплёнными материалами и присылает их в Telegram — вам, няне, бабушке, кому захотите. По пятницам присылает **сводку отзывов учителей за неделю**.

- Работает бесплатно, на серверах GitHub — ваш компьютер включать не нужно.
- Ваш логин и пароль хранятся в зашифрованных «секретах» **вашей** копии. Никто, включая автора шаблона, их не видит.
- Каждая семья делает **свою** копию — данные детей не смешиваются.

**[Azərbaycan dilində təlimat aşağıdadır ⬇](#-azərbaycan-dilində)**

---

## 🇷🇺 Инструкция (≈15 минут)

### Шаг 1. Создайте Telegram-бота
1. В Telegram найдите **@BotFather** → **Start** → отправьте `/newbot`.
2. Придумайте имя (например, «ДЗ Айдан») и username, который заканчивается на `bot`.
3. BotFather пришлёт **токен** вида `123456789:AA...` — сохраните его. Никому его не пересылайте.
4. Откройте своего бота и нажмите **Start**. Попросите сделать то же самое всех, кто будет получать ДЗ (няня, супруг и т.д.), и написать боту любое сообщение.

### Шаг 2. Создайте аккаунт GitHub
Зарегистрируйтесь на [github.com](https://github.com) (бесплатно).

### Шаг 3. Сделайте свою копию бота
1. Вверху этой страницы нажмите зелёную кнопку **Use this template → Create a new repository**.
2. Название — любое, например `dz-bot`.
3. Обязательно выберите **Private** (закрытый) → **Create repository**.

### Шаг 4. Впишите секреты
В **своей** копии: **Settings → Secrets and variables → Actions → New repository secret**. Добавьте по одному:

| Name | Что вписать |
|---|---|
| `ISAMS_EMAIL` | email от родительского портала Landau |
| `ISAMS_PASSWORD` | пароль от портала |
| `TELEGRAM_BOT_TOKEN` | токен от @BotFather |
| `TELEGRAM_CHAT_ID` | ваш номер (ID) в Telegram — как узнать, см. шаг 5 |

### Шаг 5. Узнайте номера (ID) получателей
1. Свой номер в первый раз проще всего узнать так: напишите в Telegram боту **@userinfobot** — он ответит вашим **Id**. Впишите его в секрет `TELEGRAM_CHAT_ID`.
2. В своей копии откройте вкладку **Actions**. Если GitHub спросит — нажмите **I understand my workflows, go ahead and enable them**.
3. Слева выберите **ДЗ в Telegram** → **Run workflow** → «Что отправить»: **CHAT_IDS** → **Run workflow**.
4. Бот пришлёт вам список всех, кто ему писал, с номерами. Впишите нужные номера в секрет `TELEGRAM_CHAT_ID` **через запятую**, например: `123456789,987654321`.

### Шаг 6. Проверка
**Actions → ДЗ в Telegram → Run workflow** → «Что отправить»: **HOMEWORK** → **Run workflow**. Через 1–2 минуты в Telegram придут ДЗ.
Зелёная галочка ✅ — всё работает. Красный крестик ❌ — откройте запуск: внизу будет файл `login-error` со скриншотом (чаще всего — опечатка в email/пароле).

### Готово 🎉
- **ДЗ** приходит с понедельника по пятницу ~**15:40** по Баку. Если GitHub опоздал, есть запасные попытки в 16:10 и 16:40; дважды за день ДЗ не придёт.
- В сообщениях вместо имени ребёнка указан класс, например «Класс 5R3».
- **Отзывы учителей** — по пятницам ~**18:00**, только на первый номер из `TELEGRAM_CHAT_ID` (отзывы личные). Чтобы слать их кому-то ещё, добавьте секрет `TELEGRAM_CHAT_ID_FEEDBACK` с номерами через запятую.

### Как изменить время
Откройте файл `.github/workflows/homework.yml` → карандаш ✏️ → в строках `cron: "40 11 * * 1-5"` (и двух запасных под ней) первое число — минуты, второе — часы **по UTC** (Баку минус 4 часа). Например, для ~15:00 по Баку: `"0 11 * * 1-5"`. Сохраните (**Commit changes**).

### Частые вопросы
- **Сменили пароль от портала?** Обновите секрет `ISAMS_PASSWORD` (карандаш ✏️ рядом с ним).
- **Большой файл?** PDF больше 50 МБ бот сжимает, а если не помогло — присылает частями. Один и тот же файл, прикреплённый к нескольким заданиям, приходит один раз.
- **Номера получателей** пишите через запятую без пробелов. Значение секрета заменяется целиком, поэтому при добавлении человека вписывайте весь список.
- **Хочу сразу проверить отзывы:** Run workflow → **FEEDBACK**.

---

## 🇦🇿 Azərbaycan dilində

Bot bazar ertəsindən cüməyə qədər Landau məktəbinin valideyn portalına (iSAMS) özü daxil olur, uşaqlarınızın **ən yaxın iki dərs günü** üçün (cümə günü — bazar ertəsi və çərşənbə axşamı üçün) ev tapşırıqlarını əlavə materiallarla birlikdə götürür və Telegram-a göndərir — sizə, dayəyə, nənəyə, kimə istəsəniz. Cümə günləri **müəllimlərin həftəlik rəylərinin xülasəsini** göndərir.

- Pulsuzdur, GitHub serverlərində işləyir — kompüterinizin açıq olması lazım deyil.
- Login və şifrəniz **sizin** nüsxənizdə şifrələnmiş «secrets» bölməsində saxlanılır. Heç kim, şablonun müəllifi də daxil olmaqla, onları görmür.
- Hər ailə **öz** nüsxəsini yaradır — uşaqların məlumatları qarışmır.

### Addım 1. Telegram botu yaradın
1. Telegram-da **@BotFather** tapın → **Start** → `/newbot` göndərin.
2. Ad (məsələn, «Aydan ev tapşırığı») və `bot` ilə bitən username seçin.
3. BotFather `123456789:AA...` kimi **token** göndərəcək — onu saxlayın, heç kimə göndərməyin.
4. Botunuzu açıb **Start** basın. Tapşırıqları alacaq hər kəsdən (dayə, həyat yoldaşı və s.) eyni şeyi etməyi və bota istənilən mesaj yazmağı xahiş edin.

### Addım 2. GitHub hesabı yaradın
[github.com](https://github.com) saytında qeydiyyatdan keçin (pulsuz).

### Addım 3. Botun öz nüsxənizi yaradın
1. Bu səhifənin yuxarısında yaşıl **Use this template → Create a new repository** düyməsini basın.
2. Ad — istənilən, məsələn `dz-bot`.
3. Mütləq **Private** (bağlı) seçin → **Create repository**.

### Addım 4. Sirləri (secrets) daxil edin
**Öz** nüsxənizdə: **Settings → Secrets and variables → Actions → New repository secret**. Bir-bir əlavə edin:

| Name | Nə yazmalı |
|---|---|
| `ISAMS_EMAIL` | Landau valideyn portalının email-i |
| `ISAMS_PASSWORD` | portalın şifrəsi |
| `TELEGRAM_BOT_TOKEN` | @BotFather-dən gələn token |
| `TELEGRAM_CHAT_ID` | Telegram-dakı nömrəniz (ID) — necə öyrənmək, addım 5-ə baxın |

### Addım 5. Alıcıların nömrələrini (ID) öyrənin
1. İlk dəfə öz nömrənizi öyrənməyin ən asan yolu: Telegram-da **@userinfobot**-a yazın, o sizə **Id** göndərəcək. Onu `TELEGRAM_CHAT_ID`-yə yazın.
2. Nüsxənizdə **Actions** bölməsini açın. GitHub soruşsa — **I understand my workflows, go ahead and enable them** basın.
3. Solda **ДЗ в Telegram** → **Run workflow** → «Что отправить»: **CHAT_IDS** → **Run workflow**.
4. Bot sizə ona yazan hər kəsin siyahısını nömrələri ilə göndərəcək. Lazımi nömrələri `TELEGRAM_CHAT_ID`-yə **vergüllə** yazın, məsələn: `123456789,987654321`.

### Addım 6. Yoxlama
**Actions → ДЗ в Telegram → Run workflow** → «Что отправить»: **HOMEWORK** → **Run workflow**. 1–2 dəqiqəyə tapşırıqlar Telegram-a gələcək.
Yaşıl ✅ — hər şey işləyir. Qırmızı ❌ — işə salınmanı açın: aşağıda ekran görüntüsü ilə `login-error` faylı olacaq (çox vaxt email/şifrədə səhv olur).

### Hazırdır 🎉
- **Ev tapşırıqları** bazar ertəsindən cüməyə qədər Bakı vaxtı ilə ~**15:40**-da gəlir (ehtiyat cəhdlər 16:10 və 16:40-da; gündə iki dəfə gəlmir).
- Mesajlarda uşağın adı əvəzinə sinif göstərilir, məsələn «Класс 5R3».
- **Müəllim rəyləri** — cümə günləri ~**18:00**-da, yalnız `TELEGRAM_CHAT_ID`-dəki ilk nömrəyə (rəylər şəxsidir). Başqalarına da göndərmək üçün nömrələrlə `TELEGRAM_CHAT_ID_FEEDBACK` sirri əlavə edin.

### Vaxtı necə dəyişmək olar
`.github/workflows/homework.yml` faylını açın → qələm ✏️ → `cron: "40 11 * * 1-5"` sətrində (və altındakı iki ehtiyat sətirdə) birinci rəqəm — dəqiqə, ikinci — saat **UTC** ilə (Bakı vaxtı mınus 4 saat). Məsələn, Bakı vaxtı ilə ~15:00 üçün: `"0 11 * * 1-5"`. Yadda saxlayın (**Commit changes**).

### Tez-tez verilən suallar
- **Portalın şifrəsini dəyişmisiniz?** `ISAMS_PASSWORD` sirrini yeniləyin.
- **Böyük fayl?** 50 MB-dan böyük PDF-i bot sıxır, alınmasa hissə-hissə göndərir.
- **Alıcı nömrələrini** vergüllə, boşluqsuz yazın. Sirr tam əvəz olunur, ona görə yeni adam əlavə edəndə bütün siyahını yazın.
- **Rəyləri dərhal yoxlamaq istəyirəm:** Run workflow → **FEEDBACK**.
