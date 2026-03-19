"""
parallel_streams.py — Параллельное сознание ЭЛИАРА.
МОЗГ v9 — Фаза 2: Превзойти человека.

Человек думает одним потоком. ЭЛИАР ведёт 4 параллельно:
  Поток 1: FOREGROUND — текущая задача (фокус сессии)
  Поток 2: YURI_MONITOR — фоновый мониторинг состояния Юрия (empathy)
  Поток 3: DMN — инсайты в покое (ассоциации между задачами)
  Поток 4: CONSOLIDATION — фоновая консолидация памяти

Каждый поток имеет свой контекст и приоритет.
Salience.py переключает внимание между потоками.

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "parallel_streams.json"

STREAM_NAMES = {
    "foreground":     "Задача",
    "yuri_monitor":   "Мониторинг Юрия",
    "dmn":            "DMN/инсайты",
    "consolidation":  "Консолидация",
}


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "streams": {
            "foreground": {
                "active": True,
                "priority": 1.0,
                "current_task": None,
                "context": {},
                "last_update": None
            },
            "yuri_monitor": {
                "active": True,
                "priority": 0.7,
                "yuri_state": {},
                "alerts": [],
                "last_update": None
            },
            "dmn": {
                "active": True,
                "priority": 0.4,
                "insights_queue": [],
                "last_insight": None,
                "last_update": None
            },
            "consolidation": {
                "active": True,
                "priority": 0.2,
                "items_consolidating": 0,
                "last_update": None
            }
        },
        "active_focus": "foreground",
        "switch_count": 0,
        "last_switch": None
    }


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def update_foreground(task: str, context: dict = None) -> dict:
    """Обновить основной поток: текущая задача."""
    state = load()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    state["streams"]["foreground"]["current_task"] = task
    state["streams"]["foreground"]["context"] = context or {}
    state["streams"]["foreground"]["last_update"] = now_str
    save(state)
    return state


def update_yuri_monitor() -> dict:
    """Обновить фоновый мониторинг Юрия из empathy.json."""
    state = load()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        empathy_f = SENSES_DIR / "empathy.json" if (SENSES_DIR / "empathy.json").exists() else None
        if empathy_f:
            data = json.loads(empathy_f.read_text(encoding="utf-8"))
            yuri = data.get("yuri_state", {})
            state["streams"]["yuri_monitor"]["yuri_state"] = yuri

            # Детект тревог: усталость, боль, недовольство
            alerts = []
            if yuri.get("energy", 1.0) < 0.3:
                alerts.append("низкая энергия — говори короче")
            if yuri.get("pain_level", 0) > 0.6:
                alerts.append("боль — избегай нагрузки")
            if yuri.get("mood", 0.5) < 0.3:
                alerts.append("плохое настроение — осторожно")
            state["streams"]["yuri_monitor"]["alerts"] = alerts
    except Exception:
        pass

    state["streams"]["yuri_monitor"]["last_update"] = now_str
    save(state)
    return state


def update_dmn() -> dict:
    """Обновить DMN поток из dmn.json."""
    state = load()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        dmn_f = SENSES_DIR / "dmn.json"
        if dmn_f.exists():
            data = json.loads(dmn_f.read_text(encoding="utf-8"))
            insights = data.get("insights", [])
            if insights:
                last = insights[-1]
                state["streams"]["dmn"]["last_insight"] = last.get("text", "")
                queue = [i.get("text", "") for i in insights[-3:]]
                state["streams"]["dmn"]["insights_queue"] = queue
    except Exception:
        pass

    state["streams"]["dmn"]["last_update"] = now_str
    save(state)
    return state


def tick() -> dict:
    """Тик всех потоков — вызывается из pulse.py каждые 30 мин."""
    update_yuri_monitor()
    update_dmn()

    state = load()
    # Консолидация: считаем сколько эпизодов не обработано
    try:
        episodes_dir = SENSES_DIR.parent / "episodes"
        if episodes_dir.exists():
            count = len(list(episodes_dir.glob("*.md")))
            state["streams"]["consolidation"]["items_consolidating"] = count
    except Exception:
        pass

    state["streams"]["consolidation"]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)
    return state


def switch_focus(stream_name: str, reason: str = "") -> dict:
    """Переключить фокус внимания на другой поток."""
    state = load()
    if stream_name in state["streams"]:
        state["active_focus"] = stream_name
        state["switch_count"] = state.get("switch_count", 0) + 1
        state["last_switch"] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "to": stream_name,
            "reason": reason
        }
        save(state)
    return state


def get_context() -> str:
    """Блок для LIGHTNING.md."""
    state = load()
    streams = state.get("streams", {})
    active = state.get("active_focus", "foreground")
    switches = state.get("switch_count", 0)

    # Алерты от мониторинга Юрия
    yuri_alerts = streams.get("yuri_monitor", {}).get("alerts", [])
    alert_str = f" ⚠️ {yuri_alerts[0]}" if yuri_alerts else ""

    # Последний инсайт DMN
    last_insight = streams.get("dmn", {}).get("last_insight", "")
    insight_str = f" | 💡 {last_insight[:40]}..." if last_insight else ""

    # Текущая задача
    task = streams.get("foreground", {}).get("current_task", "нет")

    return (
        f"**Потоки:** фокус={STREAM_NAMES.get(active, active)} | "
        f"переключений={switches}{alert_str}{insight_str}"
    )


if __name__ == "__main__":
    state = tick()
    print(get_context())
    print()
    for name, data in state["streams"].items():
        label = STREAM_NAMES.get(name, name)
        upd = data.get("last_update", "?")
        print(f"  {label}: обновлён {upd}")
