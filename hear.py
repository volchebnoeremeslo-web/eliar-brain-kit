"""
УХО — транскрипция аудио и видео для ЭЛИАРА
Работает локально, без интернета.

Использование:
  py hear.py <файл>          # MP3, WAV, MP4, M4A, OGG

Что делает:
  - MP4/видео → извлекает аудио через moviepy
  - Транскрибирует через Whisper (локальная модель base)
  - Загружает аудио через librosa (не нужен ffmpeg)
  - Сохраняет текст в файл рядом с исходником

Результат:
  <имя_файла>_transcript.txt
"""

import sys
import os
from pathlib import Path


def extract_audio_from_video(video_path, audio_path):
    """Извлечь аудио из видео через moviepy"""
    try:
        from moviepy.editor import VideoFileClip
        print("  Извлекаю аудио из видео...")
        video = VideoFileClip(str(video_path))
        video.audio.write_audiofile(str(audio_path), verbose=False, logger=None)
        video.close()
        return True
    except ImportError:
        print("ОШИБКА: moviepy не установлен. Запусти: py -m pip install moviepy")
        return False
    except Exception as e:
        print(f"ОШИБКА при извлечении аудио: {e}")
        return False


def transcribe(audio_path):
    """Транскрибировать через Whisper + librosa (без ffmpeg)"""
    try:
        import whisper
        import librosa
        import numpy as np
    except ImportError as e:
        print(f"ОШИБКА: {e}")
        print("Установи: py -m pip install openai-whisper librosa")
        return None

    print("  Загружаю модель Whisper...")
    model = whisper.load_model("base")

    print("  Загружаю аудио...")
    audio, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    duration_min = len(audio) / sr / 60
    print(f"  Длина: {duration_min:.1f} мин")

    print("  Транскрибирую... (подожди)")
    result = model.transcribe(audio, language="en", fp16=False)
    return result["text"]


def main():
    if len(sys.argv) < 2:
        print("Использование: py hear.py <файл>")
        print("Форматы: mp3, wav, mp4, m4a, ogg, flac")
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"ОШИБКА: Файл не найден: {input_path}")
        sys.exit(1)

    print(f"Слушаю: {input_path.name}")

    # Если видео — извлечь аудио
    video_formats = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
    audio_path = input_path

    if input_path.suffix.lower() in video_formats:
        audio_path = input_path.parent / (input_path.stem + "_audio.mp3")
        ok = extract_audio_from_video(input_path, audio_path)
        if not ok:
            sys.exit(1)

    # Транскрипция
    text = transcribe(audio_path)
    if not text:
        sys.exit(1)

    # Сохранить
    out_path = input_path.parent / (input_path.stem + "_transcript.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\nГотово!")
    print(f"Символов: {len(text)}")
    print(f"Файл: {out_path}")
    print(f"\nПервые 300 символов:")
    print(text[:300])


if __name__ == "__main__":
    main()
