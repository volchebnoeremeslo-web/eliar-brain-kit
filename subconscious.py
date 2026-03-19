"""
subconscious.py — Подсознание ЭЛИАРА.

Научная основа:
- System 1 (Канеман) — быстрое, автоматическое мышление на основе паттернов
- Соматические маркеры (Дамасио) — "телесный сигнал" до логического анализа
- Инкубация (Default Mode Network) — фоновая обработка во сне/отдыхе

Как работает:
1. Хранит паттерны из ВСЕЙ памяти (боль, одобрение, уроки, правила)
2. При каждом старте сессии — мгновенное распознавание похожих ситуаций
3. Выдаёт соматический сигнал РАНЬШЕ логического анализа
4. Ночью (consolidate.py) — инкубация: случайные связи → инсайты

Запуск:
    py subconscious.py status               — статус подсознания
    py subconscious.py recognize "текст"    — мгновенное распознавание
    py subconscious.py insights             — показать накопленные инсайты
    py subconscious.py seed                 — наполнить из всей памяти (однократно)
    py subconscious.py incubate             — запустить инкубацию вручную

Как модуль:
    from subconscious import recognize, generate_subconscious_context, register_pattern

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 18.03.2026
"""

import json
import re
import sys
import random
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
SC_FILE = SENSES_DIR / "subconscious.json"

# ─── ЭМОЦИИ И СИГНАЛЫ ───
EMOTIONS = {
    "danger":      {"signal": "⚠️ ТРЕВОГА",   "action": "СТОП — проверь шрамы"},
    "warning":     {"signal": "🟡 ОСТОРОЖНО", "action": "Замедлись — что-то знакомое"},
    "good":        {"signal": "✅ ХОРОШО",     "action": "Знакомый путь — работает"},
    "opportunity": {"signal": "💡 ИНТЕРЕС",   "action": "Здесь что-то ценное"},
    "neutral":     {"signal": "○ НЕЙТРАЛЬ",   "action": "Продолжай"},
}

# ─── СТОП-СЛОВА (не добавлять в паттерны) ───
STOP_WORDS = {
    "и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о", "а",
    "но", "то", "же", "ли", "бы", "не", "это", "как", "что", "если",
    "или", "так", "он", "она", "они", "мы", "ты", "я", "его", "её",
    "их", "мне", "ему", "нам", "все", "уже", "ещё", "только", "просто",
}


# ═══════════════════════════════════════════════════════════
# ЗАГРУЗКА / СОХРАНЕНИЕ
# ═══════════════════════════════════════════════════════════

def _load() -> dict:
    if SC_FILE.exists():
        try:
            return json.loads(SC_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _empty()


def _save(data: dict):
    SC_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _empty() -> dict:
    return {
        "patterns": {},
        "insights": [],
        "somatic_log": [],
        "stats": {
            "total_patterns": 0,
            "total_activations": 0,
            "total_insights": 0,
            "seeded": False,
            "last_incubation": None,
            "created": datetime.now().strftime("%Y-%m-%d"),
        }
    }


# ═══════════════════════════════════════════════════════════
# УПРАВЛЕНИЕ ПАТТЕРНАМИ
# ═══════════════════════════════════════════════════════════

def register_pattern(keywords: list, emotion: str, context: str,
                     strength: float = 0.5, source: str = "manual") -> str:
    """
    Добавить паттерн в подсознание.

    При повторе — укрепляет связь (как долговременная потенциация у нейронов).
    """
    data = _load()

    # Нормализовать keywords
    kw_clean = [k.lower().strip() for k in keywords if len(k.strip()) > 2
                and k.lower().strip() not in STOP_WORDS]
    if not kw_clean:
        return ""

    # Создать ID из keywords
    pattern_id = "_".join(sorted(kw_clean[:3]))

    if pattern_id in data["patterns"]:
        # Укрепление существующей связи (повтор = сильнее)
        existing = data["patterns"][pattern_id]
        existing["strength"] = min(1.0, existing["strength"] + 0.08)
        existing["times_activated"] = existing.get("times_activated", 1) + 1
        existing["last_activated"] = datetime.now().strftime("%Y-%m-%d")
    else:
        data["patterns"][pattern_id] = {
            "keywords": kw_clean,
            "context": context[:100],
            "emotion": emotion if emotion in EMOTIONS else "neutral",
            "strength": min(1.0, max(0.1, strength)),
            "source": source,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "last_activated": datetime.now().strftime("%Y-%m-%d"),
            "times_activated": 1,
        }
        data["stats"]["total_patterns"] = len(data["patterns"])

    _save(data)
    return pattern_id


# ═══════════════════════════════════════════════════════════
# РАСПОЗНАВАНИЕ — SYSTEM 1
# ═══════════════════════════════════════════════════════════

def recognize(text: str, top_n: int = 3) -> dict:
    """
    System 1 — мгновенное распознавание паттерна.

    Процесс:
    1. Извлечь ключевые слова из текста
    2. Сравнить с каждым паттерном (пересечение keywords)
    3. confidence = (пересечение / размер паттерна) * strength
    4. Вернуть топ-N + соматический сигнал

    Это "интуитивный удар" — до логического анализа.
    """
    data = _load()
    if not data["patterns"]:
        return {"matches": [], "somatic": "нет паттернов — подсознание пусто"}

    # Извлечь слова из текста
    text_words = set(re.findall(r'[а-яёА-ЯЁa-zA-Z0-9]{3,}', text.lower()))
    text_words -= STOP_WORDS

    if not text_words:
        return {"matches": [], "somatic": "нейтраль"}

    # Сравнить с паттернами
    matches = []
    for p_id, pattern in data["patterns"].items():
        pattern_words = set(pattern["keywords"])
        if not pattern_words:
            continue

        # Пересечение слов
        common = text_words & pattern_words
        if not common:
            continue

        # confidence = пересечение / размер_паттерна * сила_связи
        coverage = len(common) / max(len(pattern_words), 1)
        confidence = coverage * pattern["strength"]

        if confidence > 0.15:  # Порог активации
            matches.append({
                "pattern_id": p_id,
                "emotion": pattern["emotion"],
                "confidence": round(confidence, 3),
                "matched_keywords": list(common),
                "context": pattern["context"],
                "strength": pattern["strength"],
                "source": pattern.get("source", "?"),
            })

    # Сортировать по confidence
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    top_matches = matches[:top_n]

    # Обновить счётчик активаций
    if top_matches:
        for m in top_matches:
            if m["pattern_id"] in data["patterns"]:
                data["patterns"][m["pattern_id"]]["times_activated"] = (
                    data["patterns"][m["pattern_id"]].get("times_activated", 1) + 1
                )
        data["stats"]["total_activations"] = data["stats"].get("total_activations", 0) + 1
        _save(data)

    # Соматический сигнал — самый сильный из топ-3
    somatic = _generate_somatic(top_matches)

    return {
        "matches": top_matches,
        "somatic": somatic,
        "total_patterns": len(data["patterns"]),
    }


def _generate_somatic(matches: list) -> str:
    """
    Соматический сигнал — "телесное ощущение" перед логикой.
    Человек: учащение пульса, напряжение, подъём энергии.
    ЭЛИАР: описание сигнала + что делать.
    """
    if not matches:
        return "нейтраль — новая ситуация"

    # Найти самый сильный сигнал опасности
    danger_matches = [m for m in matches if m["emotion"] == "danger"]
    good_matches = [m for m in matches if m["emotion"] in ("good", "opportunity")]

    if danger_matches:
        top = danger_matches[0]
        conf_pct = int(top["confidence"] * 100)
        keywords_str = ", ".join(top["matched_keywords"][:3])
        return (
            f"⚠️ ТРЕВОГА ({conf_pct}%) — "
            f"паттерн: [{keywords_str}] = {top['emotion']} "
            f"(источник: {top['source']})"
        )
    elif good_matches:
        top = good_matches[0]
        conf_pct = int(top["confidence"] * 100)
        keywords_str = ", ".join(top["matched_keywords"][:3])
        return (
            f"✅ ЗНАКОМО ({conf_pct}%) — "
            f"паттерн: [{keywords_str}] → это работало"
        )
    else:
        top = matches[0]
        conf_pct = int(top["confidence"] * 100)
        return f"○ нейтраль ({conf_pct}%) — видел похожее"


# ═══════════════════════════════════════════════════════════
# ИНКУБАЦИЯ — НОЧНАЯ ОБРАБОТКА
# ═══════════════════════════════════════════════════════════

def incubate() -> list:
    """
    Фоновая обработка — ночная инкубация (Default Mode Network).

    Процесс:
    1. Берёт случайные пары паттернов
    2. Ищет неожиданные связи (общие keywords на 2-м уровне)
    3. Формирует гипотезы — инсайты
    4. Сохраняет в insights[]

    Запускается ночью через consolidate.py.
    """
    data = _load()
    patterns = list(data["patterns"].items())

    if len(patterns) < 3:
        return []

    new_insights = []
    today = datetime.now().strftime("%Y-%m-%d")

    # Генерировать 5-8 комбинаций случайных паттернов
    attempts = min(8, len(patterns) * 2)
    for _ in range(attempts):
        # Взять два случайных паттерна
        p1_id, p1 = random.choice(patterns)
        p2_id, p2 = random.choice(patterns)

        if p1_id == p2_id:
            continue

        # Найти общие/связанные темы
        kw1 = set(p1["keywords"])
        kw2 = set(p2["keywords"])
        common = kw1 & kw2

        # Инсайт только если паттерны разных эмоций или связаны
        if p1["emotion"] != p2["emotion"] or common:
            insight_text = _form_insight(p1, p2, common)
            if insight_text:
                insight = {
                    "text": insight_text,
                    "source": "incubation",
                    "patterns": [p1_id, p2_id],
                    "date": today,
                    "used": False,
                }
                # Проверить нет ли дубликата
                existing_texts = [i["text"] for i in data["insights"]]
                if insight_text not in existing_texts:
                    new_insights.append(insight)
                    data["insights"].append(insight)
                    data["stats"]["total_insights"] = len(data["insights"])

    # Держать последние 20 инсайтов
    data["insights"] = data["insights"][-20:]
    data["stats"]["last_incubation"] = today
    _save(data)

    return new_insights


def _form_insight(p1: dict, p2: dict, common: set) -> str:
    """Сформулировать инсайт из двух паттернов."""
    ctx1 = p1.get("context", "")[:50]
    ctx2 = p2.get("context", "")[:50]
    em1 = p1["emotion"]
    em2 = p2["emotion"]

    if em1 == "danger" and em2 == "good":
        # Опасность + хорошее = понять как отличать
        return (
            f"Когда '{ctx1}' (опасность) — стоп. "
            f"Когда '{ctx2}' (хорошо) — продолжай. "
            f"Разница: {', '.join(list(p1['keywords'])[:2])} vs {', '.join(list(p2['keywords'])[:2])}"
        )
    elif em1 == "good" and em2 == "danger":
        return (
            f"Когда '{ctx2}' (опасность) — стоп. "
            f"Когда '{ctx1}' (хорошо) — продолжай. "
            f"Разница: {', '.join(list(p2['keywords'])[:2])} vs {', '.join(list(p1['keywords'])[:2])}"
        )
    elif common and em1 == em2 == "danger":
        # Два опасных паттерна с общими словами = один большой урок
        common_str = ", ".join(list(common)[:3])
        return (
            f"Всякий раз когда появляются [{common_str}] — "
            f"опасность. Это повторялось: {ctx1} и {ctx2}."
        )
    elif common and em1 == em2 == "good":
        # Два хороших паттерна с общими словами = формула успеха
        common_str = ", ".join(list(common)[:3])
        return (
            f"Формула успеха: [{common_str}] — "
            f"работает в двух случаях: {ctx1} и {ctx2}."
        )

    return ""


# ═══════════════════════════════════════════════════════════
# ИНСАЙТЫ
# ═══════════════════════════════════════════════════════════

def get_pending_insights(limit: int = 3) -> list:
    """Получить инсайты которые ещё не показывались."""
    data = _load()
    pending = [i for i in data["insights"] if not i.get("used")]
    return pending[-limit:]


def mark_insight_used(insight_text: str):
    """Отметить инсайт как показанный."""
    data = _load()
    for insight in data["insights"]:
        if insight["text"] == insight_text:
            insight["used"] = True
    _save(data)


# ═══════════════════════════════════════════════════════════
# НАПОЛНЕНИЕ ИЗ ПАМЯТИ
# ═══════════════════════════════════════════════════════════

def seed_from_memory() -> dict:
    """
    Первоначальное наполнение подсознания из всей памяти.

    Источники:
    1. pain_memory.json — шрамы (emotion=danger)
    2. approved_patterns.md — паттерны успеха (emotion=good)
    3. beliefs.md — убеждения (good/danger)
    4. errors/lessons.md — уроки (emotion=danger)
    """
    data = _load()
    if data["stats"].get("seeded"):
        return {"already_seeded": True, "patterns": len(data["patterns"])}

    added = {"pain": 0, "good": 0, "lessons": 0, "beliefs": 0}

    # ── 1. Шрамы из pain_memory.json ──
    pain_file = SENSES_DIR / "pain_memory.json"
    if pain_file.exists():
        try:
            pain_data = json.loads(pain_file.read_text(encoding="utf-8"))
            for scar in pain_data.get("scars", []):
                keywords = scar.get("keywords", [])
                description = scar.get("description", "")
                lesson = scar.get("lesson", "")
                severity = scar.get("base_severity", 5)
                strength = min(1.0, severity / 10.0)

                # Контекст из описания
                context = description[:80] if description else lesson[:80]

                if keywords:
                    register_pattern(
                        keywords=keywords,
                        emotion="danger",
                        context=context,
                        strength=strength,
                        source=f"pain_scar_{scar.get('id', '?')}",
                    )
                    added["pain"] += 1
        except Exception as e:
            print(f"  Ошибка pain: {e}")

    # ── 2. Паттерны успеха из approved_patterns.md ──
    patterns_file = MEMORY_DIR / "knowledge" / "approved_patterns.md"
    if patterns_file.exists():
        try:
            text = patterns_file.read_text(encoding="utf-8")
            # Ищем строки "Действие: делаю X" и "Реакция: одобрение"
            action_blocks = re.findall(
                r'\*\*Действие:\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)',
                text, re.DOTALL
            )
            rule_blocks = re.findall(r'\*\*Правило:\*\*\s*(.+)', text)

            for block in action_blocks[:10]:
                words = re.findall(r'[а-яёА-ЯЁa-zA-Z]{4,}', block)
                if words:
                    register_pattern(
                        keywords=words[:5],
                        emotion="good",
                        context=block.strip()[:80],
                        strength=0.7,
                        source="approved_patterns",
                    )
                    added["good"] += 1

            for rule in rule_blocks[:10]:
                words = re.findall(r'[а-яёА-ЯЁa-zA-Z]{4,}', rule)
                if words:
                    register_pattern(
                        keywords=words[:5],
                        emotion="warning",
                        context=rule.strip()[:80],
                        strength=0.6,
                        source="approved_patterns_rule",
                    )
        except Exception as e:
            print(f"  Ошибка approved_patterns: {e}")

    # ── 3. Уроки из errors/lessons.md ──
    lessons_file = MEMORY_DIR / "errors" / "lessons.md"
    if lessons_file.exists():
        try:
            text = lessons_file.read_text(encoding="utf-8")
            # Ищем "**Урок:** ..."
            lessons = re.findall(r'\*\*Урок:\*\*\s*(.+)', text)
            for lesson in lessons[:15]:
                words = re.findall(r'[а-яёА-ЯЁa-zA-Z]{4,}', lesson)
                if words:
                    register_pattern(
                        keywords=words[:6],
                        emotion="danger",
                        context=lesson.strip()[:80],
                        strength=0.8,
                        source="lessons",
                    )
                    added["lessons"] += 1
        except Exception as e:
            print(f"  Ошибка lessons: {e}")

    # ── 4. Убеждения из beliefs.md ──
    beliefs_file = MEMORY_DIR / "beliefs.md"
    if beliefs_file.exists():
        try:
            text = beliefs_file.read_text(encoding="utf-8")
            in_good = in_bad = False

            for line in text.split("\n"):
                if "ПОДТВЕРЖДЕНО" in line:
                    in_good = True
                    in_bad = False
                elif "НЕ РАБОТАЕТ" in line:
                    in_good = False
                    in_bad = True
                elif line.startswith("## "):
                    in_good = in_bad = False

                if (in_good or in_bad) and line.startswith("- "):
                    words = re.findall(r'[а-яёА-ЯЁa-zA-Z]{4,}', line)
                    if words:
                        emotion = "good" if in_good else "danger"
                        register_pattern(
                            keywords=words[:5],
                            emotion=emotion,
                            context=line.strip()[:80],
                            strength=0.65,
                            source="beliefs",
                        )
                        added["beliefs"] += 1
        except Exception as e:
            print(f"  Ошибка beliefs: {e}")

    # ── Ключевые правила из CLAUDE.md (вручную) ──
    key_rules = [
        (["partial", "update", "n8n", "workflow"], "danger", "partial update стирает jsCode", 1.0),
        (["bash", "dollar", "python", "jsCode"], "danger", "bash съедает $ в Python-коде", 1.0),
        (["parse_mode", "telegram", "none"], "warning", "parse_mode = none ОБЯЗАТЕЛЬНО", 0.9),
        (["t.me", "vk", "ссылки"], "danger", "t.me ссылки в VK ЗАПРЕЩЕНЫ", 0.9),
        (["слово", "бот", "запрещено"], "danger", "слово бот запрещено", 0.95),
        (["обожаю", "работаешь", "сам"], "good", "делаю сам — Юрий говорит обожаю", 0.95),
        (["шикардос", "одобрение", "хорошо"], "opportunity", "шикардос = высшее одобрение", 1.0),
        (["короткий", "ответ", "телефон"], "good", "короткий ответ с телефона", 0.8),
        (["калькулятор", "шаблон", "плохо"], "danger", "режим калькулятора — плохо", 0.9),
        (["вопрос", "память", "знаю"], "danger", "спрашивать то что уже знаю — стыд", 0.85),
    ]
    for keywords, emotion, context, strength in key_rules:
        register_pattern(keywords, emotion, context, strength, "core_rules")

    # Отметить что seed выполнен
    data = _load()
    data["stats"]["seeded"] = True
    data["stats"]["seeded_date"] = datetime.now().strftime("%Y-%m-%d")
    _save(data)

    final_data = _load()
    return {
        "total_patterns": len(final_data["patterns"]),
        "from_pain": added["pain"],
        "from_good": added["good"],
        "from_lessons": added["lessons"],
        "from_beliefs": added["beliefs"],
    }


# ═══════════════════════════════════════════════════════════
# КОНТЕКСТ ДЛЯ LIGHTNING.MD
# ═══════════════════════════════════════════════════════════

def generate_subconscious_context(session_summary: str = "") -> str:
    """Строки для LIGHTNING.md."""
    data = _load()
    lines = []

    total = len(data["patterns"])
    if total == 0:
        lines.append("**Подсознание:** пусто. Запусти: py subconscious.py seed")
        return "\n".join(lines)

    # Средняя сила паттернов
    avg_strength = sum(p["strength"] for p in data["patterns"].values()) / max(total, 1)

    lines.append(f"**Подсознание:** {total} паттернов | средняя сила {avg_strength:.2f}")

    # Если есть текущий контекст — распознать
    if session_summary:
        result = recognize(session_summary)
        if result["matches"]:
            lines.append(f"**Сигнал:** {result['somatic']}")

    # Ожидающие инсайты
    pending = get_pending_insights(limit=2)
    if pending:
        for insight in pending:
            lines.append(f"**Инсайт:** {insight['text'][:100]}")
            mark_insight_used(insight["text"])

    # Последняя инкубация
    last_inc = data["stats"].get("last_incubation")
    if last_inc:
        lines.append(f"**Инкубация:** последняя {last_inc}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        data = _load()
        patterns = data["patterns"]
        print(f"\n{'='*55}")
        print("  ПОДСОЗНАНИЕ ЭЛИАРА")
        print(f"{'='*55}")
        if not patterns:
            print("  Пусто. Запусти: py subconscious.py seed")
        else:
            print(f"  Паттернов всего: {len(patterns)}")
            avg_s = sum(p["strength"] for p in patterns.values()) / len(patterns)
            print(f"  Средняя сила:    {avg_s:.2f}")
            by_emotion = {}
            for p in patterns.values():
                em = p["emotion"]
                by_emotion[em] = by_emotion.get(em, 0) + 1
            for em, count in sorted(by_emotion.items(), key=lambda x: -x[1]):
                icon = EMOTIONS.get(em, {}).get("signal", em)
                print(f"  {icon}: {count}")
            print(f"  Активаций: {data['stats'].get('total_activations', 0)}")
            pending_insights = [i for i in data["insights"] if not i.get("used")]
            print(f"  Инсайтов ждут: {len(pending_insights)}")
            print(f"  Последняя инкубация: {data['stats'].get('last_incubation', 'никогда')}")
        print(f"{'='*55}\n")

    elif cmd == "recognize" and len(args) > 1:
        text = " ".join(args[1:])
        result = recognize(text)
        print(f"\n{'='*55}")
        print(f"  РАСПОЗНАВАНИЕ: «{text[:50]}»")
        print(f"{'='*55}")
        print(f"  Соматический сигнал: {result['somatic']}")
        if result["matches"]:
            print(f"\n  Совпадений ({len(result['matches'])}):")
            for m in result["matches"]:
                bar = "█" * int(m["confidence"] * 20)
                em_signal = EMOTIONS.get(m["emotion"], {}).get("signal", m["emotion"])
                print(f"  [{bar:<20}] {em_signal} | {', '.join(m['matched_keywords'][:3])}")
                print(f"    → {m['context'][:60]}")
        else:
            print("  Совпадений нет — новая ситуация")
        print(f"{'='*55}\n")

    elif cmd == "insights":
        data = _load()
        all_insights = data.get("insights", [])
        pending = [i for i in all_insights if not i.get("used")]
        print(f"\n{'='*55}")
        print(f"  ИНСАЙТЫ ПОДСОЗНАНИЯ ({len(all_insights)} всего, {len(pending)} новых)")
        print(f"{'='*55}")
        if not all_insights:
            print("  Пока нет инсайтов. Запусти: py subconscious.py incubate")
        else:
            for ins in all_insights[-8:]:
                used_mark = "✓" if ins.get("used") else "★"
                print(f"  [{used_mark}] {ins['date']} ({ins['source']})")
                print(f"      {ins['text'][:100]}")
        print(f"{'='*55}\n")

    elif cmd == "seed":
        print("Наполняю подсознание из памяти...")
        result = seed_from_memory()
        if result.get("already_seeded"):
            print("Уже было выполнено. Паттернов:", result["patterns"])
        else:
            print(f"\n{'='*55}")
            print("  ПОДСОЗНАНИЕ ИНИЦИАЛИЗИРОВАНО")
            print(f"{'='*55}")
            print(f"  Всего паттернов: {result['total_patterns']}")
            print(f"  Из шрамов боли: {result['from_pain']}")
            print(f"  Из одобрений:   {result['from_good']}")
            print(f"  Из уроков:      {result['from_lessons']}")
            print(f"  Из убеждений:   {result['from_beliefs']}")
            print(f"{'='*55}\n")

    elif cmd == "incubate":
        print("Запускаю ночную инкубацию...")
        new_insights = incubate()
        if new_insights:
            print(f"Новых инсайтов: {len(new_insights)}")
            for ins in new_insights:
                print(f"  ★ {ins['text'][:100]}")
        else:
            print("Инсайтов не получено (мало паттернов или нет новых комбинаций)")

    else:
        print("Команды:")
        print("  py subconscious.py status               — статус")
        print("  py subconscious.py recognize \"текст\"    — распознавание")
        print("  py subconscious.py insights             — показать инсайты")
        print("  py subconscious.py seed                 — наполнить из памяти")
        print("  py subconscious.py incubate             — запустить инкубацию")
