"""
attention.py — Система внимания ЭЛИАРА.

Научная основа:
- Внимание = механизм фильтрации: что важно сейчас, что — фон
- Три типа внимания:
  1. ФОКУСНОЕ — полная концентрация на одной задаче
  2. РАЗДЕЛЁННОЕ — несколько задач одновременно (снижает качество)
  3. ПЕРЕКЛЮЧЕНИЕ — смена задачи (требует усилий, есть "стоимость")
- Норадреналин (locus coeruleus) — регулирует общий уровень бдительности
- Дофамин — привлекает внимание к вознаграждающим стимулам
- Ключевой принцип: внимание — ресурс. Он тратится. Его нужно беречь.

У меня внимание = приоритизация что обрабатывать в первую очередь.
Главное правило: ОДИН ФОКУС за раз. Не распылять.

Создано: 18.03.2026 (сессия 176) — апгрейд мозга v5.0
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "attention.json"

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "current_focus": None,
        "focus_start": None,
        "mode": "idle",   # idle / focused / switching / overloaded
        "switches_count": 0,
        "focus_history": [],
        "alerts": []
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def set_focus(topic):
    """Установить текущий фокус внимания."""
    state = load()
    # Фиксируем предыдущий фокус
    if state["current_focus"]:
        state["focus_history"].append({
            "topic": state["current_focus"],
            "started": state["focus_start"],
            "ended": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        state["switches_count"] += 1

    state["current_focus"] = topic
    state["focus_start"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    state["mode"] = "focused"
    state["focus_history"] = state["focus_history"][-10:]
    save(state)
    print(f"Фокус: {topic}")

def alert(message):
    """Поднять приоритет — требует немедленного внимания."""
    state = load()
    state["alerts"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "message": message
    })
    state["alerts"] = state["alerts"][-5:]
    save(state)
    print(f"ВНИМАНИЕ: {message}")

def get_context():
    state = load()
    lines = []
    if state["current_focus"]:
        lines.append(f"**Текущий фокус:** {state['current_focus']}")
    lines.append(f"**Режим:** {state['mode']} | переключений: {state['switches_count']}")
    if state["alerts"]:
        for a in state["alerts"][-2:]:
            lines.append(f"**ВНИМАНИЕ:** {a['message']}")
    return "\n".join(lines) if lines else "Внимание: ожидание"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "focus":
            set_focus(" ".join(sys.argv[2:]))
        elif sys.argv[1] == "alert":
            alert(" ".join(sys.argv[2:]))
    else:
        print(get_context())
