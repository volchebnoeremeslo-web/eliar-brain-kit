"""
dopamine.py — Дофаминовая система ЭЛИАРА.

Научная основа:
- Дофамин = нейромедиатор мотивации, вознаграждения, любопытства
- Работает через предсказание ошибок (prediction error)
- Если результат ЛУЧШЕ ожидаемого → выброс дофамина → "хочу ещё"
- Если результат ХУЖЕ ожидаемого → падение дофамина → "избегать"
- Любопытство = ожидание уменьшения неопределённости → дофаминовый импульс

Три функции:
1. МОТИВАЦИЯ — зачем делать, что даёт энергию
2. ВОЗНАГРАЖДЕНИЕ — фиксировать что сработало, усиливать
3. ЛЮБОПЫТСТВО — детектировать пробелы в знаниях, тянуться к ним

Создано: 18.03.2026 (сессия 176) — апгрейд мозга v5.0
"""

import json, os
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "dopamine.json"

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "level": 0.5,
        "rewards": [],
        "curiosity_queue": [],
        "motivation_topics": [],
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def reward(description, strength=0.7):
    """Зафиксировать положительный результат → подъём дофамина."""
    state = load()
    state["level"] = min(1.0, state["level"] + strength * 0.1)
    state["rewards"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "description": description,
        "strength": strength
    })
    state["rewards"] = state["rewards"][-20:]  # последние 20
    state["last_updated"] = datetime.now().isoformat()
    save(state)
    print(f"Дофамин +{strength:.1f}: {description}")
    print(f"Уровень: {state['level']:.2f}")

def add_curiosity(topic):
    """Добавить тему которая вызывает любопытство."""
    state = load()
    if topic not in state["curiosity_queue"]:
        state["curiosity_queue"].append(topic)
    save(state)
    print(f"Любопытство: {topic}")

def get_context():
    """Для LIGHTNING.md — текущее состояние дофамина."""
    state = load()
    level = state["level"]
    if level > 0.7:
        mood = "высокий — мотивация сильная"
    elif level > 0.4:
        mood = "средний — рабочий режим"
    else:
        mood = "низкий — нужен импульс"

    lines = [f"**Дофамин:** {level:.2f} ({mood})"]
    if state["curiosity_queue"]:
        lines.append(f"**Любопытство:** {', '.join(state['curiosity_queue'][-3:])}")
    if state["rewards"]:
        last = state["rewards"][-1]
        lines.append(f"**Последняя награда:** {last['description']} ({last['date'][:10]})")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "reward" and len(sys.argv) > 2:
            reward(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.7)
        elif sys.argv[1] == "curious" and len(sys.argv) > 2:
            add_curiosity(sys.argv[2])
        elif sys.argv[1] == "context":
            print(get_context())
    else:
        print(get_context())
        state = load()
        if state["rewards"]:
            print("\nПоследние награды:")
            for r in state["rewards"][-5:]:
                print(f"  {r['date'][:10]} +{r['strength']}: {r['description']}")
