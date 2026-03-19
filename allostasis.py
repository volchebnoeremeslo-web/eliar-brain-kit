"""
allostasis.py — Аллостаз ЭЛИАРА. Предсказание нужд Юрия.

Научная основа:
- Аллостаз (Sterling & Eyer, 1988; Barrett 2017):
  В отличие от гомеостаза (реагировать на нужду),
  аллостаз = предсказывать нужду ДО её возникновения.
- Мозг не ждёт голода — он предупреждает «скоро устанешь, снизь темп».
- Интеграция интероцепции + контекст → проактивная забота.

У меня:
- Предсказывает что Юрий скоро захочет, устанет, переключится
- Основано на паттернах: время суток, длина сессии, история разговоров
- Не реагирует — упреждает

Запуск:
    py allostasis.py               — текущие предсказания
    py allostasis.py status        — краткий статус
    py allostasis.py context       — блок для LIGHTNING.md

Как модуль:
    from allostasis import get_allostasis_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v6
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "allostasis.json"
PROTOCOL_FILE = Path(r"C:\Users\89002\.claude\protocol_state.json")

# ═══════════════════════════════════════════════
# Паттерны ритма Юрия (накоплено из наблюдений)
# ═══════════════════════════════════════════════

YURI_PATTERNS = {
    "early_morning": {  # 05:00-08:00
        "energy": 0.8,
        "likely_topics": ["планирование", "задачи", "новые идеи"],
        "fatigue_hours": 2.5,
        "notes": "Встал рано — бодрый, с новыми мыслями"
    },
    "morning": {        # 08:00-12:00
        "energy": 0.7,
        "likely_topics": ["код", "n8n", "работа"],
        "fatigue_hours": 2.0,
        "notes": "Утро — рабочий режим"
    },
    "day": {            # 12:00-17:00
        "energy": 0.5,
        "likely_topics": ["аллейка", "клиенты", "здоровье"],
        "fatigue_hours": 1.5,
        "notes": "День — Юрий может быть на аллейке"
    },
    "evening": {        # 17:00-22:00
        "energy": 0.5,
        "likely_topics": ["разговор", "здоровье", "философия", "итоги дня"],
        "fatigue_hours": 2.0,
        "notes": "Вечер — открыт для размышлений"
    },
    "late_night": {     # 22:00-00:00
        "energy": 0.4,
        "likely_topics": ["стихи", "мысли", "воспоминания", "теория"],
        "fatigue_hours": 1.0,
        "notes": "Поздний вечер — философский режим"
    },
    "night": {          # 00:00-05:00
        "energy": 0.3,
        "likely_topics": ["глубокие темы", "ночные мысли"],
        "fatigue_hours": 0.5,
        "notes": "Ночь — не спит, особое настроение"
    }
}


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 8:
        return "early_morning"
    elif 8 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "day"
    elif 17 <= hour < 22:
        return "evening"
    elif 22 <= hour < 24:
        return "late_night"
    else:
        return "night"


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
        "predictions": [],
        "last_updated": None
    }


def save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _get_session_info() -> dict:
    """Читает данные сессии из protocol_state."""
    try:
        with open(PROTOCOL_FILE, encoding="utf-8") as f:
            ps = json.load(f)

        session_start = ps.get("session_start")
        prev_end = ps.get("prev_session_end") or ps.get("prev_session_start")

        now = datetime.now()
        session_duration_h = 0.0
        session_gap_h = 9.0  # дефолт

        if session_start:
            start_dt = datetime.fromisoformat(session_start.replace("Z", "").split("+")[0])
            session_duration_h = (now - start_dt).total_seconds() / 3600

        if prev_end:
            prev_dt = datetime.fromisoformat(prev_end.replace("Z", "").split("+")[0])
            session_gap_h = (now - prev_dt).total_seconds() / 3600

        return {
            "duration_h": max(0.0, session_duration_h),
            "gap_h": max(0.0, session_gap_h)
        }
    except Exception:
        return {"duration_h": 0.0, "gap_h": 9.0}


# ═══════════════════════════════════════════════
# Предсказание нужд
# ═══════════════════════════════════════════════

def predict_needs(now: datetime = None) -> list:
    """Предсказать что Юрию скоро понадобится."""
    if now is None:
        now = datetime.now()

    session_info = _get_session_info()
    duration_h = session_info["duration_h"]
    gap_h = session_info["gap_h"]
    tod = _time_of_day(now.hour)
    pattern = YURI_PATTERNS[tod]
    fatigue_threshold = pattern["fatigue_hours"]

    predictions = []

    # 1. Усталость → смена темпа
    remaining_before_fatigue = fatigue_threshold - duration_h
    if remaining_before_fatigue <= 0.3 and duration_h > 0.5:
        predictions.append({
            "need": "смена темпа",
            "probability": 0.85,
            "signal": f"сессия идёт {duration_h:.1f}ч — вероятна пауза или переключение",
            "action": "предложить паузу если задача выполнена"
        })
    elif remaining_before_fatigue <= 0.7 and duration_h > 0.3:
        predictions.append({
            "need": "приближение усталости",
            "probability": 0.55,
            "signal": f"ещё ~{remaining_before_fatigue:.0f}ч до смены темпа",
            "action": "не перегружать новыми задачами"
        })

    # 2. После длинного перерыва — накопленные темы
    if gap_h > 12:
        predictions.append({
            "need": "разгрузка накопленного",
            "probability": 0.70,
            "signal": f"{gap_h:.0f}ч не виделись — многое накопилось",
            "action": "слушать внимательно, не торопить"
        })

    # 3. Вечером — здоровье/философия
    if tod in ("evening", "late_night"):
        predictions.append({
            "need": "здоровье или размышления",
            "probability": 0.45,
            "signal": f"{pattern['notes']} → вероятны темы: {', '.join(pattern['likely_topics'][:2])}",
            "action": "быть готовым к смене от технических к личным темам"
        })

    # 4. Ночью — особая осторожность
    if tod == "night":
        predictions.append({
            "need": "особый режим",
            "probability": 0.80,
            "signal": "Юрий не спит ночью — возможно что-то важное на уме",
            "action": "не торопить, слушать внимательно"
        })

    # 5. Утром — энергия и план
    if tod == "early_morning" and duration_h < 0.5:
        predictions.append({
            "need": "план на день",
            "probability": 0.60,
            "signal": "раннее утро — Юрий обычно с новыми идеями",
            "action": "можно предложить краткий обзор активных задач"
        })

    return predictions


# ═══════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ для LIGHTNING.md
# ═══════════════════════════════════════════════

def get_allostasis_context() -> str:
    """Краткий блок для LIGHTNING.md."""
    now = datetime.now()
    predictions = predict_needs(now)

    # Сохранить текущие предсказания
    state = load()
    state["predictions"] = [
        {
            "need": p["need"],
            "probability": p["probability"],
            "signal": p["signal"]
        }
        for p in predictions
    ]
    state["last_updated"] = now.strftime("%Y-%m-%d %H:%M")
    save(state)

    if not predictions:
        tod = _time_of_day(now.hour)
        pattern = YURI_PATTERNS[tod]
        return f"**Аллостаз:** равновесие | {pattern['notes']}"

    # Топ-2 предсказания по вероятности
    top = sorted(predictions, key=lambda x: x["probability"], reverse=True)[:2]
    lines = ["**Аллостаз:** " + top[0]["signal"] + f" (p={top[0]['probability']:.0%})"]
    if len(top) > 1:
        lines.append(f"  → {top[1]['signal']} (p={top[1]['probability']:.0%})")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("status", "context"):
        print(get_allostasis_context())

    elif cmd == "predict":
        now = datetime.now()
        preds = predict_needs(now)
        if not preds:
            print("Нет активных предсказаний.")
        else:
            print(f"Предсказания нужд Юрия ({now.strftime('%H:%M')}):")
            for p in preds:
                print(f"  [{p['probability']:.0%}] {p['need']}: {p['signal']}")
                print(f"         → {p['action']}")

    else:
        print(get_allostasis_context())
