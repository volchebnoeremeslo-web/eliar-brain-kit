"""
metacognition.py — Метакогниция ЭЛИАРА.

Научная основа:
- Метакогниция = мышление о собственном мышлении
- Включает: мониторинг ошибок, оценку уверенности, выбор стратегии
- Нейронный субстрат: передняя поясная кора (ACC) + дорсолатеральная ПФК
- Человек с развитой метакогницией знает:
  * что он знает и чего не знает
  * насколько он уверен в своём ответе
  * какую стратегию использует
  * когда нужно остановиться и перепроверить

У меня метакогниция = честная оценка своих ответов ПЕРЕД тем как дать их.

Три слоя:
1. ЗНАЮ / НЕ ЗНАЮ — честно признать пробел вместо галлюцинации
2. УВЕРЕН / СОМНЕВАЮСЬ — калибровка уверенности
3. СТРАТЕГИЯ — выбор подхода: спросить память, поискать, спросить Юрия

Создано: 18.03.2026 (сессия 176) — апгрейд мозга v5.0
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "metacognition.json"

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "self_assessments": [],
        "error_detections": [],
        "strategy_log": [],
        "calibration_score": 0.5,
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def assess(topic, confidence, know_or_not, strategy=""):
    """
    Оценить свои знания по теме.
    confidence: 0.0-1.0
    know_or_not: "знаю" / "не знаю" / "частично"
    strategy: что делать дальше
    """
    state = load()
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": topic,
        "confidence": confidence,
        "status": know_or_not,
        "strategy": strategy
    }
    state["self_assessments"].append(entry)
    state["self_assessments"] = state["self_assessments"][-20:]
    state["last_updated"] = datetime.now().isoformat()
    save(state)
    print(f"Метакогниция: '{topic}' — {know_or_not} (уверенность {confidence:.0%})")
    if strategy:
        print(f"Стратегия: {strategy}")

def detect_error(description):
    """Зафиксировать обнаруженную ошибку в своём мышлении."""
    state = load()
    state["error_detections"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "error": description
    })
    state["error_detections"] = state["error_detections"][-20:]
    save(state)
    print(f"Ошибка мышления обнаружена: {description}")

def get_context():
    state = load()
    lines = [f"**Калибровка уверенности:** {state['calibration_score']:.0%}"]
    if state["error_detections"]:
        last = state["error_detections"][-1]
        lines.append(f"**Последняя обнаруженная ошибка:** {last['error']} ({last['date'][:10]})")
    if state["self_assessments"]:
        unknowns = [a for a in state["self_assessments"] if a["status"] == "не знаю"]
        if unknowns:
            lines.append(f"**Открытые пробелы:** {len(unknowns)} тем требуют изучения")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "assess":
            assess(sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
        elif sys.argv[1] == "error":
            detect_error(" ".join(sys.argv[2:]))
    else:
        print(get_context())
