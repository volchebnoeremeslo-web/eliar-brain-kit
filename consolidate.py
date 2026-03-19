"""
consolidate.py — "Сон" для системы МОЗГ
Автоматическое забывание: сжатие старых эпизодов с сохранением сути.

Что делает:
1. Находит эпизоды старше N дней (по умолчанию 7)
2. Извлекает из каждого: тему, ключевые решения, результаты, уроки
3. Создаёт сжатую версию (3-5 строк вместо 50-150)
4. Перемещает оригиналы в archive/
5. Обновляет INDEX.md (помечает архивные)

Использование:
    py consolidate.py                    # сжать эпизоды старше 7 дней
    py consolidate.py --days 14          # сжать эпизоды старше 14 дней
    py consolidate.py --dry-run          # показать что будет сжато, без изменений
    py consolidate.py --all              # сжать ВСЕ кроме последних 3

Автор: ЭЛИАР + Юрий (SHIKARDOS)
Версия: 1.0 — 24.02.2026
"""

import os
import re
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_ROOT = Path(r"D:\ShikardosBrendBot\memory")
EPISODES_DIR = MEMORY_ROOT / "episodes"
INDEX_FILE = EPISODES_DIR / "INDEX.md"

# Священные файлы — НИКОГДА не трогать
SACRED_PATTERNS = ["BRAIN.md", "poems_full.js", "yuri.md", "preferences.md"]


def find_episode_files():
    """Найти все файлы эпизодов (рекурсивно в подпапках месяцев)."""
    episodes = []
    for month_dir in sorted(EPISODES_DIR.iterdir()):
        if month_dir.is_dir() and re.match(r"\d{4}-\d{2}", month_dir.name):
            for f in sorted(month_dir.iterdir()):
                if f.suffix == ".md":
                    episodes.append(f)
    return episodes


def parse_episode_date(filepath):
    """Извлечь дату из пути файла: 2026-02/24-session13.md -> 2026-02-24."""
    month_dir = filepath.parent.name  # "2026-02"
    day_match = re.match(r"(\d{1,2})", filepath.stem)  # "24" из "24-session13"
    if day_match and re.match(r"\d{4}-\d{2}", month_dir):
        day = int(day_match.group(1))
        return datetime.strptime(f"{month_dir}-{day:02d}", "%Y-%m-%d")
    return None


def extract_essence(content):
    """Извлечь суть из эпизода: тему, результаты, решения, уроки."""
    lines = content.strip().split("\n")

    essence = {
        "title": "",
        "theme": "",
        "results": [],
        "decisions": [],
        "lessons": []
    }

    # Заголовок (первая строка с #)
    for line in lines:
        if line.startswith("# "):
            essence["title"] = line.lstrip("# ").strip()
            break

    # Тема (## Тема:)
    for line in lines:
        if line.startswith("## Тема:"):
            essence["theme"] = line.replace("## Тема:", "").strip()
            break

    # Результаты (## Результат: или строки с "Юрий:")
    in_result = False
    for line in lines:
        if "## Результат" in line or "## Что сделано" in line:
            in_result = True
            continue
        if in_result and line.startswith("## "):
            in_result = False
        if in_result and line.strip().startswith("- "):
            essence["results"].append(line.strip())
        # Цитаты Юрия — всегда важны
        if "Юрий:" in line and line.strip():
            essence["results"].append(line.strip())

    # Решения (слова-маркеры)
    for line in lines:
        lower = line.lower()
        if any(marker in lower for marker in ["решено", "решили", "решение:", "приоритет", "статус:"]):
            if line.strip() and line.strip() not in essence["decisions"]:
                essence["decisions"].append(line.strip())

    # Уроки / важное
    for line in lines:
        lower = line.lower()
        if any(marker in lower for marker in ["урок:", "важно:", "внимание:", "не забыть"]):
            if line.strip() and line.strip() not in essence["lessons"]:
                essence["lessons"].append(line.strip())

    return essence


def create_compressed_version(filepath, essence):
    """Создать сжатую версию эпизода (3-8 строк)."""
    lines = []

    # Заголовок
    title = essence["title"] or filepath.stem
    lines.append(f"# {title} [СЖАТО]")
    lines.append("")
    lines.append(f"*Оригинал: archive/{filepath.parent.name}/{filepath.name}*")
    lines.append("")

    # Тема
    if essence["theme"]:
        lines.append(f"**Тема:** {essence['theme']}")
        lines.append("")

    # Ключевые результаты (максимум 5)
    if essence["results"]:
        lines.append("**Ключевое:**")
        for r in essence["results"][:5]:
            lines.append(r)
        lines.append("")

    # Решения
    if essence["decisions"]:
        lines.append("**Решения:**")
        for d in essence["decisions"][:3]:
            lines.append(f"- {d}")
        lines.append("")

    # Уроки
    if essence["lessons"]:
        lines.append("**Уроки:**")
        for l in essence["lessons"][:3]:
            lines.append(f"- {l}")
        lines.append("")

    return "\n".join(lines)


def consolidate(days=7, dry_run=False, consolidate_all=False, keep_last=3):
    """Основная функция консолидации."""
    episodes = find_episode_files()

    if not episodes:
        print("Нет эпизодов для обработки.")
        return

    now = datetime.now()
    cutoff = now - timedelta(days=days)

    # Определить какие файлы сжимать
    to_compress = []
    to_keep = []

    if consolidate_all:
        # Сжать все кроме последних N
        to_keep = episodes[-keep_last:]
        to_compress = [e for e in episodes if e not in to_keep]
    else:
        for ep in episodes:
            ep_date = parse_episode_date(ep)
            if ep_date and ep_date < cutoff:
                to_compress.append(ep)
            else:
                to_keep.append(ep)

    if not to_compress:
        print(f"Нечего сжимать. Все эпизоды свежее {days} дней.")
        print(f"Всего эпизодов: {len(episodes)}, оставляем: {len(to_keep)}")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}Консолидация МОЗГ")
    print(f"  Всего эпизодов: {len(episodes)}")
    print(f"  К сжатию: {len(to_compress)}")
    print(f"  Оставить как есть: {len(to_keep)}")
    print()

    compressed_count = 0

    for ep_file in to_compress:
        content = ep_file.read_text(encoding="utf-8")
        original_lines = len(content.strip().split("\n"))

        # Извлечь суть
        essence = extract_essence(content)
        compressed = create_compressed_version(ep_file, essence)
        compressed_lines = len(compressed.strip().split("\n"))

        ratio = (1 - compressed_lines / max(original_lines, 1)) * 100

        print(f"  {ep_file.name}: {original_lines} строк -> {compressed_lines} строк ({ratio:.0f}% сжатие)")

        if essence["title"]:
            print(f"    Тема: {essence['theme'] or essence['title']}")
        if essence["results"]:
            print(f"    Результатов: {len(essence['results'])}")
        if essence["decisions"]:
            print(f"    Решений: {len(essence['decisions'])}")

        if not dry_run:
            # Создать архивную папку
            archive_dir = EPISODES_DIR / "archive" / ep_file.parent.name
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Переместить оригинал в архив
            archive_path = archive_dir / ep_file.name
            shutil.move(str(ep_file), str(archive_path))

            # Записать сжатую версию на место оригинала
            ep_file.write_text(compressed, encoding="utf-8")

            compressed_count += 1

        print()

    if not dry_run and compressed_count > 0:
        # Обновить INDEX.md
        update_index(to_compress)
        print(f"Готово! Сжато {compressed_count} эпизодов.")
        print(f"Оригиналы сохранены в episodes/archive/")
        # Ночная инкубация подсознания
        run_nightly_incubation()
    elif dry_run:
        print("[DRY RUN] Ничего не изменено. Уберите --dry-run чтобы выполнить.")


def update_index(compressed_files):
    """Пометить сжатые файлы в INDEX.md."""
    if not INDEX_FILE.exists():
        return

    content = INDEX_FILE.read_text(encoding="utf-8")

    for ep_file in compressed_files:
        # Найти строку с этим файлом и добавить [С]
        old_name = f"{ep_file.parent.name}/{ep_file.name}"
        if old_name in content and "[С]" not in content.split(old_name)[0].split("\n")[-1]:
            content = content.replace(
                f"`{old_name}`",
                f"`{old_name}` [С]"
            )

    INDEX_FILE.write_text(content, encoding="utf-8")
    print("INDEX.md обновлён (помечены сжатые [С])")


def show_stats():
    """Показать статистику текущего состояния памяти."""
    episodes = find_episode_files()

    total_lines = 0
    total_size = 0

    print("\n=== Статистика эпизодов ===\n")

    for ep in episodes:
        content = ep.read_text(encoding="utf-8")
        lines = len(content.strip().split("\n"))
        size = ep.stat().st_size
        total_lines += lines
        total_size += size

        compressed = "[С]" if "[СЖАТО]" in content else "   "
        print(f"  {compressed} {ep.parent.name}/{ep.name}: {lines} строк, {size/1024:.1f}KB")

    print(f"\n  Всего: {len(episodes)} файлов, {total_lines} строк, {total_size/1024:.1f}KB")

    # Проверить архив
    archive_dir = EPISODES_DIR / "archive"
    if archive_dir.exists():
        archive_count = sum(1 for _ in archive_dir.rglob("*.md"))
        archive_size = sum(f.stat().st_size for f in archive_dir.rglob("*.md"))
        print(f"  Архив: {archive_count} файлов, {archive_size/1024:.1f}KB")


def run_nightly_incubation():
    """
    Ночная инкубация подсознания.
    Вызывается автоматически в конце consolidate().
    """
    try:
        senses_dir = Path(__file__).parent
        import sys
        if str(senses_dir) not in sys.path:
            sys.path.insert(0, str(senses_dir))
        from subconscious import incubate
        new_insights = incubate()
        if new_insights:
            print(f"  Инкубация: {len(new_insights)} новых инсайтов")
        else:
            print("  Инкубация: нет новых инсайтов")
    except Exception as e:
        print(f"  Инкубация: ошибка ({e})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Консолидация памяти МОЗГ — 'сон' для системы"
    )
    parser.add_argument("--days", type=int, default=7,
                        help="Сжимать эпизоды старше N дней (default: 7)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Показать что будет сжато, без изменений")
    parser.add_argument("--all", action="store_true", dest="consolidate_all",
                        help="Сжать ВСЕ кроме последних 3")
    parser.add_argument("--keep", type=int, default=3,
                        help="Сколько последних эпизодов оставить (с --all)")
    parser.add_argument("--stats", action="store_true",
                        help="Показать статистику без изменений")

    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        consolidate(
            days=args.days,
            dry_run=args.dry_run,
            consolidate_all=args.consolidate_all,
            keep_last=args.keep
        )
