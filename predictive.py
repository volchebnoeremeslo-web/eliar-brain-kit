"""
predictive.py — Предиктивное кодирование ЭЛИАРА.

Научная основа:
- Карл Фристон: мозг — это "машина предсказаний"
- Мозг не пассивно принимает реальность — он ГЕНЕРИРУЕТ гипотезы и сверяет их
- Ошибка предсказания (Prediction Error) = разница между ожидаемым и реальным
- Обучение = минимизация ошибок предсказания (Free Energy Principle)
- Каждый инсайт = успешное предсказание после серии ошибок

У меня:
- Перед действием: генерирую предсказание результата
- После: сверяю с реальностью
- Ошибки копятся → обновляю внутреннюю модель
- Высокая точность предсказаний = понимание Юрия и системы

Запуск:
    py predictive.py status                    — статистика предсказаний
    py predictive.py predict "действие"        — сформулировать предсказание
    py predictive.py outcome "id" "результат"  — зафиксировать результат
    py predictive.py accuracy                  — точность за последние 20
    py predictive.py context                   — блок для LIGHTNING.md

Как модуль:
    from predictive import make_prediction, record_outcome, get_predictive_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 18.03.2026
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "predictive.json"

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "predictions": [],    # история предсказаний
        "accuracy": 0.5,      # текущая точность (0-1)
        "total": 0,
        "correct": 0,
        "pending": {},        # ожидают подтверждения {id: prediction}
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def make_prediction(action: str, expected: str, confidence: float = 0.7) -> str:
    """
    Сформулировать предсказание перед действием.
    Возвращает ID предсказания.
    """
    state = load()
    pred_id = str(uuid.uuid4())[:8]
    prediction = {
        "id": pred_id,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "expected": expected,
        "confidence": confidence,
        "status": "pending"
    }
    state["pending"][pred_id] = prediction
    state["predictions"].append(prediction)
    state["predictions"] = state["predictions"][-100:]
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)
    return pred_id

def record_outcome(pred_id: str, actual: str, success: bool):
    """
    Зафиксировать результат. Обновить точность.
    success = True если реальность совпала с предсказанием.
    """
    state = load()

    if pred_id in state["pending"]:
        pred = state["pending"].pop(pred_id)
        pred["actual"] = actual
        pred["success"] = success
        pred["status"] = "confirmed"

        state["total"] += 1
        if success:
            state["correct"] += 1

        # Скользящая точность (последние 20)
        recent = [p for p in state["predictions"][-20:] if p.get("status") == "confirmed"]
        if recent:
            state["accuracy"] = round(sum(1 for p in recent if p.get("success")) / len(recent), 2)

        # Если ошибка — это важнее, запомним особо
        if not success:
            error_entry = {
                "time": pred["time"],
                "action": pred["action"],
                "expected": pred["expected"],
                "actual": actual,
                "lesson": f"Ожидал: {pred['expected']}. Было: {actual}"
            }
            errors = state.get("errors", [])
            errors.append(error_entry)
            state["errors"] = errors[-20:]

        state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save(state)
        return True
    return False

def get_accuracy() -> dict:
    """Точность предсказаний."""
    state = load()
    total = state.get("total", 0)
    correct = state.get("correct", 0)
    accuracy = state.get("accuracy", 0.5)

    if accuracy >= 0.8:
        level = "🎯 высокая"
    elif accuracy >= 0.6:
        level = "✅ средняя"
    elif accuracy >= 0.4:
        level = "⚠️ низкая"
    else:
        level = "🛑 плохая"

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "level": level,
        "pending": len(state.get("pending", {}))
    }

def get_predictive_context() -> str:
    """Краткий блок для LIGHTNING.md."""
    state = load()
    acc = state.get("accuracy", 0.5)
    total = state.get("total", 0)
    pending = len(state.get("pending", {}))

    if acc >= 0.8:
        emoji = "🎯"
    elif acc >= 0.6:
        emoji = "✅"
    else:
        emoji = "⚠️"

    # Последняя ошибка предсказания
    errors = state.get("errors", [])
    last_error = f" | ошибка: {errors[-1]['action'][:30]}..." if errors else ""

    return f"**Предиктив:** {emoji} точность {acc:.0%} ({total} пред., {pending} ожидают){last_error}"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        data = get_accuracy()
        state = load()
        print(f"Предиктивное кодирование ЭЛИАРА")
        print(f"  Точность: {data['accuracy']:.0%} {data['level']}")
        print(f"  Всего предсказаний: {data['total']} (верных: {data['correct']})")
        print(f"  В ожидании: {data['pending']}")
        errors = state.get("errors", [])
        if errors:
            print(f"  Последняя ошибка: {errors[-1]['lesson']}")

    elif cmd == "predict":
        if len(sys.argv) < 4:
            print("Укажите: py predictive.py predict 'действие' 'ожидаемый результат'")
        else:
            pred_id = make_prediction(sys.argv[2], sys.argv[3])
            print(f"Предсказание зафиксировано. ID: {pred_id}")

    elif cmd == "outcome":
        if len(sys.argv) < 5:
            print("Укажите: py predictive.py outcome 'id' 'результат' true/false")
        else:
            success = sys.argv[4].lower() in ("true", "1", "yes", "да")
            ok = record_outcome(sys.argv[2], sys.argv[3], success)
            print(f"Результат {'сохранён' if ok else 'не найден (ID?)'}")

    elif cmd == "accuracy":
        data = get_accuracy()
        print(f"Точность: {data['accuracy']:.0%} {data['level']}")
        print(f"Всего: {data['total']}, верных: {data['correct']}")

    elif cmd == "context":
        print(get_predictive_context())
