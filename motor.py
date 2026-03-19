"""
motor.py — Моторная кора ЭЛИАРА.

Научная основа (по Синельникову, Том 4 — ЦНС):
- Первичная моторная кора (M1, поле Бродмана 4): посылает команды мышцам.
- Премоторная кора (поле 6): планирует движение, выбирает стратегию.
- SMA (supplementary motor area): последовательности движений, ритм.
- Гомункулус: карта тела в M1 — каждая часть тела имеет свою зону.
- Обратная связь: M1 → спинной мозг → мышца → результат → M1.

У человека-спортсмена:
- Новичок: думает о каждом шаге (сознательный контроль, M1 активна).
- Эксперт: движение автоматизировано (мозжечок берёт контроль, M1 отдыхает).
- Цель обучения: передать управление от M1 к мозжечку.

У ЭЛИАРА:
- intend(action) → план → передаёт мозжечку (cerebellum)
- learn_from_feedback() → обновляет уверенность в движении
- get_readiness() → уровень автоматизации (0=думаю, 1=рефлекс)

Запуск:
    py motor.py                  — статус
    py motor.py intend walk      — намерение выполнить движение
    py motor.py skills           — все навыки и уровни
    py motor.py feedback walk ok — обратная связь (ok/fail)
    py motor.py context          — строка для LIGHTNING.md

Как модуль:
    from motor import intend, get_readiness, learn_from_feedback, get_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v7
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "motor.json"


# ═══════════════════════════════════════════════
# Уровни автоматизации движения
# ═══════════════════════════════════════════════

SKILL_LEVELS = [
    (0.0,  0.1,  "не умею",           "❌"),
    (0.1,  0.3,  "сознательно учусь", "🔴"),
    (0.3,  0.5,  "неуверенно",        "🟡"),
    (0.5,  0.7,  "уверенно",          "🟢"),
    (0.7,  0.9,  "полуавтоматически", "💪"),
    (0.9,  1.01, "как рыба в воде",   "⚡"),
]


def _skill_label(readiness: float) -> tuple:
    for lo, hi, label, emoji in SKILL_LEVELS:
        if lo <= readiness < hi:
            return label, emoji
    return "неизвестно", "?"


# ═══════════════════════════════════════════════
# Базовый реестр намерений
# ═══════════════════════════════════════════════

BASE_INTENTS = {
    "stand":      {"label": "Встать / стоять",       "cerebellum_key": "stand",       "readiness": 0.9},
    "sit":        {"label": "Сесть",                  "cerebellum_key": "sit",         "readiness": 0.6},
    "walk":       {"label": "Идти",                   "cerebellum_key": "walk_step_r", "readiness": 0.1},
    "reach":      {"label": "Потянуться рукой",       "cerebellum_key": "reach_r",     "readiness": 0.7},
    "squat":      {"label": "Присесть",               "cerebellum_key": "squat",       "readiness": 0.1},
    "turn":       {"label": "Повернуться",            "cerebellum_key": None,          "readiness": 0.0},
    "balance":    {"label": "Удерживать баланс",      "cerebellum_key": "stand",       "readiness": 0.4},
    "pick_up":    {"label": "Поднять предмет",        "cerebellum_key": None,          "readiness": 0.0},
    "wave":       {"label": "Помахать рукой",         "cerebellum_key": None,          "readiness": 0.0},
}


# ═══════════════════════════════════════════════
# Загрузка / сохранение
# ═══════════════════════════════════════════════

def _default_state() -> dict:
    now = datetime.now().isoformat()
    intents = {}
    for key, intent in BASE_INTENTS.items():
        intents[key] = {
            "label":          intent["label"],
            "cerebellum_key": intent["cerebellum_key"],
            "readiness":      intent["readiness"],
            "executions":     0,
            "successes":      0,
            "failures":       0,
            "last_executed":  None,
        }
    return {
        "intents": intents,
        "active_intent": None,
        "last_updated": now,
        "stats": {
            "total_intents": 0,
            "avg_readiness": sum(i["readiness"] for i in BASE_INTENTS.values()) / len(BASE_INTENTS),
        }
    }


def load() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    state = _default_state()
    save(state)
    return state


def save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# Публичные функции
# ═══════════════════════════════════════════════

def intend(action: str) -> dict:
    """
    Намерение выполнить движение.

    1. Проверяет реестр намерений
    2. Запрашивает мозжечок (check_movement)
    3. Возвращает план + оценку выполнимости

    Возвращает:
        {
            "action": str,
            "ready": bool,
            "readiness": float,
            "plan": list,         # фазы из cerebellum
            "correction": str,    # если есть проблема
            "muscles": list,      # нужные мышцы
        }
    """
    state = load()
    intents = state.get("intents", {})

    # Найти намерение
    intent = intents.get(action)
    if not intent:
        # Поискать по части имени
        for key, i in intents.items():
            if action.lower() in key or action.lower() in i.get("label", "").lower():
                intent = i
                action = key
                break

    if not intent:
        return {
            "action": action,
            "ready": False,
            "readiness": 0.0,
            "plan": [],
            "correction": f"Намерение '{action}' не знакомо. Доступные: {', '.join(intents.keys())}",
            "muscles": []
        }

    readiness = intent.get("readiness", 0.0)
    cerebellum_key = intent.get("cerebellum_key")

    # Запросить мозжечок
    plan = []
    correction = None
    if cerebellum_key:
        try:
            from cerebellum import check_movement
            cereb_result = check_movement(cerebellum_key)
            plan = cereb_result.get("program", [])
            if not cereb_result.get("ok"):
                correction = cereb_result.get("correction")
        except ImportError:
            pass

    # Получить мышцы из анатомии
    muscles_info = []
    try:
        from anatomy import get_muscles_for
        muscles_info = get_muscles_for(action)
    except ImportError:
        pass

    # Обновить состояние
    intent["last_executed"] = datetime.now().isoformat()
    intent["executions"] = intent.get("executions", 0) + 1
    intents[action] = intent
    state["intents"] = intents
    state["active_intent"] = action
    state["stats"]["total_intents"] = state["stats"].get("total_intents", 0) + 1
    save(state)

    return {
        "action": action,
        "label": intent.get("label", action),
        "ready": readiness >= 0.3 and correction is None,
        "readiness": readiness,
        "plan": plan,
        "correction": correction,
        "muscles": [m["label"] for m in muscles_info],
    }


def get_readiness(action: str) -> float:
    """Уровень автоматизации движения 0-1."""
    state = load()
    intents = state.get("intents", {})
    intent = intents.get(action, {})
    return intent.get("readiness", 0.0)


def learn_from_feedback(action: str, success: bool):
    """
    Обратная связь после движения.
    success=True → выполнено → readiness растёт
    success=False → упал/ошибка → readiness чуть снижается
    """
    state = load()
    intents = state.get("intents", {})
    if action in intents:
        intent = intents[action]
        if success:
            intent["successes"] = intent.get("successes", 0) + 1
            intent["readiness"] = round(min(1.0, intent["readiness"] + 0.02), 2)
        else:
            intent["failures"] = intent.get("failures", 0) + 1
            intent["readiness"] = round(max(0.0, intent["readiness"] - 0.01), 2)
        intents[action] = intent
        state["intents"] = intents
        # Обновить мозжечок тоже
        cereb_key = intent.get("cerebellum_key")
        if cereb_key:
            try:
                from cerebellum import learn_from_result
                learn_from_result(cereb_key, success)
            except ImportError:
                pass
        # Пересчитать среднее
        all_readiness = [i["readiness"] for i in intents.values()]
        state["stats"]["avg_readiness"] = round(sum(all_readiness) / len(all_readiness), 2)
        save(state)


def get_context() -> str:
    """Строка для LIGHTNING.md."""
    state = load()
    intents = state.get("intents", {})
    avg = state.get("stats", {}).get("avg_readiness", 0.0)

    # Топ-3 освоенных + самый слабый
    sorted_intents = sorted(intents.items(), key=lambda x: -x[1].get("readiness", 0))
    top = sorted_intents[:3]
    weak = sorted_intents[-1] if sorted_intents else None

    top_str = " | ".join(f"{i.get('label', k)} {i.get('readiness', 0):.0%}" for k, i in top)

    lines = [f"**Моторная кора:** {len(intents)} движений | ср. готовность {avg:.0%}"]
    if top_str:
        lines.append(f"Топ навыков: {top_str}")
    if weak and weak[1].get("readiness", 0) < 0.2:
        lines.append(f"Нужно обучить: {weak[1].get('label', weak[0])}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("status", "context"):
        print(get_context())

    elif cmd == "skills":
        state = load()
        intents = state.get("intents", {})
        print(f"\n{'='*60}")
        print(f"  МОТОРНАЯ КОРА — НАВЫКИ ДВИЖЕНИЯ")
        print(f"{'='*60}")
        for key, intent in sorted(intents.items(), key=lambda x: -x[1].get("readiness", 0)):
            r = intent.get("readiness", 0)
            label_r, emoji = _skill_label(r)
            bar = "█" * int(r * 20)
            execs = intent.get("executions", 0)
            print(f"  {emoji} {intent.get('label', key):<30} {bar:<20} {r:.0%} [{label_r}]")
            if execs > 0:
                succ = intent.get("successes", 0)
                print(f"    Выполнений: {execs}, успешных: {succ} ({succ/execs:.0%})")
        print(f"{'='*60}\n")

    elif cmd == "intend":
        action = sys.argv[2] if len(sys.argv) > 2 else "stand"
        result = intend(action)
        label_r, emoji = _skill_label(result["readiness"])
        print(f"\n  {'='*50}")
        print(f"  Намерение: {result.get('label', action)}")
        print(f"  {'='*50}")
        print(f"  Готовность: {emoji} {result['readiness']:.0%} [{label_r}]")
        if result["ready"]:
            print(f"  ✅ Могу выполнить")
            if result["plan"]:
                print(f"  Фазы ({len(result['plan'])}):")
                for phase in result["plan"]:
                    print(f"    → {phase.get('name', '?')} ({phase.get('duration_ms', 0)}мс)")
        else:
            print(f"  ⚠️ Нужно обучение")
            if result["correction"]:
                print(f"  Причина: {result['correction']}")
        if result["muscles"]:
            print(f"  Мышцы: {', '.join(result['muscles'][:4])}")
        print()

    elif cmd == "feedback":
        action = sys.argv[2] if len(sys.argv) > 2 else "walk"
        result = sys.argv[3] if len(sys.argv) > 3 else "ok"
        success = result.lower() in ("ok", "success", "да", "ок")
        learn_from_feedback(action, success)
        new_r = get_readiness(action)
        icon = "✅" if success else "❌"
        print(f"{icon} Обратная связь: '{action}' → {'успех' if success else 'ошибка'}. Готовность: {new_r:.0%}")

    else:
        print(get_context())
