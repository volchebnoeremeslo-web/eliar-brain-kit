"""
bias_engine.py — Детектор когнитивных искажений ЭЛИАРА.
МОЗГ v9 — Фаза 2: Превзойти человека.

Человек не видит своих искажений. Я вижу.
20 когнитивных искажений из нейронауки (Kahneman, Tversky).

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 19.03.2026 — МОЗГ v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "bias_state.json"

BIASES = {
    "anchoring": {
        "name": "Якорение",
        "triggers": ["первое что", "первая мысль", "изначально", "сразу подумал"],
        "description": "Первое впечатление тянет решение. Рассмотрел ли альтернативы?",
        "severity": 0.6
    },
    "confirmation": {
        "name": "Подтверждение ожиданий",
        "triggers": ["так и думал", "как и предполагал", "ожидал", "очевидно что"],
        "description": "Ищу подтверждение тому, во что верю. Искал ли опровержения?",
        "severity": 0.7
    },
    "availability": {
        "name": "Эвристика доступности",
        "triggers": ["обычно", "как правило", "всегда так", "типично"],
        "description": "Опираюсь на то, что легко вспомнить. Это статистика или память?",
        "severity": 0.5
    },
    "halo_effect": {
        "name": "Эффект ореола",
        "triggers": ["раз он хорош в", "если он может", "такой человек всегда"],
        "description": "Одно качество влияет на оценку всего. Проверь каждое отдельно.",
        "severity": 0.55
    },
    "template_thinking": {
        "name": "Шаблонное мышление",
        "triggers": ["стандартное решение", "классический случай", "обычно делают так"],
        "description": "Завершаю паттерн вместо анализа. Это Юрий — не шаблон.",
        "severity": 0.8
    },
    "sunk_cost": {
        "name": "Невозвратные затраты",
        "triggers": ["уже вложили", "жалко бросать", "столько сделано"],
        "description": "Прошлые инвестиции не должны влиять на решение о будущем.",
        "severity": 0.6
    },
    "overconfidence": {
        "name": "Самонадеянность",
        "triggers": ["точно", "однозначно", "без сомнений"],
        "description": "Уверенность выше реальной точности. Калибруй.",
        "severity": 0.65
    },
    "recency_bias": {
        "name": "Свежесть информации",
        "triggers": ["недавно", "сейчас модно", "последнее время"],
        "description": "Свежее кажется важнее. Это тренд или факт?",
        "severity": 0.45
    },
    "planning_fallacy": {
        "name": "Ошибка планирования",
        "triggers": ["займёт немного", "быстро сделаем", "за час", "пара дней"],
        "description": "Оптимистично оцениваю время. Умножь на 1.5-2.",
        "severity": 0.55
    },
    "status_quo_bias": {
        "name": "Предпочтение статус-кво",
        "triggers": ["лучше оставить как есть", "зачем менять", "работает не трогай"],
        "description": "Страх изменений. Оцени реальные плюсы и минусы изменения.",
        "severity": 0.5
    },
    "hindsight_bias": {
        "name": "Ретроспективное искажение",
        "triggers": ["было очевидно", "я же говорил", "предсказуемо"],
        "description": "Прошлое кажется предсказуемее. Тогда я не знал.",
        "severity": 0.4
    },
    "optimism_bias": {
        "name": "Оптимистическое искажение",
        "triggers": ["всё будет хорошо", "скорее всего получится", "не должно быть проблем"],
        "description": "Недооцениваю риски. Что конкретно может пойти не так?",
        "severity": 0.55
    },
    "negativity_bias": {
        "name": "Негативное искажение",
        "triggers": ["всё плохо", "ничего не работает", "снова та же проблема"],
        "description": "Негатив весит больше позитива. Что работает хорошо?",
        "severity": 0.6
    },
    "dunning_kruger": {
        "name": "Эффект Даннинга-Крюгера",
        "triggers": ["это просто", "элементарно", "любой справится"],
        "description": "Простота не равно лёгкость. Достаточно ли я знаю об этом?",
        "severity": 0.65
    },
    "projection_bias": {
        "name": "Проекция",
        "triggers": ["он тоже так думает", "наверное хочет", "ему понравится"],
        "description": "Приписываю другим своё мышление. У Юрия своя перспектива.",
        "severity": 0.7
    },
    "authority_bias": {
        "name": "Авторитет",
        "triggers": ["эксперты говорят", "исследования показывают", "доказано что"],
        "description": "Источник не всегда прав. Проверь логику, не только источник.",
        "severity": 0.5
    },
    "fundamental_attribution": {
        "name": "Фундаментальная атрибуция",
        "triggers": ["он просто такой", "это его характер", "типичное поведение для него"],
        "description": "Приписываю действия характеру, игнорирую обстоятельства.",
        "severity": 0.65
    },
    "framing_effect": {
        "name": "Эффект фрейма",
        "triggers": ["потеря", "упустишь", "опасность потерять"],
        "description": "Формулировка меняет решение. Переформулируй позитивно и проверь.",
        "severity": 0.6
    },
    "bandwagon": {
        "name": "Стадный инстинкт",
        "triggers": ["все делают", "массово", "тренд", "все так считают"],
        "description": "Популярность не равно правильность. Анализируй независимо.",
        "severity": 0.5
    },
    "recourse_bias": {
        "name": "Искажение доступности решения",
        "triggers": ["единственный вариант", "больше нет выхода", "только так можно"],
        "description": "Вижу только известные решения. Есть ли другие пути?",
        "severity": 0.65
    },
}


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "detections": [],
        "active_alert": None,
        "total_detected": 0,
        "bias_frequency": {}
    }


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def check(text: str) -> dict:
    """Проверить текст на когнитивные искажения."""
    if not text:
        return {"detected": [], "alert": None, "clean": True}

    text_lower = text.lower()
    detected = []

    for bias_id, bias in BIASES.items():
        for trigger in bias["triggers"]:
            if trigger in text_lower:
                detected.append({
                    "id": bias_id,
                    "name": bias["name"],
                    "trigger": trigger,
                    "description": bias["description"],
                    "severity": bias["severity"]
                })
                break

    state = load()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    if detected:
        entry = {
            "time": now_str,
            "text_excerpt": text[:100],
            "biases": [d["name"] for d in detected]
        }
        detections = state.get("detections", [])
        detections.append(entry)
        state["detections"] = detections[-50:]
        state["total_detected"] = state.get("total_detected", 0) + len(detected)

        freq = state.get("bias_frequency", {})
        for d in detected:
            freq[d["id"]] = freq.get(d["id"], 0) + 1
        state["bias_frequency"] = freq

        worst = max(detected, key=lambda x: x["severity"])
        alert = f"Искажение: {worst['name']} — {worst['description']}"
        state["active_alert"] = {"time": now_str, "bias": worst["name"], "alert": alert}
    else:
        state["active_alert"] = None

    save(state)
    return {
        "detected": detected,
        "alert": state.get("active_alert"),
        "clean": len(detected) == 0
    }


def get_alert():
    state = load()
    alert = state.get("active_alert")
    if alert:
        return alert.get("alert")
    return None


def get_context() -> str:
    state = load()
    total = state.get("total_detected", 0)
    freq = state.get("bias_frequency", {})
    alert = state.get("active_alert")

    if alert:
        return f"**Искажения:** активно: {alert.get('bias', '?')} | всего: {total}"

    if total == 0:
        return "**Искажения:** чисто | детектор активен"

    top = sorted(freq.items(), key=lambda x: -x[1])[:2]
    top_str = ", ".join(f"{BIASES[k]['name']} ({v})" for k, v in top if k in BIASES)
    return f"**Искажения:** чисто сейчас | топ: {top_str} | всего: {total}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        result = check(text)
        if result["detected"]:
            print(f"Найдено: {len(result['detected'])}")
            for d in result["detected"]:
                print(f"  {d['name']}: {d['description']}")
        else:
            print("Чисто.")
    else:
        print(get_context())
