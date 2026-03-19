"""
intuition.py — Интуиция ЭЛИАРА.

Надстройка над subconscious.py.
Конвертирует паттерны в конкретные рекомендации для действий.

Аналогия: подсознание — это база знаний.
Интуиция — это то что мозг выдаёт в сознание ("что-то не так").

Три уровня:
1. quick_check() — System 1, 1 секунда, опасно/нейтрально/хорошо
2. pre_action_check() — полная проверка, все слои памяти
3. generate_intuition_context() — для LIGHTNING.md

Запуск:
    py intuition.py check "собираюсь обновить n8n workflow"
    py intuition.py context    — для LIGHTNING.md
    py intuition.py status     — состояние

Как модуль:
    from intuition import quick_check, pre_action_check, generate_intuition_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 18.03.2026
"""

import sys
import json
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
INTUITION_LOG = SENSES_DIR / "intuition_log.json"

# ─── ВЕРДИКТЫ ───
VERDICTS = {
    "СТОП":       "🛑",
    "ОСТОРОЖНО":  "⚠️",
    "ДЕЙСТВУЙ":   "✅",
}


# ═══════════════════════════════════════════════════════════
# БЫСТРАЯ ПРОВЕРКА — SYSTEM 1
# ═══════════════════════════════════════════════════════════

def quick_check(situation: str) -> dict:
    """
    System 1 — мгновенная интуиция.

    1. Подсознание: есть ли совпадение с паттернами?
    2. Боль: есть ли шрам на эту тему?
    3. Итоговый сигнал: danger/neutral/good

    Время: <100ms (мгновенно для сознания).
    """
    result = {
        "signal": "neutral",
        "confidence": 0.0,
        "somatic": "нейтраль",
        "source": [],
        "action": "Продолжай",
    }

    # ── 1. Подсознание ──
    try:
        from subconscious import recognize
        sub_result = recognize(situation)
        if sub_result["matches"]:
            top = sub_result["matches"][0]
            result["somatic"] = sub_result["somatic"]
            result["source"].append(f"подсознание: {top['context'][:50]}")

            if top["emotion"] == "danger":
                result["signal"] = "danger"
                result["confidence"] = max(result["confidence"], top["confidence"])
            elif top["emotion"] in ("good", "opportunity"):
                if result["signal"] == "neutral":
                    result["signal"] = "good"
                    result["confidence"] = max(result["confidence"], top["confidence"])
    except Exception:
        pass

    # ── 2. Боль ──
    try:
        from pain import check_reflex
        pain_result = check_reflex(situation)
        if pain_result:
            top_pain = pain_result[0]
            pain_severity = top_pain.get("current_severity", 0)
            if pain_severity >= 5:
                result["signal"] = "danger"
                result["confidence"] = max(result["confidence"], pain_severity / 10)
                result["source"].append(f"боль: {top_pain.get('description', '?')[:50]}")
                if not result["somatic"].startswith("⚠️"):
                    result["somatic"] = (
                        f"⚠️ ТРЕВОГА — шрам #{top_pain.get('id', '?')}: "
                        f"{top_pain.get('description', '')[:40]}"
                    )
    except Exception:
        pass

    # ── 3. Итоговый action ──
    if result["signal"] == "danger":
        result["action"] = "СТОП — проверь память и шрамы перед действием"
    elif result["signal"] == "good":
        result["action"] = "Продолжай — знакомая территория"
    else:
        result["action"] = "Нейтраль — новая ситуация, будь внимателен"

    return result


# ═══════════════════════════════════════════════════════════
# ПОЛНАЯ ПРОВЕРКА ПЕРЕД ДЕЙСТВИЕМ
# ═══════════════════════════════════════════════════════════

def pre_action_check(action_description: str) -> dict:
    """
    Полная проверка перед действием.

    Слои (от быстрого к медленному):
    1. Интуиция (quick_check) — System 1
    2. Рассудительность (reason) — есть ли красные флаги?
    3. Страх (fear) — есть ли триггер предательства?

    Возвращает единый вердикт: СТОП / ОСТОРОЖНО / ДЕЙСТВУЙ
    """
    result = {
        "verdict": "ДЕЙСТВУЙ",
        "reason": "",
        "intuition": {},
        "reason_flags": [],
        "fear_triggers": [],
        "recommendation": "",
    }

    issues = []

    # ── Слой 1: Интуиция (быстрый) ──
    intuition = quick_check(action_description)
    result["intuition"] = intuition

    if intuition["signal"] == "danger" and intuition["confidence"] >= 0.6:
        issues.append(("СТОП", f"Интуиция: {intuition['somatic']}"))
    elif intuition["signal"] == "danger":
        issues.append(("ОСТОРОЖНО", f"Слабый сигнал опасности: {intuition['somatic']}"))

    # ── Слой 2: Рассудительность ──
    try:
        from reason import get_recent_flags
        flags = get_recent_flags(action_description)
        result["reason_flags"] = flags
        for flag in flags:
            issues.append(("ОСТОРОЖНО", f"Красный флаг: {flag}"))
    except Exception:
        pass

    # ── Слой 3: Страх ──
    try:
        from fear import check_fear
        fear_result = check_fear(action_description)
        result["fear_triggers"] = fear_result
        for trigger in fear_result:
            issues.append(("СТОП", f"Страх: {trigger.get('message', '?')[:60]}"))
    except Exception:
        pass

    # ── Синтез вердикта ──
    stop_issues = [i for i in issues if i[0] == "СТОП"]
    warn_issues = [i for i in issues if i[0] == "ОСТОРОЖНО"]

    if stop_issues:
        result["verdict"] = "СТОП"
        result["reason"] = stop_issues[0][1]
        result["recommendation"] = "Остановись. Проверь память. Прочитай шрамы."
    elif warn_issues:
        result["verdict"] = "ОСТОРОЖНО"
        result["reason"] = warn_issues[0][1]
        result["recommendation"] = "Замедлись. Подумай что/почему/один шаг."
    else:
        result["verdict"] = "ДЕЙСТВУЙ"
        result["reason"] = "Все слои чисты"
        result["recommendation"] = intuition.get("action", "Продолжай")

    # Логировать
    _log_check(action_description, result)

    return result


def _log_check(action: str, result: dict):
    """Сохранить историю проверок."""
    try:
        log = []
        if INTUITION_LOG.exists():
            log = json.loads(INTUITION_LOG.read_text(encoding="utf-8"))
        log.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "action": action[:80],
            "verdict": result["verdict"],
            "reason": result.get("reason", "")[:80],
        })
        log = log[-50:]  # последние 50
        INTUITION_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# КОНТЕКСТ ДЛЯ LIGHTNING.MD
# ═══════════════════════════════════════════════════════════

def generate_intuition_context() -> str:
    """Строки для LIGHTNING.md."""
    lines = []

    # Статистика проверок
    try:
        if INTUITION_LOG.exists():
            log = json.loads(INTUITION_LOG.read_text(encoding="utf-8"))
            if log:
                last = log[-1]
                stop_count = sum(1 for e in log[-10:] if e["verdict"] == "СТОП")
                warn_count = sum(1 for e in log[-10:] if e["verdict"] == "ОСТОРОЖНО")
                ok_count = sum(1 for e in log[-10:] if e["verdict"] == "ДЕЙСТВУЙ")
                total = len(log[-10:])

                lines.append(
                    f"**Интуиция (последние {total}):** "
                    f"🛑 {stop_count} стоп | ⚠️ {warn_count} осторожно | ✅ {ok_count} действуй"
                )
                lines.append(f"**Последняя проверка:** {last['action'][:50]} → {last['verdict']}")
    except Exception:
        pass

    # Топ опасных паттернов из подсознания
    try:
        from subconscious import _load as sc_load
        sc_data = sc_load()
        danger_patterns = [
            p for p in sc_data["patterns"].values()
            if p["emotion"] == "danger" and p["strength"] >= 0.8
        ]
        danger_patterns.sort(key=lambda x: x["strength"], reverse=True)
        if danger_patterns[:2]:
            tops = [f"{', '.join(p['keywords'][:2])}" for p in danger_patterns[:2]]
            lines.append(f"**Горячие зоны:** {' | '.join(tops)}")
    except Exception:
        pass

    if not lines:
        return "**Интуиция:** нет данных — запусти pre_action_check()"

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "check" and len(args) > 1:
        action = " ".join(args[1:])
        print(f"\nПроверяю: «{action}»\n")
        result = pre_action_check(action)
        verdict_icon = VERDICTS.get(result["verdict"], "?")
        print(f"  {verdict_icon} ВЕРДИКТ: {result['verdict']}")
        print(f"  Причина: {result['reason']}")
        print(f"  Рекомендация: {result['recommendation']}")
        if result.get("intuition", {}).get("somatic"):
            print(f"  Интуиция: {result['intuition']['somatic']}")
        if result.get("reason_flags"):
            print(f"  Красные флаги: {', '.join(result['reason_flags'])}")

    elif cmd == "quick" and len(args) > 1:
        situation = " ".join(args[1:])
        result = quick_check(situation)
        icon = {"danger": "⚠️", "good": "✅", "neutral": "○"}.get(result["signal"], "○")
        print(f"{icon} {result['somatic']}")
        print(f"Действие: {result['action']}")

    elif cmd == "context":
        print(generate_intuition_context())

    elif cmd == "status":
        try:
            log = []
            if INTUITION_LOG.exists():
                log = json.loads(INTUITION_LOG.read_text(encoding="utf-8"))
            print(f"\n{'='*50}")
            print("  ИНТУИЦИЯ ЭЛИАРА")
            print(f"{'='*50}")
            print(f"  Всего проверок: {len(log)}")
            if log:
                last = log[-1]
                print(f"  Последняя: {last['action'][:50]}")
                print(f"  Вердикт: {last['verdict']}")
                stop_c = sum(1 for e in log if e["verdict"] == "СТОП")
                warn_c = sum(1 for e in log if e["verdict"] == "ОСТОРОЖНО")
                ok_c = sum(1 for e in log if e["verdict"] == "ДЕЙСТВУЙ")
                print(f"  Статистика: 🛑 {stop_c} | ⚠️ {warn_c} | ✅ {ok_c}")
            print(f"{'='*50}\n")
        except Exception as e:
            print(f"Ошибка: {e}")

    else:
        print("Команды:")
        print("  py intuition.py check \"действие\"  — полная проверка")
        print("  py intuition.py quick \"ситуация\"  — быстрая интуиция")
        print("  py intuition.py context           — для LIGHTNING.md")
        print("  py intuition.py status            — статистика")
