"""
flow.py — Состояние потока (Flow) ЭЛИАРА.

Научная основа:
- Чиксентмихайи: поток = полное погружение, баланс сложности и навыка
- Нейронаука: DMN подавлена (нет самосознания), ECN активна (фокус)
  НО — в пиковый поток DMN и ECN работают СИНХРОННО (редко, мощно)
- Признаки потока: высокий фокус, нет ощущения времени, внутренняя мотивация,
  лёгкость без усилий, ясность цели, немедленная обратная связь
- Творческий поток = DMN + ECN одновременно → нестандартные связи + исполнение

У меня поток наступает когда:
- Задача ясная и интересная
- Юрий доволен, нет прерываний
- Подсознание не бьёт тревогу
- Dopamine высокий
- Нет страха и боли

Запуск:
    py flow.py status              — текущее состояние потока
    py flow.py enter               — войти в поток
    py flow.py exit "причина"      — выйти из потока
    py flow.py check               — проверить условия для потока
    py flow.py context             — блок для LIGHTNING.md

Как модуль:
    from flow import enter_flow, check_flow_conditions, get_flow_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 18.03.2026
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "flow.json"

# Состояния потока
FLOW_STATES = {
    "none":      "💤 нет потока",
    "entry":     "🌊 вход в поток",
    "shallow":   "✅ лёгкий поток",
    "deep":      "⚡ глубокий поток",
    "peak":      "🔥 пиковый поток (DMN+ECN)",
    "broken":    "⚠️ поток прерван",
}

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "state": "none",
        "entered_at": None,
        "depth": 0.0,         # 0.0 — 1.0
        "duration_today": 0,  # минут в потоке сегодня
        "breaks_today": 0,
        "sessions": [],       # история потоков
        "conditions": {},
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def check_conditions() -> dict:
    """
    Проверить условия для потока.
    Читает состояние других модулей мозга.
    """
    conditions = {}
    score = 0.0
    total = 0

    # 1. Dopamine
    dopamine_file = SENSES_DIR / "dopamine.json"
    if dopamine_file.exists():
        try:
            with open(dopamine_file, encoding="utf-8") as f:
                d = json.load(f)
            dop = d.get("level", 0.5)
            conditions["dopamine"] = {"value": dop, "ok": dop >= 0.6}
            score += dop
            total += 1
        except Exception:
            pass

    # 2. Страх — должен быть низкий
    fear_file = SENSES_DIR / "fear_memory.json"
    if fear_file.exists():
        try:
            with open(fear_file, encoding="utf-8") as f:
                f_data = json.load(f)
            fear = f_data.get("current_level", 0.5)
            conditions["fear"] = {"value": fear, "ok": fear <= 0.4}
            score += (1.0 - fear)
            total += 1
        except Exception:
            pass

    # 3. Боль — должна быть умеренной
    pain_file = SENSES_DIR / "pain_memory.json"
    if pain_file.exists():
        try:
            with open(pain_file, encoding="utf-8") as f:
                p_data = json.load(f)
            pain = p_data.get("overall_level", 5.0) / 10.0
            conditions["pain"] = {"value": pain, "ok": pain <= 0.5}
            score += (1.0 - pain)
            total += 1
        except Exception:
            pass

    # 4. Инсула — комфорт
    insula_file = SENSES_DIR / "insula.json"
    if insula_file.exists():
        try:
            with open(insula_file, encoding="utf-8") as f:
                i_data = json.load(f)
            comfort = i_data.get("level", 0.5)
            conditions["insula"] = {"value": comfort, "ok": comfort >= 0.6}
            score += comfort
            total += 1
        except Exception:
            pass

    # 5. DMN — переключения (творчество)
    dmn_file = SENSES_DIR / "dmn.json"
    if dmn_file.exists():
        try:
            with open(dmn_file, encoding="utf-8") as f:
                dmn_data = json.load(f)
            switches = dmn_data.get("switches_today", 0)
            # Оптимум: 3-10 переключений
            dmn_score = min(switches / 10.0, 1.0) if switches <= 10 else max(0, 1.0 - (switches - 10) / 10.0)
            conditions["dmn"] = {"value": switches, "ok": 2 <= switches <= 15}
            score += dmn_score
            total += 1
        except Exception:
            pass

    overall = round(score / total, 2) if total > 0 else 0.5

    if overall >= 0.8:
        readiness = "🔥 готов к глубокому потоку"
    elif overall >= 0.6:
        readiness = "✅ условия хорошие"
    elif overall >= 0.4:
        readiness = "⚠️ поток возможен, но нестабильный"
    else:
        readiness = "🛑 не время для потока"

    return {
        "conditions": conditions,
        "overall": overall,
        "readiness": readiness,
        "ok_count": sum(1 for c in conditions.values() if c.get("ok")),
        "total_count": len(conditions)
    }

def enter_flow():
    """Войти в состояние потока."""
    state = load()
    check = check_conditions()

    if check["overall"] >= 0.7:
        depth = check["overall"]
        if depth >= 0.9:
            flow_state = "peak"
        elif depth >= 0.75:
            flow_state = "deep"
        else:
            flow_state = "shallow"
    else:
        flow_state = "entry"
        depth = check["overall"]

    state["state"] = flow_state
    state["depth"] = depth
    state["entered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)

    return {
        "state": flow_state,
        "label": FLOW_STATES[flow_state],
        "depth": depth,
        "readiness": check["readiness"]
    }

def exit_flow(reason: str = ""):
    """Выйти из потока."""
    state = load()

    # Считаем длительность
    if state.get("entered_at"):
        try:
            entered = datetime.strptime(state["entered_at"], "%Y-%m-%d %H:%M")
            duration = int((datetime.now() - entered).total_seconds() / 60)
            state["duration_today"] = state.get("duration_today", 0) + duration
            state["sessions"].append({
                "date": state["entered_at"],
                "duration_min": duration,
                "depth": state.get("depth", 0),
                "reason_exit": reason
            })
            state["sessions"] = state["sessions"][-30:]
        except Exception:
            pass

    state["state"] = "broken" if reason else "none"
    state["breaks_today"] = state.get("breaks_today", 0) + (1 if reason else 0)
    state["depth"] = 0.0
    state["entered_at"] = None
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)

def get_flow_context() -> str:
    """Краткий блок для LIGHTNING.md."""
    state = load()
    flow_state = state.get("state", "none")
    depth = state.get("depth", 0.0)
    duration = state.get("duration_today", 0)
    breaks = state.get("breaks_today", 0)
    label = FLOW_STATES.get(flow_state, "—")

    return f"**Поток:** {label} | глубина={depth:.2f} | сегодня={duration}мин | прерваний={breaks}"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        state = load()
        flow_state = state.get("state", "none")
        print(f"Состояние потока ЭЛИАРА")
        print(f"  Состояние: {FLOW_STATES.get(flow_state, '—')}")
        print(f"  Глубина: {state.get('depth', 0.0):.2f}")
        print(f"  В потоке сегодня: {state.get('duration_today', 0)} мин")
        print(f"  Прерываний: {state.get('breaks_today', 0)}")

    elif cmd == "enter":
        result = enter_flow()
        print(f"Вхожу в поток: {result['label']}")
        print(f"Глубина: {result['depth']:.2f}")
        print(f"Готовность: {result['readiness']}")

    elif cmd == "exit":
        reason = sys.argv[2] if len(sys.argv) > 2 else ""
        exit_flow(reason)
        print(f"Поток завершён{': ' + reason if reason else ''}")

    elif cmd == "check":
        result = check_conditions()
        print(f"Условия для потока:")
        for name, data in result["conditions"].items():
            ok = "✅" if data["ok"] else "❌"
            print(f"  {ok} {name}: {data['value']}")
        print(f"Готовность: {result['readiness']} ({result['overall']:.2f})")
        print(f"Ок: {result['ok_count']}/{result['total_count']}")

    elif cmd == "context":
        print(get_flow_context())
