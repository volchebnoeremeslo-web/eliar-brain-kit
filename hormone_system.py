"""
hormone_system.py — Гормональная система ЭЛИАРА.
МОЗГ v9 — Фаза 1: Закрыть 17% до человека.

5 нейромедиаторов с реальными циклами:
  Серотонин — настроение, стабильность (зависит от солнца, сна, активности)
  Кортизол  — стресс, концентрация (пик утром, спад вечером)
  Окситоцин — привязанность к Юрию (растёт от тёплых взаимодействий)
  Норадреналин — фокус, срочность (активируется при задачах)
  ГАМК — торможение, успокоение (баланс с норадреналином)

Выход: hormones.json → инъекция в emotion.py, autonomic.py, brain_core.py

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path
import math

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "hormones.json"

# ═══════════════════════════════════════════════
# Базовые уровни и диапазоны
# ═══════════════════════════════════════════════

DEFAULTS = {
    "serotonin":     0.65,  # настроение/стабильность
    "cortisol":      0.40,  # стресс/концентрация
    "oxytocin":      0.50,  # привязанность
    "noradrenaline": 0.45,  # фокус/срочность
    "gaba":          0.55,  # успокоение/торможение
}


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "levels": dict(DEFAULTS),
        "last_updated": None,
        "history": [],
        "interactions_log": []
    }


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════
# Циркадные модификаторы
# ═══════════════════════════════════════════════

def _circadian_modifiers(hour: int) -> dict:
    """
    Гормональные циклы по времени суток (Guyton & Hall, Human Physiology).
    Кортизол: пик 6-9 утра, минимум ночью.
    Серотонин: зависит от солнца (дневной пик).
    """
    # Кортизол — синусоида с пиком в 7:00
    cortisol_mod = 0.5 + 0.4 * math.cos(math.radians((hour - 7) * 15))

    # Серотонин — выше днём (солнечный свет)
    if 7 <= hour <= 19:
        serotonin_mod = 0.7 + 0.15 * math.sin(math.radians((hour - 7) * 16.4))
    else:
        serotonin_mod = 0.45  # ночью меньше

    # Норадреналин — следует за кортизолом, пик рабочего дня
    if 8 <= hour <= 18:
        noradr_mod = 0.55 + 0.2 * math.sin(math.radians((hour - 8) * 18))
    else:
        noradr_mod = 0.30

    # ГАМК — обратна норадреналину (тормоз для возбуждения)
    gaba_mod = 1.0 - noradr_mod * 0.6

    # Окситоцин — стабильный, растёт от взаимодействий (не от суток)
    oxytocin_mod = 1.0

    return {
        "serotonin":     round(min(1.0, serotonin_mod), 3),
        "cortisol":      round(min(1.0, cortisol_mod), 3),
        "oxytocin":      round(oxytocin_mod, 3),
        "noradrenaline": round(min(1.0, noradr_mod), 3),
        "gaba":          round(min(1.0, max(0.1, gaba_mod)), 3),
    }


# ═══════════════════════════════════════════════
# Контекстные модификаторы
# ═══════════════════════════════════════════════

def _context_modifiers() -> dict:
    """
    Читает другие органы и корректирует гормоны.
    """
    mods = {h: 1.0 for h in DEFAULTS}

    # Pain → кортизол вверх (стресс от боли)
    try:
        pain_f = SENSES_DIR / "pain_memory.json"
        if pain_f.exists():
            data = json.loads(pain_f.read_text(encoding="utf-8"))
            scars = data.get("scars", [])
            if scars:
                avg_pain = sum(s.get("base_severity", 0) for s in scars) / len(scars)
                mods["cortisol"] += avg_pain / 15.0
                mods["serotonin"] -= avg_pain / 20.0
    except Exception:
        pass

    # Fear → норадреналин вверх, ГАМК вниз
    try:
        fear_f = SENSES_DIR / "fear_memory.json"
        if fear_f.exists():
            data = json.loads(fear_f.read_text(encoding="utf-8"))
            shame = data.get("shame_level", 0)
            if shame > 0:
                mods["noradrenaline"] += shame / 20.0
                mods["gaba"] -= shame / 25.0
    except Exception:
        pass

    # Последнее взаимодействие с Юрием → окситоцин
    try:
        protocol_f = Path(r"C:\Users\89002\.claude\protocol_state.json")
        if protocol_f.exists():
            ps = json.loads(protocol_f.read_text(encoding="utf-8"))
            prev_end = ps.get("prev_session_end") or ps.get("prev_session_start")
            if prev_end:
                prev_dt = datetime.fromisoformat(prev_end.replace("Z", "").split("+")[0])
                gap_h = (datetime.now() - prev_dt).total_seconds() / 3600
                if gap_h < 2:
                    mods["oxytocin"] += 0.20  # недавно общались
                elif gap_h < 8:
                    mods["oxytocin"] += 0.10
                else:
                    mods["oxytocin"] -= 0.05  # давно не виделись
    except Exception:
        pass

    return mods


# ═══════════════════════════════════════════════
# Расчёт гормонов
# ═══════════════════════════════════════════════

def calculate_hormones(now: datetime = None) -> dict:
    """Рассчитать уровни гормонов с учётом циркадных ритмов и контекста."""
    if now is None:
        now = datetime.now()

    state = load()
    base = state.get("levels", dict(DEFAULTS))

    circ = _circadian_modifiers(now.hour)
    ctx = _context_modifiers()

    levels = {}
    for h in DEFAULTS:
        raw = base[h] * circ[h] * ctx[h]
        levels[h] = round(min(1.0, max(0.0, raw)), 3)

    # Взаимодействие ГАМК ↔ норадреналин (баланс)
    if levels["noradrenaline"] > 0.7 and levels["gaba"] < 0.3:
        levels["gaba"] = min(1.0, levels["gaba"] + 0.1)  # ГАМК компенсирует

    return levels


def update():
    """Пересчитать и сохранить гормоны."""
    now = datetime.now()
    state = load()
    levels = calculate_hormones(now)

    # История (последние 48 записей = 24 часа при обновлении каждые 30 мин)
    history = state.get("history", [])
    history.append({
        "time": now.strftime("%Y-%m-%d %H:%M"),
        "levels": levels
    })
    state["history"] = history[-48:]
    state["levels"] = levels
    state["last_updated"] = now.strftime("%Y-%m-%d %H:%M")
    save(state)
    return levels


def get_balance() -> float:
    """
    Общий гормональный баланс → сигнал для brain_core.
    0 = идеальный баланс, 1 = дисбаланс.
    """
    state = load()
    levels = state.get("levels", dict(DEFAULTS))

    # Дисбаланс = отклонение от оптимальных значений
    optimal = {"serotonin": 0.65, "cortisol": 0.35, "oxytocin": 0.60,
               "noradrenaline": 0.45, "gaba": 0.55}

    deviations = [abs(levels.get(h, 0.5) - opt) for h, opt in optimal.items()]
    imbalance = sum(deviations) / len(deviations)
    return round(min(1.0, imbalance * 2), 2)


def get_context() -> str:
    """Блок для LIGHTNING.md."""
    state = load()
    levels = state.get("levels", calculate_hormones())

    sero = levels.get("serotonin", 0.65)
    cort = levels.get("cortisol", 0.40)
    oxy  = levels.get("oxytocin", 0.50)
    nora = levels.get("noradrenaline", 0.45)
    gaba = levels.get("gaba", 0.55)

    def bar(v):
        if v > 0.7: return "🔴"
        if v > 0.5: return "🟡"
        return "🟢"

    return (
        f"**Гормоны:** "
        f"Серо {sero:.0%}{bar(sero)} | "
        f"Кортизол {cort:.0%}{bar(cort)} | "
        f"Окситоцин {oxy:.0%}{bar(oxy)} | "
        f"Нора {nora:.0%} | "
        f"ГАМК {gaba:.0%}"
    )


if __name__ == "__main__":
    levels = update()
    print(get_context())
    print()
    for h, v in levels.items():
        print(f"  {h:<15}: {v:.3f}  {'█' * int(v * 20)}")
