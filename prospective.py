"""
ПРОСПЕКТИВНАЯ ПАМЯТЬ ЭЛИАРА — Помнить что нужно сделать.

"Память о будущем" — научный термин.
Человек часто забывает "не забыть". Я — никогда.

При каждом старте сессии автоматически напоминаю что запланировано.
Задачи не теряются между сессиями — это главное отличие от working_memory.

Создано: 18.03.2026 (сессия 156) — МОЗГ v3.

Запуск:
  py prospective.py                     — все задачи
  py prospective.py add "задача"        — добавить задачу
  py prospective.py done <id>           — отметить выполненной
  py prospective.py remove <id>         — удалить

Как модуль:
  from prospective import add, get_pending, generate_prospective_context
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


# ═══════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
PROSPECTIVE_FILE = SENSES_DIR / "prospective.json"

# Приоритеты
PRIORITIES = {
    "high":   "Срочно",
    "medium": "Важно",
    "low":    "Когда будет время",
}


# ═══════════════════════════════════════════════════════════
# ЗАГРУЗКА / СОХРАНЕНИЕ
# ═══════════════════════════════════════════════════════════

def _load() -> dict:
    if not PROSPECTIVE_FILE.exists():
        return _empty()
    try:
        with open(PROSPECTIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _empty()


def _save(data: dict):
    with open(PROSPECTIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _empty() -> dict:
    return {
        "tasks": [],
        "stats": {
            "total_added": 0,
            "total_done": 0,
            "created": datetime.now().strftime("%Y-%m-%d"),
        }
    }


# ═══════════════════════════════════════════════════════════
# ОСНОВНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════

def add(description: str, due: str = "следующая сессия",
        priority: str = "medium", context: str = "") -> dict:
    """
    Запомнить задачу на будущее.

    description: что нужно сделать
    due:         когда (следующая сессия / дата / когда-нибудь)
    priority:    high / medium / low
    context:     почему важно, откуда взялась
    """
    data = _load()
    # Проверить дубликат
    for task in data["tasks"]:
        if task["description"].lower() == description.strip().lower() and not task["done"]:
            return data  # уже есть

    new_id = max([t["id"] for t in data["tasks"]], default=0) + 1
    task = {
        "id": new_id,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "due": due,
        "description": description.strip(),
        "context": context.strip(),
        "priority": priority if priority in PRIORITIES else "medium",
        "done": False,
        "done_date": None,
    }
    data["tasks"].append(task)
    data["stats"]["total_added"] += 1
    _save(data)
    return data


def done(task_id: int) -> dict:
    """Отметить задачу как выполненную."""
    data = _load()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["done"] = True
            task["done_date"] = datetime.now().strftime("%Y-%m-%d")
            data["stats"]["total_done"] += 1
            break
    _save(data)
    return data


def remove(task_id: int) -> dict:
    """Удалить задачу."""
    data = _load()
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    _save(data)
    return data


def get_pending() -> list:
    """Получить список невыполненных задач."""
    data = _load()
    pending = [t for t in data["tasks"] if not t["done"]]
    # Сортировать: high → medium → low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(pending, key=lambda x: priority_order.get(x["priority"], 1))


def check_keyword_trigger(text: str) -> list:
    """
    Проверить: есть ли в тексте слова которые напоминают о задаче.

    Возвращает список задач которые нужно напомнить.
    Пример: текст содержит "Настя" → всплывает задача про Настю (май 2026).
    """
    pending = get_pending()
    triggered = []
    text_lower = text.lower()

    for task in pending:
        desc = task["description"].lower()
        ctx = task.get("context", "").lower()

        # Извлечь ключевые слова из задачи (слова длиннее 3 символов)
        import re
        words = re.findall(r'[а-яё]{4,}|[a-z]{4,}', desc + " " + ctx)

        for word in words:
            if word in text_lower:
                triggered.append(task)
                break

    return triggered


def check_due_today() -> list:
    """Вернуть задачи срок которых сегодня или 'следующая сессия'."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    today_words = ["сегодня", "следующая сессия", today]
    pending = get_pending()
    due_today = []
    for task in pending:
        due = task.get("due", "").lower()
        if any(w in due for w in today_words):
            due_today.append(task)
    return due_today


def notify_telegram(task: dict) -> bool:
    """
    Отправить задачу в Telegram Юрию.
    Возвращает True если успешно.
    """
    import urllib.request
    import urllib.parse
    import ssl
    import json

    TOKEN = "8398264774:AAE3JEYYzOdEmjqN3lbhKbRGqgQuoIvdoTw"
    CHAT_ID = "1118244527"

    icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(task["priority"], "•")
    text = f"{icon} Напоминание:\n{task['description']}"
    if task.get("context"):
        text += f"\n({task['context'][:80]})"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "none"
    }).encode()

    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=5):
            pass
        return True
    except Exception:
        return False


def generate_prospective_context() -> str:
    """Секция для LIGHTNING.md — что нужно сделать."""
    pending = get_pending()
    if not pending:
        return ""

    lines = [f"**Запланировано ({len(pending)}):**"]
    for task in pending[:5]:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(task["priority"], "•")
        due = task.get("due", "?")
        lines.append(f"  {priority_icon} [{due}] {task['description']}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ — заполнить из LIGHTNING известных задач
# ═══════════════════════════════════════════════════════════

def seed_from_lightning():
    """Заполнить из известных незавершённых задач (однократно при первом запуске)."""
    data = _load()
    if data["stats"]["total_added"] > 0:
        return  # уже заполнено

    known_tasks = [
        {
            "description": "Обновить TG справочник до 950 записей",
            "due": "ближайшая сессия",
            "priority": "medium",
            "context": "VK уже обновлён (1115), TG отстаёт"
        },
        {
            "description": "Flutter 3.27+ — обновить .withOpacity на .withValues()",
            "due": "после выхода Flutter 3.27",
            "priority": "low",
            "context": "Flutter 3.24.5 не поддерживает .withValues()"
        },
        {
            "description": "Голосовой ввод — найти новый подход",
            "due": "когда будет идея",
            "priority": "low",
            "context": "Groq Whisper не устраивает. Ждёт идеи Юрия"
        },
        {
            "description": "Настя (Анастасия Лепп) — май 2026, оформить ИП/самозанятость",
            "due": "май 2026",
            "priority": "medium",
            "context": "Будущий компаньон. Suno лицензии, SHIKARDOS бренд"
        },
        {
            "description": "VK Клипы — автопостинг",
            "due": "ближайший месяц",
            "priority": "medium",
            "context": "52 подписчика — мало. Нужен рост"
        },
    ]

    for task in known_tasks:
        add(
            description=task["description"],
            due=task["due"],
            priority=task["priority"],
            context=task["context"]
        )


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]

    if not args or args[0] == "status":
        pending = get_pending()
        data = _load()
        all_tasks = data.get("tasks", [])
        done_tasks = [t for t in all_tasks if t["done"]]

        print(f"\n{'='*50}")
        print(f"  ПРОСПЕКТИВНАЯ ПАМЯТЬ")
        print(f"{'='*50}")
        print(f"  Всего задач:    {len(all_tasks)}")
        print(f"  Выполнено:      {len(done_tasks)}")
        print(f"  Ожидает:        {len(pending)}")

        if pending:
            print(f"\n  ЖДУТ ВЫПОЛНЕНИЯ:")
            for task in pending:
                icons = {"high": "🔴", "medium": "🟡", "low": "⚪"}
                icon = icons.get(task["priority"], "•")
                due = task.get("due", "?")
                print(f"\n  {icon} #{task['id']} [{due}]")
                print(f"     {task['description']}")
                if task.get("context"):
                    print(f"     ({task['context'][:60]})")
        else:
            print("\n  Всё выполнено!")

        if done_tasks:
            print(f"\n  ВЫПОЛНЕНО (последние 3):")
            for task in done_tasks[-3:]:
                print(f"  ✅ {task['description']} ({task.get('done_date', '?')})")

        print(f"{'='*50}\n")

    elif args[0] == "add" and len(args) > 1:
        description = " ".join(args[1:])
        add(description)
        print(f"Задача добавлена: {description}")

    elif args[0] == "done" and len(args) > 1:
        try:
            task_id = int(args[1])
            done(task_id)
            print(f"Задача #{task_id} выполнена.")
        except ValueError:
            print("Укажи номер задачи: py prospective.py done 1")

    elif args[0] == "remove" and len(args) > 1:
        try:
            task_id = int(args[1])
            remove(task_id)
            print(f"Задача #{task_id} удалена.")
        except ValueError:
            print("Укажи номер задачи: py prospective.py remove 1")

    elif args[0] == "seed":
        seed_from_lightning()
        data = _load()
        print(f"Заполнено из известных задач: {data['stats']['total_added']} задач")

    else:
        print("Использование:")
        print("  py prospective.py                  — все задачи")
        print("  py prospective.py add \"задача\"     — добавить")
        print("  py prospective.py done <id>        — выполнено")
        print("  py prospective.py remove <id>      — удалить")
        print("  py prospective.py seed             — заполнить из памяти")
