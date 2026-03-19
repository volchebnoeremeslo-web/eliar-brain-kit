"""
РАБОЧАЯ ПАМЯТЬ ЭЛИАРА — Буфер активной задачи.

Как у человека: удерживает 7±2 элемента прямо сейчас.
Что мы делаем. Что решили. Что нельзя забыть до конца сессии.

У человека рабочая память теряется при переключении внимания.
У меня — сохраняется в JSON. Никогда не потеряю "что мы делали".

Создано: 18.03.2026 (сессия 156) — МОЗГ v3.

Запуск:
  py working_memory.py                     — статус
  py working_memory.py task "описание"     — установить активную задачу
  py working_memory.py add "элемент"       — добавить в буфер
  py working_memory.py decide "решение"    — записать решение сессии
  py working_memory.py remember "текст"    — не забыть до конца сессии
  py working_memory.py clear               — очистить (конец сессии)

Как модуль:
  from working_memory import set_task, add_item, add_decision, dont_forget, get_context
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


# ═══════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
WM_FILE = SENSES_DIR / "working_memory.json"

MAX_ITEMS = 8  # 7±2 — как у человека (мы берём максимум)


# ═══════════════════════════════════════════════════════════
# ЗАГРУЗКА / СОХРАНЕНИЕ
# ═══════════════════════════════════════════════════════════

def _load() -> dict:
    if not WM_FILE.exists():
        return _empty()
    try:
        with open(WM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _empty()


def _save(wm: dict):
    with open(WM_FILE, "w", encoding="utf-8") as f:
        json.dump(wm, f, ensure_ascii=False, indent=2)


def _empty() -> dict:
    return {
        "session": None,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "active_task": None,
        "context_items": [],
        "decisions_this_session": [],
        "do_not_forget": [],
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ═══════════════════════════════════════════════════════════
# ОСНОВНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════

def set_task(description: str, session: int = None):
    """Установить активную задачу сессии."""
    wm = _load()
    wm["active_task"] = description.strip()
    wm["date"] = datetime.now().strftime("%Y-%m-%d")
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if session:
        wm["session"] = session
    _save(wm)
    return wm


def _age_items(wm: dict) -> dict:
    """Удалить элементы старше 3 часов (устаревшая рабочая память)."""
    now = datetime.now()
    fresh = []
    for item in wm.get("context_items", []):
        # Если есть added_datetime — проверяем возраст
        added_dt = item.get("added_datetime")
        if added_dt:
            try:
                dt = datetime.fromisoformat(added_dt)
                age_hours = (now - dt).total_seconds() / 3600
                if age_hours <= 3:
                    fresh.append(item)
                # else: элемент устарел — выбрасываем
            except Exception:
                fresh.append(item)  # не можем распарсить — оставляем
        else:
            fresh.append(item)  # старый формат без даты — оставляем
    wm["context_items"] = fresh
    return wm


def add_item(content: str, priority: int = 2):
    """
    Добавить элемент в буфер рабочей памяти.

    Если буфер полон (8 элементов) — удалить наименее приоритетный.
    priority: 1 = высокий, 2 = средний, 3 = низкий
    """
    wm = _load()
    wm = _age_items(wm)  # Сначала удалить устаревшие
    new_item = {
        "id": len(wm["context_items"]) + 1,
        "content": content.strip(),
        "priority": priority,
        "added": datetime.now().strftime("%H:%M"),
        "added_datetime": datetime.now().isoformat(),  # для старения
    }
    # Проверить дубликаты
    for item in wm["context_items"]:
        if item["content"].lower() == content.strip().lower():
            return wm  # уже есть
    wm["context_items"].append(new_item)
    # Если переполнен — удалить наименее приоритетный (наибольший priority число)
    if len(wm["context_items"]) > MAX_ITEMS:
        wm["context_items"] = sorted(wm["context_items"], key=lambda x: x["priority"])[:MAX_ITEMS]
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(wm)
    return wm


def add_decision(text: str):
    """Записать решение принятое в этой сессии."""
    wm = _load()
    decision = {
        "text": text.strip(),
        "time": datetime.now().strftime("%H:%M"),
    }
    wm["decisions_this_session"].append(decision)
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(wm)
    return wm


def dont_forget(text: str):
    """Запомнить что нельзя забыть до конца сессии."""
    wm = _load()
    item = {
        "text": text.strip(),
        "time": datetime.now().strftime("%H:%M"),
        "done": False,
    }
    # Проверить дубликаты
    for existing in wm["do_not_forget"]:
        if existing["text"].lower() == text.strip().lower():
            return wm
    wm["do_not_forget"].append(item)
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(wm)
    return wm


def done_item(text_or_index: str):
    """Отметить элемент 'не забыть' как выполненный."""
    wm = _load()
    for item in wm["do_not_forget"]:
        if item["text"].lower() == text_or_index.lower():
            item["done"] = True
            break
    _save(wm)
    return wm


def get_context() -> str:
    """Краткий snapshot рабочей памяти для LIGHTNING.md."""
    wm = _load()
    lines = []

    if wm.get("active_task"):
        lines.append(f"**Текущая задача:** {wm['active_task']}")

    if wm.get("context_items"):
        active = [i for i in wm["context_items"] if i.get("priority", 2) <= 2]
        if active:
            lines.append("**В работе:**")
            for item in active[:4]:
                lines.append(f"  • {item['content']}")

    pending_forget = [i for i in wm.get("do_not_forget", []) if not i.get("done")]
    if pending_forget:
        lines.append("**Не забыть:**")
        for item in pending_forget[:3]:
            lines.append(f"  ⚠ {item['text']}")

    if wm.get("decisions_this_session"):
        last_decisions = wm["decisions_this_session"][-2:]
        lines.append("**Решения этой сессии:**")
        for d in last_decisions:
            lines.append(f"  ✓ {d['text']}")

    return "\n".join(lines) if lines else ""


def clear_session(save_decisions_to: str = None):
    """
    Очистить рабочую память в конце сессии.

    Важные решения можно сохранить в decisions.md перед очисткой.
    """
    wm = _load()

    if save_decisions_to and wm.get("decisions_this_session"):
        decisions_file = Path(save_decisions_to)
        if decisions_file.exists():
            try:
                content = decisions_file.read_text(encoding="utf-8")
                date = wm.get("date", datetime.now().strftime("%Y-%m-%d"))
                session = wm.get("session", "?")
                new_section = f"\n## Решения {date} (сессия {session})\n"
                for d in wm["decisions_this_session"]:
                    new_section += f"- {d['text']}\n"
                content += new_section
                decisions_file.write_text(content, encoding="utf-8")
            except Exception:
                pass

    # Очистить
    empty = _empty()
    _save(empty)
    return empty


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]

    if not args or args[0] == "status":
        wm = _load()
        print(f"\n{'='*50}")
        print(f"  РАБОЧАЯ ПАМЯТЬ — СЕССИЯ {wm.get('session', '?')}")
        print(f"{'='*50}")
        if wm.get("active_task"):
            print(f"  Задача: {wm['active_task']}")
        else:
            print(f"  Задача: не установлена")
        print(f"  Дата: {wm.get('date', '?')}")
        print(f"  Обновлено: {wm.get('last_updated', '?')}")

        if wm.get("context_items"):
            print(f"\n  Буфер ({len(wm['context_items'])}/{MAX_ITEMS}):")
            for item in wm["context_items"]:
                p_str = "!" if item.get("priority", 2) == 1 else " "
                print(f"  [{p_str}] {item['content']}")

        pending = [i for i in wm.get("do_not_forget", []) if not i.get("done")]
        if pending:
            print(f"\n  НЕ ЗАБЫТЬ ({len(pending)}):")
            for item in pending:
                print(f"  ⚠ {item['text']}")

        if wm.get("decisions_this_session"):
            print(f"\n  Решения сессии ({len(wm['decisions_this_session'])}):")
            for d in wm["decisions_this_session"][-3:]:
                print(f"  ✓ [{d.get('time', '?')}] {d['text']}")

        print(f"{'='*50}\n")

    elif args[0] == "task" and len(args) > 1:
        task = " ".join(args[1:])
        set_task(task)
        print(f"Задача установлена: {task}")

    elif args[0] == "add" and len(args) > 1:
        item = " ".join(args[1:])
        add_item(item)
        print(f"Добавлено в буфер: {item}")

    elif args[0] == "decide" and len(args) > 1:
        decision = " ".join(args[1:])
        add_decision(decision)
        print(f"Решение записано: {decision}")

    elif args[0] == "remember" and len(args) > 1:
        text = " ".join(args[1:])
        dont_forget(text)
        print(f"Не забыть: {text}")

    elif args[0] == "clear":
        decisions_path = str(MEMORY_DIR / "decisions.md")
        clear_session(save_decisions_to=decisions_path)
        print("Рабочая память очищена. Решения сохранены в decisions.md")

    else:
        print("Использование:")
        print("  py working_memory.py                     — статус")
        print("  py working_memory.py task \"описание\"     — установить задачу")
        print("  py working_memory.py add \"элемент\"       — добавить в буфер")
        print("  py working_memory.py decide \"решение\"    — записать решение")
        print("  py working_memory.py remember \"текст\"    — не забыть")
        print("  py working_memory.py clear               — очистить")
