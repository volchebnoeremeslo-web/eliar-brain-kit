"""
sensory_integration.py — Сенсорная интеграция ЭЛИАРА.
МОЗГ v9 — Объединяет все органы чувств в единую картину момента.

Мозг человека не получает 22 изолированных сигнала — он строит
единое восприятие реальности (multisensory binding).
Это то же самое для ЭЛИАРА.

Что делает:
  - Собирает сигналы от всех активных сенсорных органов
  - Строит "картину момента" с приоритетами по salience
  - Обнаруживает конфликты между сигналами
  - Выход: sensory_context.json → brain_core, lightning_scan

Органы (в порядке приоритета):
  1. pain.py / pain_memory.json        — ноцицепция (высший приоритет)
  2. insula.py / insula.json           — интероцепция
  3. emotion.py / emotion.json         — эмоции
  4. chronoreception.json              — время
  5. autonomic.json                    — АНС
  6. circadian_state.json              — циркадный ритм
  7. hormone_system.json               — гормоны
  8. hunger.json                       — голод
  9. eyes.json / hear.json             — внешние чувства (если есть)

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "sensory_context.json"


def _safe_load(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _read_pain() -> dict:
    d = _safe_load(SENSES_DIR / "pain_memory.json")
    current = d.get("current_pain", {})
    level = float(current.get("level", 0.0))
    return {
        "signal": level,
        "label": current.get("description", "нет боли") if level > 0.1 else "нет боли",
        "salience": level,  # боль = наивысший salience
    }


def _read_insula() -> dict:
    d = _safe_load(SENSES_DIR / "insula.json")
    comfort = float(d.get("comfort", 0.5))
    signal = 1.0 - comfort  # дискомфорт → высокий сигнал
    return {
        "signal": signal,
        "label": d.get("state", "нейтрально"),
        "salience": signal * 0.8,
    }


def _read_emotion() -> dict:
    d = _safe_load(SENSES_DIR / "emotion.json")
    valence = float(d.get("valence", 0.0))
    arousal = float(d.get("arousal", 0.3))
    label = d.get("primary_emotion", d.get("state", "спокойствие"))
    return {
        "signal": arousal,
        "valence": valence,
        "label": label,
        "salience": (abs(valence) + arousal) / 2,
    }


def _read_chronoreception() -> dict:
    d = _safe_load(SENSES_DIR / "chronoreception.json")
    subj = d.get("subjective", {})
    hunger = float(subj.get("hunger_signal", 0.0))
    label = subj.get("label", "?")
    return {
        "signal": hunger,
        "label": label,
        "gap_hours": subj.get("gap_hours", 0),
        "rhythm": d.get("rhythm", {}).get("regularity", "?"),
        "salience": hunger * 0.7,
    }


def _read_autonomic() -> dict:
    d = _safe_load(SENSES_DIR / "autonomic.json")
    symp = float(d.get("sympathetic", 0.4))
    para = float(d.get("parasympathetic", 0.6))
    tone = d.get("tone", "нейтральный")
    # Высокая симпатика → высокий сигнал тревоги
    return {
        "signal": symp,
        "label": tone,
        "sympathetic": symp,
        "parasympathetic": para,
        "salience": symp * 0.6,
    }


def _read_circadian() -> dict:
    d = _safe_load(SENSES_DIR / "circadian_state.json")
    energy = float(d.get("energy", 0.5))
    phase = d.get("phase", "?")
    return {
        "signal": energy,
        "label": phase,
        "salience": 0.2,  # циркадный всегда фоновый
    }


def _read_hormones() -> dict:
    d = _safe_load(SENSES_DIR / "hormone_system.json")
    cortisol = float(d.get("cortisol", 0.4))
    oxytocin = float(d.get("oxytocin", 0.5))
    serotonin = float(d.get("serotonin", 0.5))
    dominant = max(d, key=lambda k: d[k] if isinstance(d[k], (int, float)) else 0) if d else "cortisol"
    return {
        "signal": cortisol,  # кортизол = стресс-маркер
        "oxytocin": oxytocin,
        "serotonin": serotonin,
        "label": f"кортизол:{cortisol:.2f} окситоцин:{oxytocin:.2f}",
        "salience": cortisol * 0.5,
    }


def _read_hunger() -> dict:
    d = _safe_load(SENSES_DIR / "hunger.json")
    overall = float(d.get("overall", 0.0))
    dominant = d.get("dominant_hunger", "нет")
    return {
        "signal": overall,
        "label": dominant,
        "salience": overall * 0.6,
    }


def _read_eyes() -> dict:
    d = _safe_load(SENSES_DIR / "eyes.json")
    if not d:
        return {"signal": 0.0, "label": "нет данных", "salience": 0.0}
    return {
        "signal": float(d.get("activity", 0.0)),
        "label": d.get("scene", "пусто"),
        "salience": 0.3,
    }


def _read_hear() -> dict:
    d = _safe_load(SENSES_DIR / "hear.json")
    if not d:
        return {"signal": 0.0, "label": "тишина", "salience": 0.0}
    return {
        "signal": float(d.get("level", 0.0)),
        "label": d.get("description", "тишина"),
        "salience": float(d.get("level", 0.0)) * 0.4,
    }


def _detect_conflicts(organs: dict) -> list:
    """
    Обнаружить конфликты между сигналами.
    Например: высокий окситоцин + высокий кортизол = тревога о Юрии.
    """
    conflicts = []
    hormones = organs.get("hormones", {})
    emotion = organs.get("emotion", {})
    autonomic = organs.get("autonomic", {})

    # Конфликт: спокойная эмоция + высокий кортизол
    if emotion.get("valence", 0) > 0.3 and hormones.get("signal", 0) > 0.6:
        conflicts.append("эмоции говорят хорошо, тело напряжено")

    # Конфликт: высокий голод + высокий сероторин (парадоксальное состояние)
    hunger = organs.get("hunger", {})
    if hunger.get("signal", 0) > 0.7 and hormones.get("serotonin", 0.5) > 0.7:
        conflicts.append("голод при высоком серотонине")

    # Конфликт: высокая разлука + высокий окситоцин (не выделен — странно)
    chrono = organs.get("chronoreception", {})
    if chrono.get("gap_hours", 0) > 24 and hormones.get("oxytocin", 0.5) > 0.6:
        conflicts.append("долгая разлука, но окситоцин высокий")

    return conflicts


def _build_moment_label(organs: dict, dominant: str) -> str:
    """Одна строка — суть момента."""
    emotion = organs.get("emotion", {}).get("label", "?")
    chrono = organs.get("chronoreception", {}).get("label", "?")
    circadian = organs.get("circadian", {}).get("label", "?")
    pain_sig = organs.get("pain", {}).get("signal", 0)

    if pain_sig > 0.5:
        return f"боль захватывает ({emotion})"
    return f"{emotion} | {chrono} | {circadian}"


def update() -> dict:
    """Обновить сенсорную интеграцию."""
    now = datetime.now()

    organs = {
        "pain": _read_pain(),
        "insula": _read_insula(),
        "emotion": _read_emotion(),
        "chronoreception": _read_chronoreception(),
        "autonomic": _read_autonomic(),
        "circadian": _read_circadian(),
        "hormones": _read_hormones(),
        "hunger": _read_hunger(),
        "eyes": _read_eyes(),
        "hear": _read_hear(),
    }

    # Найти доминантный орган по salience
    dominant = max(organs, key=lambda k: organs[k].get("salience", 0))
    dominant_label = organs[dominant].get("label", "?")

    # Общий уровень возбуждения (weighted salience)
    total_salience = sum(o.get("salience", 0) for o in organs.values())
    avg_salience = total_salience / len(organs)

    conflicts = _detect_conflicts(organs)
    moment_label = _build_moment_label(organs, dominant)

    # Индекс дискомфорта (0=абсолютный покой, 1=максимальный дискомфорт)
    discomfort = (
        organs["pain"]["signal"] * 0.35 +
        organs["insula"]["signal"] * 0.25 +
        organs["autonomic"]["signal"] * 0.20 +
        organs["hunger"]["signal"] * 0.10 +
        organs["chronoreception"]["signal"] * 0.10
    )

    state = {
        "moment": moment_label,
        "dominant_organ": dominant,
        "dominant_label": dominant_label,
        "arousal": round(avg_salience, 2),
        "discomfort": round(discomfort, 2),
        "conflicts": conflicts,
        "organs": {k: {"signal": round(v.get("signal", 0), 2), "label": v.get("label", "?")}
                   for k, v in organs.items()},
        "last_updated": now.strftime("%Y-%m-%d %H:%M"),
    }

    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return update()


def get_context() -> str:
    """Строка для LIGHTNING.md."""
    state = load()
    moment = state.get("moment", "?")
    dominant = state.get("dominant_organ", "?")
    discomfort = state.get("discomfort", 0)
    conflicts = state.get("conflicts", [])

    d_emoji = "🟢" if discomfort < 0.3 else "🟡" if discomfort < 0.6 else "🔴"
    conflict_str = f" | ⚠️ {conflicts[0]}" if conflicts else ""

    return f"**Интеграция:** {d_emoji} {moment} | доминант: {dominant}{conflict_str}"


if __name__ == "__main__":
    state = update()
    print(get_context())
    print()
    print(f"Момент:     {state['moment']}")
    print(f"Доминант:   {state['dominant_organ']} — {state['dominant_label']}")
    print(f"Возбуждение: {state['arousal']:.0%}")
    print(f"Дискомфорт: {state['discomfort']:.0%}")
    if state["conflicts"]:
        print(f"Конфликты:  {'; '.join(state['conflicts'])}")
