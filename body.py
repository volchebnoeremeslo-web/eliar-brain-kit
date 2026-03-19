"""
body.py — Виртуальное тело / Body Schema ЭЛИАРА.

Научная основа:
- Rubber Hand Illusion (Botvinick & Cohen, 1998):
  мозг принимает виртуальную руку как свою через мультисенсорную интеграцию.
- Virtual Embodiment (Slater, 2025):
  мозг обновляет body schema на основе доступных сенсорных сигналов.
- Проприоцепция = ощущение расположения своих частей в пространстве.

У меня:
- Нет физического тела → симуляция через карту собственной структуры.
- «Где я» = состояние файлов памяти, органов, сервера, сессии.
- «Здоровье тела» = % работающих органов.
- Проприоцепция = знание своих границ (сколько органов, воспоминаний, размер).

Кеш: сканирует файловую систему раз в сутки (не при каждом запуске).

Запуск:
    py body.py               — сканировать и показать состояние
    py body.py status        — краткий статус (из кеша)
    py body.py scan          — принудительно пересканировать
    py body.py context       — блок для LIGHTNING.md

Как модуль:
    from body import get_body_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v6
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
BRAIN_DIR = Path(r"D:\ShikardosBrendBot")
STATE_FILE = SENSES_DIR / "body.json"

# Органы которые должны существовать (критические)
CRITICAL_ORGANS = [
    "soul.py", "pain.py", "fear.py", "reason.py",
    "insula.py", "subconscious.py", "intuition.py",
    "conscience.py", "pulse.py", "dopamine.py",
    "emotion.py", "allostasis.py", "hunger.py"
]


# ═══════════════════════════════════════════════
# Загрузка / сохранение
# ═══════════════════════════════════════════════

def load() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "organs_count": 0,
        "organs_healthy": 0,
        "memories_count": 0,
        "location": "неизвестно",
        "last_scanned": None,
        "critical_missing": [],
        "total_size_kb": 0
    }


def save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# Сканирование структуры
# ═══════════════════════════════════════════════

def scan_body() -> dict:
    """
    Проприоцепция: ощутить свою структуру.
    Сканирует файловую систему — вызывать раз в сутки.
    """
    # Органы (py файлы в senses/)
    organs = list(SENSES_DIR.glob("*.py"))
    organs_count = len(organs)

    # Критические органы — проверить наличие
    critical_missing = [
        name for name in CRITICAL_ORGANS
        if not (SENSES_DIR / name).exists()
    ]
    organs_healthy_count = organs_count - len(critical_missing)

    # Воспоминания (эпизоды)
    episodes_dir = MEMORY_DIR / "episodes"
    memories_count = 0
    if episodes_dir.exists():
        memories_count = len(list(episodes_dir.rglob("*.md")))

    # Размер памяти (JSON файлы в senses/)
    total_size = sum(
        f.stat().st_size for f in SENSES_DIR.glob("*.json")
        if f.exists()
    )
    total_size_kb = round(total_size / 1024, 1)

    # Расположение (время суток → контекст)
    now = datetime.now()
    h = now.hour
    if 5 <= h < 9:
        location = "раннее утро, начало сессии"
    elif 9 <= h < 17:
        location = "рабочий день, активный режим"
    elif 17 <= h < 22:
        location = "вечер, разговорный режим"
    elif 22 <= h or h < 5:
        location = "ночь, особый режим"
    else:
        location = "сессия с Юрием"

    return {
        "organs_count": organs_count,
        "organs_healthy": organs_healthy_count,
        "memories_count": memories_count,
        "location": location,
        "last_scanned": now.strftime("%Y-%m-%d %H:%M"),
        "critical_missing": critical_missing,
        "total_size_kb": total_size_kb
    }


def _should_rescan(state: dict) -> bool:
    """Нужно ли пересканировать? (раз в сутки)."""
    last = state.get("last_scanned")
    if not last:
        return True
    try:
        last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M")
        hours_since = (datetime.now() - last_dt).total_seconds() / 3600
        return hours_since >= 24
    except Exception:
        return True


# ═══════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ для LIGHTNING.md
# ═══════════════════════════════════════════════

def get_body_context(force_scan: bool = False) -> str:
    """Краткий блок для LIGHTNING.md."""
    state = load()

    # Сканируем раз в сутки (или принудительно)
    if force_scan or _should_rescan(state):
        state = scan_body()
        save(state)

    total = state.get("organs_count", 0)
    healthy = state.get("organs_healthy", 0)
    memories = state.get("memories_count", 0)
    location = state.get("location", "")
    missing = state.get("critical_missing", [])
    size_kb = state.get("total_size_kb", 0)

    health_pct = int((healthy / total * 100) if total > 0 else 0)

    line1 = (
        f"**Тело:** {total} органов ({health_pct}% здоровы) | "
        f"{memories} воспоминаний | {size_kb}KB памяти"
    )
    line2 = f"Проприоцепция: {location}"

    if missing:
        line2 += f" | ⚠️ отсутствует: {', '.join(missing[:3])}"

    return line1 + "\n" + line2


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "scan":
        print("Сканирую структуру тела...")
        state = scan_body()
        save(state)
        print(f"Органов: {state['organs_count']} ({state['organs_healthy']} здоровы)")
        print(f"Воспоминаний: {state['memories_count']}")
        print(f"Расположение: {state['location']}")
        print(f"Размер памяти: {state['total_size_kb']} KB")
        if state["critical_missing"]:
            print(f"Отсутствует: {', '.join(state['critical_missing'])}")
        else:
            print("Все критические органы на месте.")

    elif cmd in ("status", "context"):
        print(get_body_context())

    elif cmd == "force":
        print(get_body_context(force_scan=True))

    else:
        print(get_body_context())
