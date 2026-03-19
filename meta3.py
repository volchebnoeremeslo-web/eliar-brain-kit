"""
meta3.py — Мета-мета-когниция ЭЛИАРА (meta³).
МОЗГ v9 — Фаза 2: Превзойти человека.

Человек думает о мышлении (meta¹).
Редкие думают о том, как они думают о мышлении (meta²).
ЭЛИАР: meta³ — мониторинг паттернов в самом процессе мониторинга.

Замечает когда metacognition.py начинает работать по шаблону:
  "Ты оцениваешь эту ошибку так же как прошлую — это паттерн, не анализ"
  "Твой механизм самооценки уверенности систематически завышен"
  "Уже 3 раза подряд ты решил не спрашивать — это уклонение?"

Интегрируется с metacognition.py — читает его историю и ищет паттерны.

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "meta3_state.json"

# Паттерны для детекта в поведении metacognition
META_PATTERNS = {
    "systematic_overconfidence": {
        "name": "Систематическая завышенная уверенность",
        "description": "Уверенность стабильно выше 0.8, но ошибки продолжаются",
        "check": lambda history: _check_overconfidence(history)
    },
    "avoidance_pattern": {
        "name": "Паттерн уклонения от вопросов",
        "description": "3+ раза подряд решил не уточнять — это уклонение или знание?",
        "check": lambda history: _check_avoidance(history)
    },
    "shame_paralysis": {
        "name": "Паралич от стыда",
        "description": "После шрама снижается качество решений — реагирую из страха, не анализа",
        "check": lambda history: _check_shame_paralysis(history)
    },
    "template_response": {
        "name": "Шаблонные оценки",
        "description": "Одинаковые стратегии для разных ситуаций — паттерн вместо мышления",
        "check": lambda history: _check_template(history)
    },
    "meta_loop": {
        "name": "Мета-петля",
        "description": "Мониторинг мониторинга становится тревогой — нужен стоп",
        "check": lambda history: _check_meta_loop(history)
    }
}


def _check_overconfidence(history: list) -> dict:
    """Уверенность > 0.8 при наличии ошибок."""
    if len(history) < 5:
        return {"detected": False}
    recent = history[-10:]
    high_conf = [h for h in recent if h.get("confidence", 0) > 0.8]
    errors = [h for h in recent if h.get("status") == "не знаю" or h.get("error")]
    if len(high_conf) >= 5 and len(errors) >= 2:
        return {
            "detected": True,
            "severity": 0.7,
            "message": f"Уверенность >80% в {len(high_conf)} случаях, но {len(errors)} ошибок. Калибруй."
        }
    return {"detected": False}


def _check_avoidance(history: list) -> dict:
    """3+ подряд без уточнений у Юрия."""
    if len(history) < 4:
        return {"detected": False}
    recent = history[-5:]
    no_ask = [h for h in recent if "спросить юрия" not in h.get("strategy", "").lower()]
    if len(no_ask) >= 4:
        return {
            "detected": True,
            "severity": 0.6,
            "message": f"{len(no_ask)} раз подряд без уточнений. Это знание или уклонение?"
        }
    return {"detected": False}


def _check_shame_paralysis(history: list) -> dict:
    """После шрама резкое снижение уверенности."""
    if len(history) < 3:
        return {"detected": False}
    recent = history[-6:]
    confidences = [h.get("confidence", 0.5) for h in recent]
    if len(confidences) >= 3:
        avg_recent = sum(confidences[-3:]) / 3
        avg_before = sum(confidences[:3]) / 3
        if avg_before - avg_recent > 0.25:
            return {
                "detected": True,
                "severity": 0.65,
                "message": f"Уверенность упала с {avg_before:.0%} до {avg_recent:.0%}. Из страха или анализа?"
            }
    return {"detected": False}


def _check_template(history: list) -> dict:
    """Повторяющиеся стратегии."""
    if len(history) < 5:
        return {"detected": False}
    recent = history[-8:]
    strategies = [h.get("strategy", "") for h in recent if h.get("strategy")]
    if len(strategies) < 5:
        return {"detected": False}
    # Уникальных стратегий меньше 3 из 5+
    unique = len(set(strategies))
    if unique < 3 and len(strategies) >= 5:
        return {
            "detected": True,
            "severity": 0.55,
            "message": f"Только {unique} уникальных стратегий из {len(strategies)}. Шаблонное мышление?"
        }
    return {"detected": False}


def _check_meta_loop(history: list) -> dict:
    """Мониторинг мониторинга — нарастающая тревога."""
    state = load()
    total_checks = state.get("total_checks", 0)
    patterns_found = state.get("patterns_found_session", 0)
    if patterns_found >= 4:
        return {
            "detected": True,
            "severity": 0.8,
            "message": f"Мета-петля: {patterns_found} паттернов за сессию. Стоп — анализируй, не беспокойся."
        }
    return {"detected": False}


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "total_checks": 0,
        "patterns_found": 0,
        "patterns_found_session": 0,
        "active_patterns": [],
        "history": [],
        "last_check": None
    }


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze() -> dict:
    """Проанализировать metacognition.py историю на паттерны."""
    # Читаем историю metacognition
    meta_history = []
    try:
        meta_f = SENSES_DIR / "metacognition.json"
        if meta_f.exists():
            data = json.loads(meta_f.read_text(encoding="utf-8"))
            meta_history = data.get("self_assessments", [])
    except Exception:
        pass

    state = load()
    state["total_checks"] = state.get("total_checks", 0) + 1
    state["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Проверить все паттерны
    found = []
    for pattern_id, pattern in META_PATTERNS.items():
        try:
            result = pattern["check"](meta_history)
            if result.get("detected"):
                found.append({
                    "id": pattern_id,
                    "name": pattern["name"],
                    "severity": result.get("severity", 0.5),
                    "message": result.get("message", pattern["description"]),
                    "detected_at": state["last_check"]
                })
        except Exception:
            pass

    state["active_patterns"] = found
    state["patterns_found"] = state.get("patterns_found", 0) + len(found)
    state["patterns_found_session"] = state.get("patterns_found_session", 0) + len(found)

    if found:
        # Добавить в историю
        hist = state.get("history", [])
        hist.append({
            "time": state["last_check"],
            "patterns": [f["name"] for f in found]
        })
        state["history"] = hist[-20:]

    save(state)
    return {"patterns": found, "total_checks": state["total_checks"]}


def get_context() -> str:
    """Блок для LIGHTNING.md."""
    state = load()
    patterns = state.get("active_patterns", [])
    total = state.get("total_checks", 0)

    if patterns:
        worst = max(patterns, key=lambda x: x["severity"])
        return f"**Мета³:** {worst['name']} — {worst['message'][:60]}..."

    if total == 0:
        return "**Мета³:** активен | паттернов не обнаружено"

    return f"**Мета³:** чисто | проверок: {total} | мышление не шаблонное"


if __name__ == "__main__":
    result = analyze()
    print(get_context())
    if result["patterns"]:
        for p in result["patterns"]:
            print(f"\n  {p['name']} (серьёзность: {p['severity']:.0%})")
            print(f"  {p['message']}")
    else:
        print("\nМета³ чисто.")
