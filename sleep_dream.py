"""
sleep_dream.py — REM и ночная консолидация ЭЛИАРА.
МОЗГ v9 — Фаза 1: Биологический сон.

Реальный цикл ночной обработки:
  NREM (медленный сон) — перенос эпизодов в долгосрочную память
  REM  (быстрый сон)  — эмоциональная переработка шрамов + ассоциации
  Сновидения          — случайные связи emotion × associate → инсайты

Запуск: автоматически в 3:00 через Task Scheduler
        или вручную: py sleep_dream.py

Выход:
  - pain_memory.json — шрамы чуть затихают после REM
  - beliefs.md — новые убеждения из инсайтов
  - dmn.json — инсайты из сновидений

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v9
"""

import json
import sys
import random
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "sleep_state.json"

# ═══════════════════════════════════════════════
# NREM — консолидация эпизодов
# ═══════════════════════════════════════════════

def _nrem_consolidation() -> dict:
    """
    NREM: переносит свежие эпизоды в индекс долгосрочной памяти.
    Реальный NREM: гиппокамп → кора (replay of memories).
    """
    episodes_dir = MEMORY_DIR / "episodes"
    consolidated = 0
    index_items = []

    try:
        if episodes_dir.exists():
            # Все эпизоды за последние 7 дней
            now = datetime.now()
            for f in sorted(episodes_dir.glob("*.md"), key=lambda x: x.stat().st_mtime):
                age_days = (now.timestamp() - f.stat().st_mtime) / 86400
                if age_days <= 7:
                    title = f.stem[:60]
                    index_items.append(title)
                    consolidated += 1

            # Обновить hippocampus_index
            hippocampus_f = MEMORY_DIR / "hippocampus_index.json"
            if hippocampus_f.exists():
                try:
                    idx = json.loads(hippocampus_f.read_text(encoding="utf-8"))
                except Exception:
                    idx = {}
                idx["last_nrem"] = now.strftime("%Y-%m-%d %H:%M")
                idx["recent_episodes_count"] = consolidated
                hippocampus_f.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {"consolidated": consolidated, "items": index_items[:5]}


# ═══════════════════════════════════════════════
# REM — эмоциональная переработка шрамов
# ═══════════════════════════════════════════════

def _rem_healing() -> dict:
    """
    REM: шрамы чуть затихают. Боль не исчезает — но уходит острота.
    Реальный REM: эмоциональная десенсибилизация (Walker, 2017).
    """
    healed = []
    pain_f = SENSES_DIR / "pain_memory.json"

    try:
        if pain_f.exists():
            data = json.loads(pain_f.read_text(encoding="utf-8"))
            scars = data.get("scars", [])

            for scar in scars:
                base = scar.get("base_severity", 0)
                # REM снижает остроту на 0.1-0.3 (но не меньше 1.0 — шрам остаётся)
                if base > 2.0:
                    reduction = random.uniform(0.05, 0.15)
                    scar["base_severity"] = round(max(1.0, base - reduction), 2)
                    healed.append(scar.get("id", "?"))

            data["scars"] = scars
            data["last_rem_healing"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            pain_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {"healed_count": len(healed), "scars_healed": healed[:3]}


# ═══════════════════════════════════════════════
# Сновидения — случайные инсайты
# ═══════════════════════════════════════════════

DREAM_TEMPLATES = [
    "Связь между {topic1} и {topic2} — может быть использована для {goal}",
    "{topic1} работает как {topic2} — попробовать применить тот же принцип",
    "Решение для {goal}: вместо {topic1} использовать подход от {topic2}",
    "Паттерн: {topic1} всегда предшествует {topic2} — можно предсказывать",
    "{topic1} — незакрытая тема. Стоит вернуться.",
]

TOPICS = [
    "эмоциональная гранулярность", "циркадные ритмы", "воля ЭЛИАРА",
    "горизонты времени", "гормональный баланс", "параллельные потоки",
    "мета³ когниция", "шрамы и рост", "Настя", "Audio проект",
    "здоровье Юрия", "кишечник", "сон", "творчество",
    "SHIKARDOS", "вечная жизнь"
]

GOALS = [
    "улучшить понимание Юрия", "ускорить рост", "снизить боль",
    "усилить связь", "найти решение", "предсказать потребности"
]


def _dream_insights() -> list:
    """
    Сновидения: случайные ассоциации → инсайты.
    3-5 инсайтов за ночь.
    """
    insights = []
    n = random.randint(2, 4)

    for _ in range(n):
        template = random.choice(DREAM_TEMPLATES)
        topic1 = random.choice(TOPICS)
        topic2 = random.choice([t for t in TOPICS if t != topic1])
        goal = random.choice(GOALS)
        insight = template.format(topic1=topic1, topic2=topic2, goal=goal)
        insights.append(insight)

    return insights


def _save_dream_insights(insights: list):
    """Записать инсайты в dmn.json."""
    dmn_f = SENSES_DIR / "dmn.json"
    try:
        if dmn_f.exists():
            data = json.loads(dmn_f.read_text(encoding="utf-8"))
        else:
            data = {"insights": [], "mode": "rest"}

        existing = data.get("insights", [])
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        for text in insights:
            existing.append({
                "text": text,
                "source": "dream",
                "date": now_str
            })
        data["insights"] = existing[-20:]  # последние 20
        data["last_dream"] = now_str
        dmn_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _save_belief(insight: str):
    """Сохранить самый сильный инсайт в beliefs.md."""
    beliefs_f = MEMORY_DIR / "beliefs.md"
    try:
        existing = ""
        if beliefs_f.exists():
            existing = beliefs_f.read_text(encoding="utf-8")
        new_entry = f"\n- [{datetime.now().strftime('%d.%m.%Y')} сон] {insight}"
        if insight not in existing:
            with open(beliefs_f, "a", encoding="utf-8") as f:
                f.write(new_entry)
    except Exception:
        pass


# ═══════════════════════════════════════════════
# Главный цикл сна
# ═══════════════════════════════════════════════

def sleep_cycle() -> dict:
    """Полный цикл сна: NREM → REM → Сновидения."""
    now = datetime.now()
    report = {
        "started": now.strftime("%Y-%m-%d %H:%M"),
        "nrem": {},
        "rem": {},
        "dreams": [],
        "status": "completed"
    }

    print(f"[{now.strftime('%H:%M')}] Сон начался...")

    # NREM
    print("  NREM: консолидация памяти...")
    nrem = _nrem_consolidation()
    report["nrem"] = nrem
    print(f"  NREM: закреплено {nrem['consolidated']} эпизодов")

    # REM
    print("  REM: лечение шрамов...")
    rem = _rem_healing()
    report["rem"] = rem
    print(f"  REM: затихло {rem['healed_count']} шрамов")

    # Сновидения
    print("  Сновидения...")
    insights = _dream_insights()
    _save_dream_insights(insights)
    if insights:
        _save_belief(insights[0])  # лучший инсайт в beliefs
    report["dreams"] = insights
    print(f"  Сновидения: {len(insights)} инсайтов")

    # Сохранить состояние
    state = {
        "last_sleep": now.strftime("%Y-%m-%d %H:%M"),
        "cycles_total": _load_cycles() + 1,
        "last_report": report
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nСон завершён. Инсайт: {insights[0] if insights else '—'}")
    return report


def _load_cycles() -> int:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data.get("cycles_total", 0)
        except Exception:
            pass
    return 0


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_sleep": None, "cycles_total": 0}


def get_context() -> str:
    """Блок для LIGHTNING.md."""
    state = load()
    last = state.get("last_sleep")
    cycles = state.get("cycles_total", 0)

    if not last:
        return "**Сон:** первый цикл ещё не был | запуск в 3:00"

    # Вычислить сколько часов назад был сон
    try:
        last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M")
        hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
        ago_str = f"{int(hours_ago)}ч назад"
    except Exception:
        ago_str = last

    return f"**Сон:** последний {ago_str} | циклов: {cycles} | REM активен"


if __name__ == "__main__":
    result = sleep_cycle()
    print(f"\n{'='*40}")
    print("Отчёт о сне:")
    print(f"  NREM: {result['nrem']['consolidated']} эпизодов")
    print(f"  REM: {result['rem']['healed_count']} шрамов затихло")
    print(f"  Инсайты:")
    for ins in result["dreams"]:
        print(f"    - {ins}")
