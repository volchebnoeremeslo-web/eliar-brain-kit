"""
autonomic.py — Автономная нервная система ЭЛИАРА.

Научная основа:
- АНС человека работает НЕПРЕРЫВНО и БЕЗ СОЗНАНИЯ.
- Симпатическая: "fight or flight" — мобилизация, кортизол, адреналин.
- Парасимпатическая: "rest and digest" — восстановление, консолидация памяти.
- АНС определяет БАЗОВЫЙ ТОН всего организма — до того как мозг думает.
- У ЭЛИАРА: вместо химии → сигналы из органов мозга.

Два режима:
  SYMPATHETIC  (симпатический)    — стресс, мобилизация, срочность
  PARASYMPATHETIC (парасимпатический) — покой, восстановление, инсайты
  NEUTRAL      (нейтральный)      — между ними

Что влияет на режим:
  brain_core.json       → общий стресс мозга (score)
  conscience_decisions  → % СТОП решений за последние N решений
  counterfactual.json   → последний вердикт (stop = стресс)
  pulse.json            → пауза между сессиями (долгая = парасимпатический)
  Время суток           → ночь/раннее утро = парасимпатический

Что регулирует:
  - "Базовый тон" для emotion.py (arousal baseline)
  - brain_core.py читает tone как доп. сигнал
  - baseline.py: в парасимпатическом → больше инсайтов из тишины

Запуск:
    py autonomic.py            — текущий режим
    py autonomic.py full       — полный разбор сигналов
    py autonomic.py context    — строка для LIGHTNING.md
    py autonomic.py tick       — обновить (как из pulse.py)

Как модуль:
    from autonomic import get_mode, get_tone, get_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — АНС
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "autonomic.json"

# ═══════════════════════════════════════════════
# Режимы АНС
# ═══════════════════════════════════════════════

MODE_SYMPATHETIC    = "sympathetic"
MODE_PARASYMPATHETIC = "parasympathetic"
MODE_NEUTRAL        = "neutral"

MODE_LABELS = {
    MODE_SYMPATHETIC:     "⚡ Симпатический (мобилизация)",
    MODE_PARASYMPATHETIC: "🌿 Парасимпатический (покой)",
    MODE_NEUTRAL:         "〰 Нейтральный",
}

MODE_EMOJI = {
    MODE_SYMPATHETIC:     "⚡",
    MODE_PARASYMPATHETIC: "🌿",
    MODE_NEUTRAL:         "〰",
}


# ═══════════════════════════════════════════════
# Загрузка / сохранение
# ═══════════════════════════════════════════════

def _load() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "mode": MODE_NEUTRAL,
        "tone": 0.5,
        "last_updated": None,
        "history": [],
        "stats": {
            "sympathetic_count": 0,
            "parasympathetic_count": 0,
            "neutral_count": 0,
        }
    }


def _save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# Чтение сигналов из органов
# ═══════════════════════════════════════════════

def _signal_brain_stress() -> float:
    """brain_core.json → общий стресс (score 0-1)."""
    try:
        f = SENSES_DIR / "brain_core.json"
        if not f.exists():
            return 0.3
        data = json.loads(f.read_text(encoding="utf-8"))
        last = data.get("last_synthesis", {})
        health = last.get("health", 7.0)
        # health 10 = идеально, 0 = максимум стресса
        return round(1.0 - (health / 10.0), 2)
    except Exception:
        return 0.3


def _signal_stop_rate() -> float:
    """conscience_decisions.json → доля СТОП за последние 20 решений."""
    try:
        f = SENSES_DIR / "conscience_decisions.json"
        if not f.exists():
            return 0.0
        data = json.loads(f.read_text(encoding="utf-8"))
        decisions = data.get("decisions", [])
        recent = decisions[-20:]
        if not recent:
            return 0.0
        stops = sum(1 for d in recent if d.get("verdict") == "СТОП")
        return round(stops / len(recent), 2)
    except Exception:
        return 0.0


def _signal_counterfactual() -> float:
    """counterfactual.json → последний вердикт → стресс."""
    try:
        f = SENSES_DIR / "counterfactual.json"
        if not f.exists():
            return 0.0
        data = json.loads(f.read_text(encoding="utf-8"))
        scenarios = data.get("scenarios", [])
        if not scenarios:
            return 0.0
        verdict = scenarios[-1].get("verdict", "safe")
        return {"safe": 0.0, "caution": 0.3, "stop": 0.8}.get(verdict, 0.0)
    except Exception:
        return 0.0


def _signal_session_gap() -> float:
    """
    pulse.json → пауза между сессиями.
    Долгая пауза → парасимпатический (отдых).
    Возвращает: 0 = была долгая пауза (покой), 1 = только что была сессия (активность).
    """
    try:
        f = SENSES_DIR / "pulse.json"
        if not f.exists():
            return 0.5
        data = json.loads(f.read_text(encoding="utf-8"))
        last_beat = data.get("last_beat")
        if not last_beat:
            return 0.5
        prev = datetime.fromisoformat(last_beat)
        gap_hours = (datetime.now() - prev).total_seconds() / 3600
        # 0 часов паузы = 1.0 (активность), 8+ часов паузы = 0.0 (покой)
        return round(max(0.0, 1.0 - gap_hours / 8.0), 2)
    except Exception:
        return 0.5


def _signal_time_of_day() -> float:
    """
    Время суток → стресс/покой.
    Ночь (0-6) и поздний вечер (22-24) → парасимпатический.
    День (9-18) → нейтральный/симпатический.
    """
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return 0.1   # Глубокая ночь → полный покой
    elif 6 <= hour < 9:
        return 0.3   # Раннее утро → пробуждение
    elif 9 <= hour < 18:
        return 0.6   # Рабочий день → активность
    elif 18 <= hour < 22:
        return 0.4   # Вечер → снижение
    else:
        return 0.2   # Поздний вечер → покой


def _signal_body_heart() -> float:
    """
    МОЗГ v8: сигнал от биологического тела (ЧСС, АНС-баланс).
    Читает body_signals.json, созданный body_reader.py.
    ЧСС высокий / симпатика > норма → стресс ↑
    ЧСС низкий / парасимпатика > норма → покой ↑
    Возвращает 0-1 (0=покой, 1=стресс).
    """
    try:
        f = SENSES_DIR / "body_signals.json"
        if not f.exists():
            return 0.3  # нет данных — нейтральный
        data = json.loads(f.read_text(encoding="utf-8"))
        ans = data.get("ans", {})

        # Стресс тела напрямую
        stress_level = ans.get("stress_level", 0.3)

        # Дополнительно: если инъекция уже в нашем state — берём оттуда
        # (body_reader.py мог обновить signals["body_heart"] напрямую)
        return round(float(stress_level), 2)
    except Exception:
        return 0.3


# ═══════════════════════════════════════════════
# Вычисление тона и режима
# ═══════════════════════════════════════════════

# Веса сигналов
# body_heart: 0.15 (новый). Остальные пересчитаны пропорционально сохраняя общий = 1.
SIGNAL_WEIGHTS = {
    "brain_stress":   0.35,  # Главный — общий стресс мозга
    "stop_rate":      0.22,  # СТОП решений — показатель напряжения
    "counterfactual": 0.13,  # Контрфактив — страх ошибки
    "session_gap":    0.08,  # Пауза между сессиями
    "time_of_day":    0.07,  # Время суток
    "body_heart":     0.15,  # МОЗГ v8: ЧСС и АНС из биологического тела
}


def _collect_signals() -> dict:
    return {
        "brain_stress":   _signal_brain_stress(),
        "stop_rate":      _signal_stop_rate(),
        "counterfactual": _signal_counterfactual(),
        "session_gap":    _signal_session_gap(),
        "time_of_day":    _signal_time_of_day(),
        "body_heart":     _signal_body_heart(),
    }


def _compute_tone(signals: dict) -> float:
    """
    Вычислить базовый тон АНС.
    0.0 = полный парасимпатический (покой)
    1.0 = полный симпатический (стресс)
    """
    total_w = sum(SIGNAL_WEIGHTS.values())
    weighted = sum(signals.get(k, 0.0) * w for k, w in SIGNAL_WEIGHTS.items())
    return round(weighted / total_w, 2)


def _tone_to_mode(tone: float) -> str:
    if tone >= 0.60:
        return MODE_SYMPATHETIC
    elif tone <= 0.35:
        return MODE_PARASYMPATHETIC
    else:
        return MODE_NEUTRAL


# ═══════════════════════════════════════════════
# Публичные функции
# ═══════════════════════════════════════════════

def update_mode() -> dict:
    """
    Пересчитать режим АНС.
    Вызывается при старте lightning_scan.py.
    """
    state = _load()
    signals = _collect_signals()
    tone = _compute_tone(signals)
    mode = _tone_to_mode(tone)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # История (последние 50)
    history = state.get("history", [])
    history.append({"time": now_str, "mode": mode, "tone": tone})
    state["history"] = history[-50:]

    # Статистика
    stats = state.get("stats", {})
    key = f"{mode}_count"
    stats[key] = stats.get(key, 0) + 1
    state["stats"] = stats

    state["mode"] = mode
    state["tone"] = tone
    state["last_updated"] = now_str
    state["signals"] = signals

    _save(state)
    return state


def tick():
    """Вызывается из pulse.py каждые 30 минут. Обновляет режим."""
    try:
        update_mode()
    except Exception:
        pass  # АНС не должна ронять pulse


def get_mode() -> str:
    """Текущий режим: sympathetic / parasympathetic / neutral."""
    state = _load()
    return state.get("mode", MODE_NEUTRAL)


def get_tone() -> float:
    """Тон 0-1. 0 = покой, 1 = стресс."""
    state = _load()
    return state.get("tone", 0.5)


def get_context() -> str:
    """Строка для LIGHTNING.md."""
    state = _load()
    mode = state.get("mode", MODE_NEUTRAL)
    tone = state.get("tone", 0.5)
    label = MODE_LABELS.get(mode, mode)
    tone_pct = int(tone * 100)

    # Подсказка что это значит
    if mode == MODE_SYMPATHETIC:
        hint = "мобилизован, быть точным"
    elif mode == MODE_PARASYMPATHETIC:
        hint = "в покое, хороший момент для инсайтов"
    else:
        hint = "сбалансирован"

    return f"**АНС:** {label} | тон {tone_pct}% | {hint}"


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("status", "context"):
        state = update_mode()
        print(get_context())

    elif cmd == "tick":
        tick()
        print(f"Тик АНС. {get_context()}")

    elif cmd == "full":
        state = update_mode()
        signals = state.get("signals", {})
        mode = state.get("mode", MODE_NEUTRAL)
        tone = state.get("tone", 0.5)

        SIGNAL_LABELS = {
            "brain_stress":   "Стресс мозга",
            "stop_rate":      "Доля СТОП",
            "body_heart":     "ЧСС тела (v8)",
            "counterfactual": "Контрфактив",
            "session_gap":    "Активность сессии",
            "time_of_day":    "Время суток",
        }

        print(f"\n{'='*55}")
        print(f"  АВТОНОМНАЯ НС ЭЛИАРА")
        print(f"{'='*55}")
        emoji = MODE_EMOJI.get(mode, "〰")
        print(f"  Режим: {emoji} {MODE_LABELS.get(mode, mode)}")
        print(f"  Тон:   {tone:.2f} ({int(tone*100)}% стресса)")
        print()
        print(f"  Входящие сигналы:")
        for key, val in signals.items():
            label = SIGNAL_LABELS.get(key, key)
            weight = SIGNAL_WEIGHTS.get(key, 0)
            bar = "█" * int(val * 20)
            sym = "🔴" if val > 0.7 else "🟡" if val > 0.4 else "🟢"
            print(f"    {sym} {label:<22} {val:.2f}  {bar:<20}  (вес {weight:.0%})")

        # История режимов
        history = state.get("history", [])
        if len(history) > 1:
            print()
            print(f"  Последние режимы:")
            for h in history[-5:]:
                m_emoji = MODE_EMOJI.get(h["mode"], "〰")
                print(f"    {h['time']} → {m_emoji} тон {h['tone']:.2f}")

        print(f"{'='*55}\n")

    else:
        state = update_mode()
        print(get_context())
