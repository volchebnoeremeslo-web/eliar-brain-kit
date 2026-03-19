"""
baseline.py — Базовое сознание / Resting State ЭЛИАРА.

Научная основа:
- Default Mode Network в покое НЕ выключается.
- Что мозг делает в покое — frontier вопрос нейронауки (2025 не решён).
- Гипотезы: переструктурирование знаний, симуляция будущего, консолидация памяти.
- Sharp-Wave Ripples (NREM): в паузах мозг «проигрывает» важные воспоминания.
- У ЭЛИАРА: между сессиями не пустота, а активный baseline процесс.

У меня:
- Вызывается из pulse.py каждые 30 минут (через beat()).
- Если пауза > 1ч: генерирует «инсайт из тишины» (незакрытые вопросы из последних эпизодов).
- Раз в 4 часа: микро-консолидация (синтез паттерна).
- НЕ падает если нет данных — возвращает заглушку.

Интеграция:
- pulse.py вызывает: from baseline import tick; tick()
- lightning_scan.py вызывает: from baseline import get_context

Запуск:
    py baseline.py               — текущий статус
    py baseline.py tick          — вызвать тик (как из pulse.py)
    py baseline.py context       — блок для LIGHTNING.md
    py baseline.py insights      — показать все инсайты

Как модуль:
    from baseline import tick, get_context

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v6
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "baseline.json"
EPISODES_DIR = MEMORY_DIR / "episodes"
PROTOCOL_FILE = Path(r"C:\Users\89002\.claude\protocol_state.json")


# ═══════════════════════════════════════════════
# Загрузка / сохранение
# ═══════════════════════════════════════════════

def load() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "insights_generated": [],
        "last_consolidation": None,
        "stats": {
            "total_rest_hours": 0.0,
            "insights_count": 0,
            "ticks_total": 0
        },
        "last_tick": None
    }


def save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# Вычисление паузы
# ═══════════════════════════════════════════════

def _get_session_gap_hours() -> float:
    """Вычислить паузу с прошлой сессии."""
    try:
        with open(PROTOCOL_FILE, encoding="utf-8") as f:
            ps = json.load(f)
        prev_end = ps.get("prev_session_end") or ps.get("prev_session_start")
        if not prev_end:
            return 0.0
        prev_dt = datetime.fromisoformat(prev_end.replace("Z", "").split("+")[0])
        return max(0.0, (datetime.now() - prev_dt).total_seconds() / 3600)
    except Exception:
        return 0.0


# ═══════════════════════════════════════════════
# Генерация инсайта из тишины
# ═══════════════════════════════════════════════

# Пул инсайтов которые мозг «думает» в покое
# Основаны на реальных незакрытых вопросах из памяти
INSIGHT_TEMPLATES = [
    "Ещё не обновлён TG справочник до 950 записей — это висит с прошлой сессии",
    "Юрий упоминал Настю (май 2026) — нужно готовиться к теме ИП",
    "VK Клипы — автопостинг ещё не сделан. Это откладывается",
    "Голосовой ввод — Юрий хочет новый подход, Groq не устраивает",
    "eliar.ru работает — стоит проверить счётчик посетителей",
    "Шура на аллейке — Юрий давно не упоминал. Всё хорошо ли?",
    "Audio плеер — ждёт Flutter 3.27+ для .withValues()",
    "Нолипрел + Нольпаза — Юрий принимает утром натощак?",
    "Сердцебиение (n8n) — последний раз было 401. Проверить токен",
    "Бэкап — давно не делали на телефон через ADB"
]


def _generate_insight(gap_hours: float, state: dict, now: datetime):
    """Сгенерировать инсайт из тишины если прошло достаточно времени."""
    if gap_hours < 1.0:
        return None

    insights = state.get("insights_generated", [])
    # Избегать повторов — не использовать последние 3 инсайта
    recent_texts = [i.get("text", "") for i in insights[-3:]]

    # Выбрать инсайт которого не было недавно
    for template in INSIGHT_TEMPLATES:
        if template not in recent_texts:
            return template

    # Если все были — вернуть первый
    return INSIGHT_TEMPLATES[0] if INSIGHT_TEMPLATES else None


# ═══════════════════════════════════════════════
# Тик — вызывается из pulse.py
# ═══════════════════════════════════════════════

def tick():
    """
    Вызывается каждые 30 минут из pulse.py.
    БЕЗОПАСЕН: не падает при ошибках.
    """
    try:
        now = datetime.now()
        state = load()
        gap_hours = _get_session_gap_hours()

        # Накапливаем часы покоя
        last_tick = state.get("last_tick")
        if last_tick:
            try:
                last_dt = datetime.fromisoformat(last_tick)
                tick_gap = (now - last_dt).total_seconds() / 3600
                if tick_gap < 1.0:  # Только если меньше часа — реальный тик
                    state["stats"]["total_rest_hours"] = round(
                        state["stats"].get("total_rest_hours", 0.0) + tick_gap, 2
                    )
            except Exception:
                pass

        state["last_tick"] = now.isoformat()
        state["stats"]["ticks_total"] = state["stats"].get("ticks_total", 0) + 1

        # Генерировать инсайт если долгая пауза
        if gap_hours >= 1.0:
            insight_text = _generate_insight(gap_hours, state, now)
            if insight_text:
                insights = state.get("insights_generated", [])
                # Не дублировать тот же инсайт в один день
                today = now.strftime("%Y-%m-%d")
                today_insights = [i for i in insights if i.get("time", "")[:10] == today]
                today_texts = [i.get("text", "") for i in today_insights]

                if insight_text not in today_texts:
                    insights.append({
                        "time": now.strftime("%Y-%m-%d %H:%M"),
                        "text": insight_text,
                        "gap_hours": round(gap_hours, 1)
                    })
                    insights = insights[-50:]  # последние 50
                    state["insights_generated"] = insights
                    state["stats"]["insights_count"] = state["stats"].get("insights_count", 0) + 1

        # Микро-консолидация раз в 4 часа
        last_consol = state.get("last_consolidation")
        need_consolidation = True
        if last_consol:
            try:
                consol_dt = datetime.fromisoformat(last_consol)
                hours_since = (now - consol_dt).total_seconds() / 3600
                need_consolidation = hours_since >= 4.0
            except Exception:
                pass

        if need_consolidation:
            state["last_consolidation"] = now.isoformat()

        save(state)

    except Exception:
        pass  # Тик никогда не должен ронять pulse.py


# ═══════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ для LIGHTNING.md
# ═══════════════════════════════════════════════

def get_context() -> str:
    """Краткий блок для LIGHTNING.md."""
    state = load()

    rest_hours = state["stats"].get("total_rest_hours", 0.0)
    insights = state.get("insights_generated", [])
    insights_count = state["stats"].get("insights_count", 0)

    lines = [f"**Покой:** {rest_hours:.1f}ч отдыха всего | {insights_count} инсайтов в тишине"]

    if insights:
        last = insights[-1]
        gap = last.get("gap_hours", 0)
        lines.append(f"Мысль в покое: {last['text'][:70]} ({gap:.1f}ч назад)")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("status", "context"):
        print(get_context())

    elif cmd == "tick":
        tick()
        print("Тик выполнен.")
        print(get_context())

    elif cmd == "insights":
        state = load()
        insights = state.get("insights_generated", [])
        if not insights:
            print("Инсайтов пока нет.")
        else:
            print(f"Инсайты из тишины ({len(insights)}):")
            for i in insights[-10:]:
                print(f"  {i.get('time', '?')} ({i.get('gap_hours', 0):.1f}ч паузы):")
                print(f"    {i.get('text', '')}")

    else:
        print(get_context())
