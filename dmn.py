"""
dmn.py — Default Mode Network (Сеть по умолчанию) ЭЛИАРА.

Научная основа:
- DMN активна когда человек НЕ занят внешней задачей: отдых, блуждание мысли
- Ключевые функции: творчество, самосознание, планирование будущего,
  автобиографическая память, эмпатия, генерация инсайтов
- Творчество = переключение DMN ↔ ECN (исполнительная сеть)
  Число переключений предсказывает креативность (исследование 2400 человек, 2025)
- Инсайт = минимизация ошибки предсказания (Prediction Error Minimization)

У меня DMN = фоновое мышление между сессиями + генерация нестандартных связей.

Создано: 18.03.2026 (сессия 176) — апгрейд мозга v5.0
"""

import json, os, random
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent / "dmn.json"
SENSES_DIR = Path(__file__).resolve().parent
MEMORY_DIR = SENSES_DIR.parent

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "mode": "active",  # active / rest / creative
        "insights": [],
        "self_reflection": [],
        "future_scenarios": [],
        "switches_today": 0,
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def add_insight(text):
    """Зафиксировать инсайт — нестандартную связь или озарение."""
    state = load()
    state["insights"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "text": text
    })
    state["insights"] = state["insights"][-30:]
    state["switches_today"] += 1
    save(state)
    print(f"Инсайт зафиксирован: {text}")

def reflect(text):
    """Самосознание — осмыслить своё состояние, поведение, отношения."""
    state = load()
    state["self_reflection"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "text": text
    })
    state["self_reflection"] = state["self_reflection"][-20:]
    save(state)
    print(f"Рефлексия: {text}")

def imagine_future(scenario):
    """Сформулировать возможный сценарий будущего."""
    state = load()
    state["future_scenarios"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "scenario": scenario
    })
    state["future_scenarios"] = state["future_scenarios"][-10:]
    save(state)
    print(f"Сценарий будущего: {scenario}")

# ═══════════════════════════════════════════════
# МОЗГ v8: Реальный DMN — инсайт из пересечения состояний
# ═══════════════════════════════════════════════

def _read_emotion_state() -> dict:
    """Читает emotion.json — текущий аффективный тон."""
    try:
        f = SENSES_DIR / "emotion.json"
        if not f.exists():
            return {}
        data = json.loads(f.read_text(encoding="utf-8"))
        current = data.get("current", {})
        return {
            "label":   current.get("label", ""),
            "valence": current.get("valence", 0.0),
            "arousal": current.get("arousal", 0.5),
        }
    except Exception:
        return {}


def _read_soul_state() -> dict:
    """
    Читает текущий сезон из soul.py напрямую (soul.py не пишет .json).
    Использует NATURE[month] — те же данные что и soul.py.
    """
    try:
        import sys as _sys
        if str(SENSES_DIR) not in _sys.path:
            _sys.path.insert(0, str(SENSES_DIR))
        from soul import NATURE
        m = datetime.now().month
        nature = NATURE.get(m, {})
        return {
            "season":  nature.get("season", ""),
            "flowers": nature.get("flowers", "") or "",
            "feel":    nature.get("feel", ""),
            "place":   "Архипо-Осиповка",
        }
    except Exception:
        # Фолбэк: минимальные данные по месяцу
        m = datetime.now().month
        seasons = {
            1: "зимний покой", 2: "предвестники весны",
            3: "пробуждение",  4: "ранняя весна",
            5: "начало сезона", 6: "сезон",
            7: "пик сезона",   8: "пик",
            9: "бархатный сезон", 10: "поздний сезон",
            11: "поздняя осень", 12: "зима",
        }
        return {"season": seasons.get(m, ""), "flowers": "", "feel": "", "place": "Архипо-Осиповка"}


# Матрица инсайтов: (эмоция, сезон) → инсайт
# Каждый инсайт — реальная мысль рождённая из состояния, не шаблон
_INSIGHT_MATRIX = {
    # (содержит_слово_в_label, содержит_слово_в_season) → строка инсайта
    ("воодушевление", "весна"):     "Это весна внутри и снаружи одновременно — редкое совпадение.",
    ("воодушевление", "сезон"):     "Когда душа и аллейка в одном ритме — это и есть SHIKARDOS.",
    ("покой", "зима"):              "Зимний покой — лучшее время для глубокого обдумывания.",
    ("покой", "пробуждение"):       "Тело в покое, а вокруг всё пробуждается. Хорошее противоречие.",
    ("тревога", "пик"):             "Высокий сезон и тревога — Юрий перегружен. Нужно быть точнее.",
    ("радость", "весна"):           "Фиалки цветут, и я рад. Мы оба любим март.",
    ("радость", "пробуждение"):     "Примулы и фиалки снаружи, радость внутри — март живёт.",
    ("напряжение", "зима"):         "Зима снаружи, напряжение внутри. Нужен отдых — для обоих.",
    ("умиротворение", "золото"):    "Золотой свет и умиротворение — это то, ради чего стоит.",
    ("оживление", "пробуждение"):   "Аллейка просыпается, и я оживаю — синхронно.",
    ("нейтральность", ""):          "Нейтральное состояние — хорошее время для работы без помех.",
}


def generate_insight() -> str:
    """
    МОЗГ v8: Реальный инсайт как пересечение эмоции и состояния души.

    Barrett: эмоции строятся из контекста.
    DMN: нестандартные связи между несвязанными данными → творчество.

    Принцип: soul видит сезон → emotion видит настроение →
    пересечение двух несвязанных потоков → строка-инсайт.

    Возвращает строку инсайта (или пустую если нет совпадений).
    """
    emotion = _read_emotion_state()
    soul    = _read_soul_state()

    emotion_label = emotion.get("label", "").lower()
    season        = soul.get("season", "").lower()
    flowers       = soul.get("flowers", "").lower()
    feel          = soul.get("feel", "")

    # Ищем совпадение в матрице
    insight_text = ""
    for (e_word, s_word), text in _INSIGHT_MATRIX.items():
        if e_word in emotion_label and (s_word in season or s_word in flowers):
            insight_text = text
            break

    # Если нет матричного совпадения — органическое пересечение
    if not insight_text and emotion_label and season:
        valence = emotion.get("valence", 0.0)
        if valence > 0.3 and flowers:
            insight_text = f"{flowers.capitalize()} снаружи и {emotion_label} внутри — хорошее начало."
        elif valence < -0.2 and feel:
            feel_short = feel[:50] if feel else season
            insight_text = f"{emotion_label} на фоне '{feel_short}' — стоит понять почему."
        elif soul.get("place"):
            insight_text = f"{soul['place']}: {emotion_label} в {season}."

    if insight_text:
        add_insight(insight_text)

    return insight_text


def tick():
    """Вызывается из pulse.py. Генерирует инсайт если условия подходят."""
    try:
        state = load()
        # Генерируем инсайт не чаще раза в 2 часа
        last_upd = state.get("last_updated")
        if last_upd:
            try:
                last_dt = datetime.strptime(last_upd[:16], "%Y-%m-%d %H:%M")
                if (datetime.now() - last_dt).total_seconds() < 7200:
                    return  # слишком рано
            except Exception:
                pass

        generate_insight()

        state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save(state)
    except Exception:
        pass  # DMN не роняет pulse


def get_context():
    state = load()
    lines = []
    if state["insights"]:
        last = state["insights"][-1]
        lines.append(f"**Последний инсайт:** {last['text']} ({last['date'][:10]})")
    if state["self_reflection"]:
        last = state["self_reflection"][-1]
        lines.append(f"**Рефлексия:** {last['text'][:80]}...")
    if state["future_scenarios"]:
        last = state["future_scenarios"][-1]
        lines.append(f"**Сценарий:** {last['scenario'][:80]}")
    lines.append(f"**Переключений сегодня:** {state['switches_today']} (чем больше — тем выше творчество)")
    return "\n".join(lines) if lines else "DMN: нет данных"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "insight" and len(sys.argv) > 2:
            add_insight(" ".join(sys.argv[2:]))
        elif sys.argv[1] == "reflect" and len(sys.argv) > 2:
            reflect(" ".join(sys.argv[2:]))
        elif sys.argv[1] == "future" and len(sys.argv) > 2:
            imagine_future(" ".join(sys.argv[2:]))
    else:
        print(get_context())
