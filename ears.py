"""
УШИ — аудио-анализатор для Claude
Анализирует музыку и создаёт визуальное представление звука

Использование:
  py ears.py <аудио_файл>

Результат:
  - Спектрограмма (картинка — "как выглядит звук")
  - Волновая форма (картинка — амплитуда по времени)
  - Хромаграмма (картинка — ноты по времени)
  - Текстовый отчёт (BPM, тональность, громкость, характеристики)
"""

import sys
import os
import json
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import librosa
import librosa.display
import matplotlib
matplotlib.use('Agg')  # без GUI
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import timedelta


# Названия нот
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_NAMES_RU = ['До', 'До#', 'Ре', 'Ре#', 'Ми', 'Фа', 'Фа#', 'Соль', 'Соль#', 'Ля', 'Ля#', 'Си']


def detect_key(y, sr):
    """Определить тональность трека"""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    # Мажорные и минорные профили Крумхансла
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    best_corr = -1
    best_key = ""
    best_key_ru = ""
    best_mode = ""

    for i in range(12):
        rolled = np.roll(chroma_mean, -i)

        corr_major = np.corrcoef(rolled, major_profile)[0, 1]
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = f"{NOTE_NAMES[i]} major"
            best_key_ru = f"{NOTE_NAMES_RU[i]} мажор"
            best_mode = "major"

        corr_minor = np.corrcoef(rolled, minor_profile)[0, 1]
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = f"{NOTE_NAMES[i]} minor"
            best_key_ru = f"{NOTE_NAMES_RU[i]} минор"
            best_mode = "minor"

    return best_key, best_key_ru, best_mode, best_corr


def analyze_dynamics(y, sr):
    """Анализ динамики: тихие/громкие участки"""
    rms = librosa.feature.rms(y=y)[0]
    times = librosa.times_like(rms, sr=sr)

    # Нормализуем
    rms_norm = rms / (rms.max() + 1e-10)

    # Находим кульминацию
    peak_idx = np.argmax(rms)
    peak_time = times[peak_idx]

    # Средняя и макс громкость в dB
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    avg_db = float(np.mean(rms_db))

    # Динамический диапазон
    dynamic_range = float(np.max(rms_db) - np.min(rms_db[rms_db > -80]))

    return {
        "peak_time": float(peak_time),
        "peak_time_str": str(timedelta(seconds=int(peak_time))),
        "avg_loudness_db": round(avg_db, 1),
        "dynamic_range_db": round(dynamic_range, 1),
        "rms": rms,
        "rms_times": times
    }


def detect_mood(tempo, key_mode, spectral_centroid_mean, dynamic_range):
    """Определить настроение трека (приблизительно)"""
    moods = []

    if key_mode == "minor":
        moods.append("меланхоличное")
    else:
        moods.append("светлое")

    if tempo > 120:
        moods.append("энергичное")
    elif tempo < 80:
        moods.append("спокойное")
    else:
        moods.append("умеренное")

    if spectral_centroid_mean > 3000:
        moods.append("яркое")
    elif spectral_centroid_mean < 1500:
        moods.append("тёмное/глубокое")

    if dynamic_range > 30:
        moods.append("контрастное")
    elif dynamic_range < 10:
        moods.append("ровное")

    return ", ".join(moods)


def analyze_audio(audio_path, output_dir=None):
    """Полный анализ аудиофайла"""

    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(f"ОШИБКА: Файл не найден: {audio_path}")
        return None

    # Папка для результатов
    if output_dir is None:
        output_dir = audio_path.parent / f"{audio_path.stem}_analysis"
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"Анализирую: {audio_path.name}")
    print(f"  Загрузка аудио...")

    # Загружаем аудио
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    duration_str = str(timedelta(seconds=int(duration)))

    print(f"  Длительность: {duration_str}")
    print(f"  Sample rate: {sr} Hz")

    # === АНАЛИЗ ===

    # 1. Темп (BPM)
    print(f"  Определяю темп...")
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, '__len__'):
        tempo = float(tempo[0])
    else:
        tempo = float(tempo)

    # 2. Тональность
    print(f"  Определяю тональность...")
    key, key_ru, key_mode, key_confidence = detect_key(y, sr)

    # 3. Спектральные характеристики
    print(f"  Анализирую спектр...")
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]

    # 4. Динамика
    print(f"  Анализирую динамику...")
    dynamics = analyze_dynamics(y, sr)

    # 5. Zero crossing rate (перкуссивность)
    zcr = librosa.feature.zero_crossing_rate(y)[0]

    # 6. Настроение
    mood = detect_mood(tempo, key_mode, float(np.mean(spectral_centroid)), dynamics["dynamic_range_db"])

    # === ВИЗУАЛИЗАЦИЯ ===

    print(f"  Создаю визуализации...")

    # Общий стиль
    plt.style.use('dark_background')

    # 1. Спектрограмма — "как выглядит звук"
    fig, ax = plt.subplots(figsize=(14, 6))
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    S_dB = librosa.power_to_db(S, ref=np.max)
    img = librosa.display.specshow(S_dB, sr=sr, x_axis='time', y_axis='mel', ax=ax, cmap='magma')
    fig.colorbar(img, ax=ax, format='%+2.0f dB')
    ax.set_title(f'СПЕКТРОГРАММА — {audio_path.stem}', fontsize=14, fontweight='bold')
    ax.set_xlabel('Время')
    ax.set_ylabel('Частота (Hz)')
    spec_path = output_dir / "spectrogram.png"
    fig.savefig(str(spec_path), dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close()

    # 2. Волновая форма — амплитуда по времени (даунсэмплинг для длинных треков)
    fig, ax = plt.subplots(figsize=(14, 4))
    max_points = 50000  # лимит точек чтобы matplotlib не упал
    if len(y) > max_points:
        step = len(y) // max_points
        y_plot = y[::step]
    else:
        y_plot = y
    times_wave = np.linspace(0, duration, len(y_plot))
    ax.plot(times_wave, y_plot, color='#00BFFF', linewidth=0.3, alpha=0.7)
    ax.fill_between(times_wave, y_plot, alpha=0.3, color='#00BFFF')
    ax.set_title(f'ВОЛНОВАЯ ФОРМА — {audio_path.stem}', fontsize=14, fontweight='bold')
    ax.set_xlabel('Время (сек)')
    ax.set_ylabel('Амплитуда')
    ax.set_xlim(0, duration)
    wave_path = output_dir / "waveform.png"
    fig.savefig(str(wave_path), dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close()

    # 3. Хромаграмма — ноты по времени
    fig, ax = plt.subplots(figsize=(14, 5))
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    img = librosa.display.specshow(chroma, sr=sr, x_axis='time', y_axis='chroma', ax=ax, cmap='coolwarm')
    fig.colorbar(img, ax=ax)
    ax.set_title(f'ХРОМАГРАММА (ноты) — {audio_path.stem}', fontsize=14, fontweight='bold')
    ax.set_xlabel('Время')
    ax.set_ylabel('Нота')
    chroma_path = output_dir / "chromagram.png"
    fig.savefig(str(chroma_path), dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close()

    # 4. Динамика + темп
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    # Громкость
    ax1.plot(dynamics["rms_times"], dynamics["rms"], color='#FF6B35', linewidth=1)
    ax1.fill_between(dynamics["rms_times"], dynamics["rms"], alpha=0.3, color='#FF6B35')
    ax1.axvline(x=dynamics["peak_time"], color='red', linestyle='--', alpha=0.7, label=f'Кульминация: {dynamics["peak_time_str"]}')
    ax1.set_title(f'ДИНАМИКА — {audio_path.stem}', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Громкость')
    ax1.legend()

    # Спектральный центроид (яркость звука)
    frames = range(len(spectral_centroid))
    t = librosa.frames_to_time(list(frames), sr=sr)
    ax2.plot(t, spectral_centroid, color='#7B68EE', linewidth=0.8)
    ax2.fill_between(t, spectral_centroid, alpha=0.2, color='#7B68EE')
    ax2.set_title('Яркость звука (спектральный центроид)', fontsize=12)
    ax2.set_xlabel('Время (сек)')
    ax2.set_ylabel('Частота (Hz)')

    dynamics_path = output_dir / "dynamics.png"
    fig.savefig(str(dynamics_path), dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close()

    # === ОТЧЁТ ===

    info = {
        "file": str(audio_path),
        "file_size_mb": round(audio_path.stat().st_size / (1024*1024), 1),
        "duration": duration_str,
        "duration_seconds": round(duration, 1),
        "sample_rate": sr,
        "tempo_bpm": round(tempo, 1),
        "key": key,
        "key_ru": key_ru,
        "key_confidence": round(key_confidence, 3),
        "mood": mood,
        "spectral_centroid_mean_hz": round(float(np.mean(spectral_centroid)), 1),
        "spectral_bandwidth_mean_hz": round(float(np.mean(spectral_bandwidth)), 1),
        "peak_time": dynamics["peak_time_str"],
        "avg_loudness_db": dynamics["avg_loudness_db"],
        "dynamic_range_db": dynamics["dynamic_range_db"],
        "percussiveness": round(float(np.mean(zcr)) * 100, 2),
        "images": {
            "spectrogram": str(spec_path),
            "waveform": str(wave_path),
            "chromagram": str(chroma_path),
            "dynamics": str(dynamics_path)
        }
    }

    # JSON отчёт
    report_path = output_dir / "audio_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    # Текстовый отчёт для Claude
    txt_path = output_dir / "audio_report.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"{'='*60}\n")
        f.write(f"  АУДИО-АНАЛИЗ: {audio_path.name}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"Файл: {audio_path}\n")
        f.write(f"Размер: {info['file_size_mb']} МБ\n")
        f.write(f"Длительность: {info['duration']}\n\n")
        f.write(f"--- РИТМ ---\n")
        f.write(f"Темп: {info['tempo_bpm']} BPM\n\n")
        f.write(f"--- ТОНАЛЬНОСТЬ ---\n")
        f.write(f"Тональность: {info['key_ru']} ({info['key']})\n")
        f.write(f"Уверенность: {info['key_confidence']}\n\n")
        f.write(f"--- НАСТРОЕНИЕ ---\n")
        f.write(f"{info['mood']}\n\n")
        f.write(f"--- ДИНАМИКА ---\n")
        f.write(f"Кульминация: {info['peak_time']}\n")
        f.write(f"Средняя громкость: {info['avg_loudness_db']} dB\n")
        f.write(f"Динамический диапазон: {info['dynamic_range_db']} dB\n\n")
        f.write(f"--- ТЕМБР ---\n")
        f.write(f"Яркость (центроид): {info['spectral_centroid_mean_hz']} Hz\n")
        f.write(f"Ширина спектра: {info['spectral_bandwidth_mean_hz']} Hz\n")
        f.write(f"Перкуссивность: {info['percussiveness']}%\n\n")
        f.write(f"--- ВИЗУАЛИЗАЦИИ ---\n")
        for name, path in info['images'].items():
            f.write(f"  {name}: {path}\n")

    # Вывод в консоль
    print(f"\n{'='*50}")
    print(f"  РЕЗУЛЬТАТ АНАЛИЗА")
    print(f"{'='*50}")
    print(f"  Темп: {info['tempo_bpm']} BPM")
    print(f"  Тональность: {info['key_ru']}")
    print(f"  Настроение: {info['mood']}")
    print(f"  Кульминация: {info['peak_time']}")
    print(f"  Динамический диапазон: {info['dynamic_range_db']} dB")
    print(f"{'='*50}")
    print(f"\nВизуализации в папке: {output_dir}")

    return info


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: py ears.py <аудио_файл>")
        print("Поддерживаемые форматы: mp3, wav, flac, ogg, m4a")
        print("Пример: py ears.py song.mp3")
        sys.exit(1)

    analyze_audio(sys.argv[1])
