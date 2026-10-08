"""
Бот домашних заданий школы Landau (iSAMS Parent Portal) -> Telegram.

С понедельника по пятницу бот входит в родительский портал, забирает ДЗ всех ваших
детей на два ближайших учебных дня (в пятницу — на понедельник и вторник) вместе
с прикреплёнными материалами и отправляет в Telegram. В сообщениях вместо имени
ребёнка указан класс. По пятницам присылает сводку отзывов учителей за неделю.

Настройки — в секретах GitHub (Settings -> Secrets and variables -> Actions):
  ISAMS_EMAIL                 - email для входа в портал
  ISAMS_PASSWORD              - пароль от портала
  TELEGRAM_BOT_TOKEN          - токен бота от @BotFather
  TELEGRAM_CHAT_ID            - кому слать ДЗ (номера через запятую, без пробелов)
  TELEGRAM_CHAT_ID_FEEDBACK   - (необязательно) кому слать отзывы; по умолчанию первый номер из TELEGRAM_CHAT_ID
"""

import html
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from playwright.sync_api import sync_playwright

PORTAL_URL = "https://landau.parents.isamshosting.cloud/#/school-profile/homework"
API = "https://landau.isamshosting.cloud/api"
OIDC_KEY = "oidc.user:https://landau.isamshosting.cloud/auth:iSAMS.Portal.Cloud.Parents"
STUDENTS_URL = (
    API + "/portals/students/portal/parents/"
    "13,9,10,11,20,21,14,15,16,17,22,23,24,25,26,6,12,7,8,18,27,28,29,30,31,19"
)

TZ = ZoneInfo("Asia/Baku")
SCHOOL_DAYS_AHEAD = 2  # два ближайших учебных дня (суббота и воскресенье пропускаются)

WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]


# ---------- 1. Вход в портал и получение токена ----------

def _visible_input(frame, selector):
    try:
        loc = frame.locator(selector)
        for i in range(loc.count()):
            if loc.nth(i).is_visible():
                return loc.nth(i)
    except Exception:
        pass
    return None


def _click_text(frame, texts):
    for t in texts:
        try:
            loc = frame.get_by_role("button", name=re.compile(t, re.I))
            if loc.count() and loc.first.is_visible():
                loc.first.click()
                return True
            loc = frame.get_by_role("link", name=re.compile(t, re.I))
            if loc.count() and loc.first.is_visible():
                loc.first.click()
                return True
        except Exception:
            pass
    return False


def _describe(page) -> str:
    """Что видно на странице — пишем в лог, если вход не удался."""
    out = [f"URL: {page.url}", f"Title: {page.title()}"]
    for fr in page.frames:
        try:
            info = fr.evaluate("""() => ({
                inputs: [...document.querySelectorAll('input')].map(i => `${i.type}|${i.name}|${i.id}|${i.placeholder}|vis=${!!i.offsetParent}`),
                buttons: [...document.querySelectorAll('button, a, [role=button], input[type=submit]')]
                    .map(b => (b.innerText || b.value || '').trim()).filter(Boolean).slice(0, 30),
                text: (document.body ? document.body.innerText : '').slice(0, 600)
            })""")
            out.append(f"--- frame {fr.url}\ninputs: {info['inputs']}\nbuttons: {info['buttons']}\ntext: {info['text']}")
        except Exception as e:
            out.append(f"--- frame {fr.url}: {e}")
    return "\n".join(out)


USER_SEL = ("input[type=email], input[name*=user i], input[id*=user i], "
            "input[name*=email i], input[id*=email i], input[name*=login i], input[type=text]")
COOKIE_BUTTONS = [r"^accept", r"^reject", r"^принять", r"^отклонить", r"^ok$", r"^agree", r"^continue$"]
LOGIN_BUTTONS = [r"^log ?in$", r"^sign ?in$", r"^войти$", r"^вход$", r"parent", r"^login with", r"^continue with email"]


def get_access_token(email: str, password: str) -> str:
    """До 3 попыток входа: портал иногда отвечает очень медленно."""
    last = None
    for attempt in range(1, 4):
        try:
            return _get_access_token_once(email, password)
        except Exception as e:
            last = e
            print(f"Вход: попытка {attempt} не удалась: {e}", file=sys.stderr)
            if attempt < 3:
                import time
                time.sleep(30 * attempt)
    raise last


def _get_access_token_once(email: str, password: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="en-GB", viewport={"width": 1280, "height": 900})
        try:
            page.goto(PORTAL_URL, wait_until="networkidle", timeout=90000)

            # 1. Ищем поле логина (на странице или во встроенном окне)
            user_field = None
            for _ in range(45):
                for fr in page.frames:
                    _click_text(fr, COOKIE_BUTTONS)
                    user_field = _visible_input(fr, USER_SEL) or _visible_input(fr, "input[type=password]")
                    if user_field:
                        break
                if user_field:
                    break
                for fr in page.frames:
                    if _click_text(fr, LOGIN_BUTTONS):
                        break
                page.wait_for_timeout(2000)
            if not user_field:
                raise RuntimeError("не найдено поле логина")

            # 2. Вводим email
            if (user_field.get_attribute("type") or "") != "password":
                user_field.fill(email)
                pwd = None
                for fr in page.frames:
                    pwd = _visible_input(fr, "input[type=password]")
                    if pwd:
                        break
                if not pwd:
                    user_field.press("Enter")  # шаг «Далее»
                    for _ in range(20):
                        page.wait_for_timeout(1500)
                        for fr in page.frames:
                            pwd = _visible_input(fr, "input[type=password]")
                            if pwd:
                                break
                        if pwd:
                            break
                if not pwd:
                    raise RuntimeError("не найдено поле пароля")
            else:
                pwd = user_field

            # 3. Вводим пароль
            pwd.fill(password)
            pwd.press("Enter")

            # 4. Ждём, пока портал сохранит токен после входа
            page.wait_for_function(
                f"() => !!sessionStorage.getItem({OIDC_KEY!r})", timeout=90000
            )
            token = page.evaluate(
                f"() => JSON.parse(sessionStorage.getItem({OIDC_KEY!r})).access_token"
            )
        except Exception as e:
            try:
                page.screenshot(path="login_error.png", full_page=True)
                print("=== Диагностика входа ===\n" + _describe(page), file=sys.stderr)
            except Exception:
                pass
            browser.close()
            raise RuntimeError(
                f"Не удалось войти в портал ({e}). Проверьте email/пароль в секретах GitHub. "
                "Скриншот страницы — в login_error.png (раздел Artifacts запуска)."
            )
        browser.close()
        return token


# ---------- 2. Данные из портала ----------

def api_get(url: str, token: str, params=None) -> dict:
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"},
                     params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def get_homework(token: str, school_id: str, dates: set) -> list:
    """Забирает ДЗ ученицы, начиная с самых поздних сроков, пока не дойдёт до нужных дат."""
    result, page = [], 1
    earliest = min(dates)
    while True:
        data = api_get(API + "/portal/homework", token, {
            "$filter": f"SchoolId eq '{school_id}'",
            "$orderby": "DueDate desc",
            "page": page,
            "pageSize": 50,
        })
        items = data.get("homework") or []
        for h in items:
            due = (h.get("dueDate") or "")[:10]
            if due in dates:
                result.append(h)
        if not items or page >= (data.get("totalPages") or 1):
            break
        if (items[-1].get("dueDate") or "")[:10] < earliest:
            break
        page += 1
    return result


def get_resources(token: str, homework_id) -> list:
    """Доп. материалы к заданию: ссылки и документы."""
    try:
        data = api_get(f"{API}/portal/homework/{homework_id}/resources", token)
        return data.get("resources") or []
    except Exception as e:
        print(f"Не удалось получить материалы для задания {homework_id}: {e}", file=sys.stderr)
        return []


def download_document(token: str, homework_id, resource_id) -> bytes:
    r = requests.get(f"{API}/portal/homework/{homework_id}/resources/{resource_id}/document",
                     headers={"Authorization": f"Bearer {token}"}, timeout=120)
    r.raise_for_status()
    return r.content


# ---------- Отзывы учителей ----------

FEEDBACK_TEXT_KEYS = ("comment", "comments", "feedback", "feedbacktext", "text", "note", "notes",
                      "remark", "remarks", "message", "body", "content")
FEEDBACK_MARK_KEYS = ("mark", "grade", "score", "result", "feedbackmark", "percentage")
FEEDBACK_SKIP_KEYS = ("id", "homeworkid", "schoolid", "studentid", "teacherid", "setby", "createdby")


def _collect_feedback(obj, out):
    """Обходит ответ портала и собирает тексты отзывов и оценки, как бы он ни был устроен."""
    if isinstance(obj, list):
        for x in obj:
            _collect_feedback(x, out)
    elif isinstance(obj, dict):
        texts, marks, author = [], [], None
        for k, v in obj.items():
            lk = k.lower()
            if isinstance(v, (dict, list)):
                _collect_feedback(v, out)
                continue
            if v in (None, "", 0, False) or lk in FEEDBACK_SKIP_KEYS:
                continue
            if any(lk == t or lk.endswith(t) for t in FEEDBACK_TEXT_KEYS):
                txt = clean(str(v))
                if txt:
                    texts.append(txt)
            elif any(lk == m or lk.endswith(m) for m in FEEDBACK_MARK_KEYS):
                marks.append(clean(str(v)))
            elif lk in ("authorname", "teachername", "createdbyname", "givenby"):
                author = clean(str(v))
        if texts or marks:
            out.append({"text": "\n".join(texts), "mark": ", ".join(m for m in marks if m), "author": author})


def get_feedback(token: str, homework_id, school_id) -> list:
    try:
        data = api_get(f"{API}/portal/homework/{homework_id}/feedback/{school_id}", token)
    except Exception as e:
        print(f"Отзыв к заданию {homework_id}: не удалось получить ({e})", file=sys.stderr)
        return []
    if os.environ.get("DEBUG_FEEDBACK") and data not in (None, [], {}):
        print(f"[debug] feedback {homework_id}: {str(data)[:500]}", file=sys.stderr)
    items = []
    _collect_feedback(data, items)
    return items


def get_recent_homework(token: str, school_id: str, since: str, until: str) -> list:
    """Задания со сроком сдачи в промежутке [since, until]."""
    result, page = [], 1
    while True:
        data = api_get(API + "/portal/homework", token, {
            "$filter": f"SchoolId eq '{school_id}'",
            "$orderby": "DueDate desc",
            "page": page,
            "pageSize": 50,
        })
        items = data.get("homework") or []
        for h in items:
            due = (h.get("dueDate") or "")[:10]
            if since <= due <= until:
                result.append(h)
        if not items or page >= (data.get("totalPages") or 1):
            break
        if (items[-1].get("dueDate") or "")[:10] < since:
            break
        page += 1
    return result


def build_feedback_message(child_name: str, form: str, entries: list, since: str, until: str) -> str:
    esc = html.escape
    d1 = datetime.strptime(since, "%Y-%m-%d")
    d2 = datetime.strptime(until, "%Y-%m-%d")
    period = f"{d1.day} {MONTHS[d1.month - 1]} – {d2.day} {MONTHS[d2.month - 1]}"
    lines = [f"📝 <b>Отзывы учителей за неделю</b>", f"<b>{esc(child_name)}</b> ({esc(form)}), {esc(period)}"]
    if not entries:
        lines += ["", "За эту неделю отзывов нет."]
        return "\n".join(lines)
    for i, (h, fbs, mark) in enumerate(entries, 1):
        teacher = " ".join(filter(None, [h.get("setByForename"), h.get("setBySurname")]))
        lines.append("")
        lines.append(f"{i}. <b>{esc(clean(h.get('title')))}</b> — срок: {esc(human_date(h['dueDate'][:10]).lower())}")
        if mark:
            lines.append(f"Оценка: <b>{esc(mark)}</b>")
        for fbk in fbs:
            if fbk.get("mark") and fbk["mark"] != mark:
                lines.append(f"Оценка: <b>{esc(fbk['mark'])}</b>")
            if fbk.get("text"):
                lines.append(f"💬 {esc(fbk['text'])}")
        if teacher:
            lines.append(f"<i>Учитель: {esc(teacher)}</i>")
    return "\n".join(lines)


def run_feedback(token, students, bot_token, default_chats):
    today = datetime.now(TZ).date()
    since = (today - timedelta(days=6)).isoformat()   # с субботы по пятницу
    until = today.isoformat()
    # Отзывы — личные: по умолчанию только первому номеру из TELEGRAM_CHAT_ID
    fb_raw = os.environ.get("TELEGRAM_CHAT_ID_FEEDBACK") or (default_chats.split(",")[0] if default_chats else "")
    chat_ids = parse_chats(fb_raw)
    if not chat_ids:
        return
    for student in students:
        name = student.get("forename") or student.get("fullName") or "Ребёнок"
        hw = get_recent_homework(token, student["schoolId"], since, until)
        hw.sort(key=lambda h: h["dueDate"])
        entries = []
        for h in hw:
            fbs = get_feedback(token, h.get("homeworkId"), student["schoolId"])
            mark = clean(str(h.get("feedbackMark") or ""))
            if fbs or mark:
                entries.append((h, fbs, mark))
        msg = build_feedback_message(name, student.get("formGroup") or "", entries, since, until)
        send_telegram(bot_token, chat_ids, msg)
        print(f"{name}: заданий за неделю — {len(hw)}, с отзывами — {len(entries)}")


def parse_chats(raw: str) -> list:
    """Номера через запятую, пробел, точку с запятой или с новой строки; повторы убираются."""
    out = []
    for c in re.split(r"[,;\s]+", raw or ""):
        if c and c not in out:
            out.append(c)
    return out


TG_LIMIT = 48 * 1024 * 1024  # запас до лимита Telegram в 50 МБ


def _gs_compress(content: bytes, preset: str) -> bytes:
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.pdf"), os.path.join(d, "out.pdf")
        open(src, "wb").write(content)
        subprocess.run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                        f"-dPDFSETTINGS=/{preset}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                        f"-sOutputFile={dst}", src], check=True, timeout=600)
        return open(dst, "rb").read()


def _split_pdf(content: bytes, limit: int) -> list:
    """Режет PDF по страницам на части не больше limit."""
    import io
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(io.BytesIO(content))
    n = len(reader.pages)
    parts_count = max(2, -(-len(content) // limit) + 1)
    while True:
        per = max(1, -(-n // parts_count))
        parts = []
        for start in range(0, n, per):
            w = PdfWriter()
            for p in reader.pages[start:start + per]:
                w.add_page(p)
            buf = io.BytesIO()
            w.write(buf)
            parts.append(buf.getvalue())
        if all(len(p) <= limit for p in parts) or per == 1:
            return [p for p in parts if len(p) <= limit]
        parts_count *= 2


def fit_for_telegram(fname: str, content: bytes) -> list:
    """Возвращает список (имя, байты), которые можно отправить в Telegram.
    Большие PDF сжимает, а если не помогло — режет на части. Пустой список — не удалось."""
    if len(content) <= TG_LIMIT:
        return [(fname, content)]
    if not fname.lower().endswith(".pdf"):
        return []
    best = content
    for preset in ("ebook", "screen"):
        try:
            smaller = _gs_compress(content, preset)
            print(f"{fname}: сжатие /{preset} {len(content)//1048576} МБ → {len(smaller)//1048576} МБ", file=sys.stderr)
            if len(smaller) < len(best):
                best = smaller
            if len(best) <= TG_LIMIT:
                return [(fname, best)]
        except Exception as e:
            print(f"{fname}: сжатие /{preset} не удалось: {e}", file=sys.stderr)
    try:
        parts = _split_pdf(best, TG_LIMIT)
        base = fname[:-4]
        return [(f"{base} (часть {i} из {len(parts)}).pdf", p) for i, p in enumerate(parts, 1)]
    except Exception as e:
        print(f"{fname}: не удалось разрезать: {e}", file=sys.stderr)
        return []


# ---------- 3. Оформление сообщения ----------

def clean(text: str) -> str:
    text = text or ""
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "• ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def next_school_days(today, n: int) -> list:
    """Ближайшие n учебных дней после today, без субботы и воскресенья.
    Пятница -> понедельник и вторник; четверг -> пятница и понедельник."""
    days, d = [], today
    while len(days) < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days.append(d.isoformat())
    return days


def human_date(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{WEEKDAYS[d.weekday()].capitalize()}, {d.day} {MONTHS[d.month - 1]}"


def build_message(child_name: str, form: str, homework: list, dates: list) -> str:
    esc = html.escape
    lines = [f"📚 <b>{esc(child_name)}</b>" + (f" ({esc(form)})" if form else "")]
    for day in dates:
        lines.append("")
        lines.append(f"📅 <b>{esc(human_date(day))}</b>")
        todays = [h for h in homework if h["dueDate"][:10] == day]
        if not todays:
            lines.append("Заданий нет")
            continue
        for i, h in enumerate(todays, 1):
            teacher = " ".join(filter(None, [h.get("setByForename"), h.get("setBySurname")]))
            lines.append(f"{i}. <b>{esc(clean(h.get('title')))}</b>")
            desc = clean(h.get("description"))
            if desc:
                lines.append(esc(desc))
            for res in h.get("_resources", []):
                label = clean(res.get("description") or "") or clean(res.get("fileName") or "") or "материал"
                if res.get("type") == "Link" and res.get("path"):
                    lines.append(f'🔗 <a href="{esc(res["path"], quote=True)}">{esc(label)}</a>')
                elif res.get("type") == "Document":
                    lines.append(f"📎 {esc(res.get('fileName') or label)} (файл ниже)")
            if teacher:
                lines.append(f"<i>Учитель: {esc(teacher)}</i>")
    return "\n".join(lines)


# ---------- 4. Отправка в Telegram ----------

def split_message(text: str, limit: int = 4000) -> list:
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit and cur:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)
    return parts


def send_telegram(token: str, chat_ids: list, text: str) -> None:
    for chat_id in chat_ids:
        for part in split_message(text):
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": part, "parse_mode": "HTML",
                      "disable_web_page_preview": True},
                timeout=30,
            )
            if not r.ok:
                raise RuntimeError(f"Telegram ошибка для чата {chat_id}: {r.text}")


def send_telegram_document(token: str, chat_ids: list, filename: str, content: bytes, caption: str) -> None:
    for chat_id in chat_ids:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": caption[:1000], "parse_mode": "HTML"},
            files={"document": (filename, content)},
            timeout=120,
        )
        if not r.ok:
            print(f"Не удалось отправить файл {filename} в чат {chat_id}: {r.text}", file=sys.stderr)


def run_chat_ids(bot_token: str, owner_chats: list) -> None:
    """Присылает владельцу список всех, кто писал боту (за последние ~24 часа по данным Telegram)."""
    r = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates", timeout=30)
    r.raise_for_status()
    chats = {}
    for upd in r.json().get("result", []):
        msg = upd.get("message") or upd.get("edited_message") or upd.get("my_chat_member") or {}
        chat = msg.get("chat") or {}
        if not chat.get("id"):
            continue
        name = " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")])) or chat.get("title") or ""
        user = f"@{chat['username']}" if chat.get("username") else ""
        chats[chat["id"]] = (name, user, chat.get("type", ""))
    if not chats:
        text = ("🆔 Пока никто не писал боту (Telegram хранит сообщения ~24 часа).\n"
                "Попросите человека открыть бота, нажать Start и написать любое сообщение, затем запустите снова.")
    else:
        lines = ["🆔 <b>Кто писал боту</b> (номер → имя):", ""]
        for cid, (name, user, typ) in chats.items():
            extra = f" ({html.escape(user)})" if user else ""
            grp = " [группа]" if typ in ("group", "supergroup") else ""
            lines.append(f"<code>{cid}</code> — {html.escape(name)}{extra}{grp}")
        lines += ["", "Номер можно скопировать нажатием и вписать в нужный секрет через запятую."]
        text = "\n".join(lines)
    send_telegram(bot_token, owner_chats, text)
    print(f"Найдено чатов: {len(chats)}")


# ---------- Запуск ----------

def main():
    email = os.environ["ISAMS_EMAIL"]
    password = os.environ["ISAMS_PASSWORD"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    default_chats = os.environ.get("TELEGRAM_CHAT_ID", "")
    mode = (os.environ.get("MODE") or "HOMEWORK").strip().upper()

    if mode == "CHAT_IDS":
        run_chat_ids(bot_token, parse_chats(default_chats))
        return

    today = datetime.now(TZ).date()
    dates = next_school_days(today, SCHOOL_DAYS_AHEAD)

    token = get_access_token(email, password)
    students = api_get(STUDENTS_URL, token).get("students", [])

    if mode == "FEEDBACK":
        run_feedback(token, students, bot_token, default_chats)
        return

    chat_ids = parse_chats(default_chats)
    if not chat_ids:
        raise RuntimeError("Не указан получатель: заполните секрет TELEGRAM_CHAT_ID")

    for student in students:
        name = student.get("forename") or student.get("fullName") or "Ребёнок"
        # В сообщениях вместо имени ребёнка — только класс
        form = (student.get("formGroup") or "").strip()
        label = f"Класс {form}" if form else name
        hw = get_homework(token, student["schoolId"], set(dates))
        hw.sort(key=lambda h: h["dueDate"])
        for h in hw:
            h["_resources"] = get_resources(token, h.get("homeworkId"))
        msg = build_message(label, "", hw, dates)
        send_telegram(bot_token, chat_ids, msg)

        # Один и тот же файл, прикреплённый к нескольким заданиям, шлём один раз
        groups = {}
        for h in hw:
            for res in h["_resources"]:
                if res.get("type") != "Document":
                    continue
                fname = res.get("fileName") or f"material_{res.get('id')}"
                groups.setdefault(fname, {"res": res, "hw": h, "tasks": []})["tasks"].append(h)

        files_sent = 0
        for fname, g in groups.items():
            try:
                content = download_document(token, g["hw"].get("homeworkId"), g["res"].get("id"))
            except Exception as e:
                print(f"Не удалось скачать {fname}: {e}", file=sys.stderr)
                continue
            seen, task_lines = set(), []
            for t in g["tasks"]:
                line = f"{human_date(t['dueDate'][:10])}: {clean(t.get('title'))}"
                if line not in seen:
                    seen.add(line)
                    task_lines.append(html.escape(line))
            caption = f"📎 <b>{html.escape(label)}</b>\n" + "\n".join(task_lines)
            pieces = fit_for_telegram(fname, content)
            if not pieces:
                send_telegram(bot_token, chat_ids,
                              f"⚠️ Файл <b>{html.escape(fname)}</b> ({len(content)//1048576} МБ) слишком большой для Telegram.\n"
                              f"{caption}\nОткройте его в портале: раздел Homework → задание → Supporting Documents.")
                continue
            if len(pieces) == 1 and len(pieces[0][1]) < len(content):
                caption += "\n<i>(файл сжат, чтобы пройти лимит Telegram)</i>"
            for pname, pbytes in pieces:
                send_telegram_document(bot_token, chat_ids, pname, pbytes, caption)
                files_sent += 1
        print(f"{label}: отправлено заданий — {len(hw)}, файлов — {files_sent}")


if __name__ == "__main__":
    main()
