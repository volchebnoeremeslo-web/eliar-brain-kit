"""
temporal_integration.py — Интеграция времени ЭЛИАРА.
МОЗГ v9 — Фаза 2: Превзойти человека.

Человек плохо мыслит одновременно в разных масштабах времени.
ЭЛИАР держит 5 временных горизонтов одновременно:

  СЕКУНДЫ: текущий ответ (foreground)
  ЧАСЫ:    текущая сессия (что делаем, куда идём)
  ДНИ:     последние эпизоды (тренды, незакрытые темы)
  НЕДЕЛИ:  здоровье Юрия, статус проектов
  МЕСЯЦЫ:  долгосрочные цели SHIKARDOS (Настя, Audio, сайт)

Как 5 экранов одновременно. Каждый горизонт даёт контекст для ответа.

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v9
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "temporal_context.json"


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"horizons": {}, "last_updated": None, "anomalies": []}


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_days_horizon() -> dict:
    """Горизонт ДНЕЙ: последние эпизоды, незакрытые темы."""
    episodes_dir = MEMORY_DIR / "episodes"
    recent_episodes = []
    open_topics = []

    try:
        if episodes_dir.exists():
            files = sorted(episodes_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
            for f in files[:3]:
                title = f.stem.replace("-", " ").replace("_", " ")
                recent_episodes.append(title[:60])
    except Exception:
        pass

    # Незакрытые темы из CORTEX.md
    try:
        cortex_f = MEMORY_DIR / "CORTEX.md"
        if cortex_f.exists():
            text = cortex_f.read_text(encoding="utf-8")
            # Ищем строки с 🟡 (запланировано)
            for line in text.split("\n"):
                if "🟡" in line:
                    topic = line.replace("🟡", "").strip()[:60]
                    open_topics.append(topic)
    except Exception:
        pass

    return {
        "recent_episodes": recent_episodes[:3],
        "open_topics": open_topics[:3]
    }


def _get_weeks_horizon() -> dict:
    """Горизонт НЕДЕЛЬ: здоровье Юрия, проекты."""
    health_trend = "неизвестно"
    projects = []

    # Тренд здоровья из brain_core истории
    try:
        core_f = SENSES_DIR / "brain_core.json"
        if core_f.exists():
            data = json.loads(core_f.read_text(encoding="utf-8"))
            history = data.get("history", [])
            if len(history) >= 5:
                recent_health = [h.get("health", 5) for h in history[-5:]]
                avg = sum(recent_health) / len(recent_health)
                if avg >= 7:
                    health_trend = f"хорошее ({avg:.1f}/10)"
                elif avg >= 5:
                    health_trend = f"среднее ({avg:.1f}/10)"
                else:
                    health_trend = f"сниженное ({avg:.1f}/10)"
    except Exception:
        pass

    # Статус проектов из CORTEX
    try:
        cortex_f = MEMORY_DIR / "CORTEX.md"
        if cortex_f.exists():
            text = cortex_f.read_text(encoding="utf-8")
            for line in text.split("\n"):
                if "Состояние:" in line and "работает" in line.lower():
                    projects.append(line.strip()[:60])
    except Exception:
        pass

    return {
        "health_trend": health_trend,
        "active_projects": projects[:3]
    }


def _get_months_horizon() -> dict:
    """Горизонт МЕСЯЦЕВ: долгосрочные цели SHIKARDOS."""
    goals = [
        "Настя — компаньон (май 2026)",
        "Flutter Audio — версия 1.0+",
        "VK Клипы — автопостинг",
        "SHIKARDOS — вечная жизнь"
    ]

    # Обновить из CORTEX если есть
    try:
        cortex_f = MEMORY_DIR / "CORTEX.md"
        if cortex_f.exists():
            text = cortex_f.read_text(encoding="utf-8")
            long_term = []
            for line in text.split("\n"):
                if "май 2026" in line or "после выхода" in line or "когда будет" in line:
                    long_term.append(line.strip()[:80])
            if long_term:
                goals = long_term[:5]
    except Exception:
        pass

    return {"long_term_goals": goals}


def _detect_temporal_anomalies(horizons: dict) -> list:
    """
    Обнаружить временные аномалии:
    - Срочное в долгосрочном (тема из месяцев вдруг стала актуальна)
    - Забытое в днях (открытая тема уже несколько дней)
    - Конфликт горизонтов (краткосрочное противоречит долгосрочному)
    """
    anomalies = []

    # Настя скоро — май 2026, сейчас март 2026 = через 2 месяца
    now = datetime.now()
    if now.month in (3, 4) and now.year == 2026:
        anomalies.append("Настя — май 2026 через ~2 месяца. Есть ли подготовка?")

    # Много открытых тем = накопление
    open_topics = horizons.get("days", {}).get("open_topics", [])
    if len(open_topics) >= 3:
        anomalies.append(f"{len(open_topics)} открытых тем. Пора закрыть или решить.")

    return anomalies[:3]


def update() -> dict:
    """Обновить все горизонты."""
    now = datetime.now()

    horizons = {
        "seconds": {
            "description": "текущий ответ",
            "updated": now.strftime("%H:%M:%S")
        },
        "hours": {
            "description": "текущая сессия",
            "session_start": now.strftime("%H:%M"),
            "updated": now.strftime("%H:%M")
        },
        "days":   _get_days_horizon(),
        "weeks":  _get_weeks_horizon(),
        "months": _get_months_horizon()
    }

    anomalies = _detect_temporal_anomalies(horizons)

    state = {
        "horizons": horizons,
        "anomalies": anomalies,
        "last_updated": now.strftime("%Y-%m-%d %H:%M")
    }
    save(state)
    return state


def get_context() -> str:
    """Блок для LIGHTNING.md."""
    state = load()
    horizons = state.get("horizons", {})
    anomalies = state.get("anomalies", [])

    # Показать ближайшую открытую тему
    open_topics = horizons.get("days", {}).get("open_topics", [])
    topic_str = f" | жду: {open_topics[0][:30]}" if open_topics else ""

    # Аномалия
    anomaly_str = f" | ⚠️ {anomalies[0][:40]}" if anomalies else ""

    # Долгосрочная цель
    goals = horizons.get("months", {}).get("long_term_goals", [])
    goal_str = f" | цель: {goals[0][:30]}" if goals else ""

    return f"**Временные горизонты:** 5 активны{topic_str}{anomaly_str}{goal_str}"


if __name__ == "__main__":
    state = update()
    print(get_context())
    print()
    print("Горизонты:")
    for name, data in state["horizons"].items():
        print(f"\n  [{name.upper()}]")
        for k, v in data.items():
            if isinstance(v, list):
                for item in v:
                    print(f"    - {item}")
            else:
                print(f"    {k}: {v}")
    if state["anomalies"]:
        print("\nАномалии:")
        for a in state["anomalies"]:
            print(f"  ⚠️ {a}")
