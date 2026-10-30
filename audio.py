import numpy as np
import soundfile as sf


def analyze_audio(path, window_seconds=30, threshold=0.015):
    """Return coarse acoustic activity windows. No speech recognition."""
    try:
        audio, sr = sf.read(path, always_2d=True)
    except Exception as exc:
        raise RuntimeError(
            "Could not read the WAV file. Please upload a standard PCM WAV file."
        ) from exc

    if audio.size == 0:
        return []

    mono = np.asarray(audio, dtype=np.float32).mean(axis=1)
    size = max(1, int(sr * window_seconds))
    frame = max(1, int(sr * 0.02))
    output = []

    for start in range(0, len(mono), size):
        x = mono[start:start + size]
        if len(x) == 0:
            continue

        energies = []
        for i in range(0, len(x), frame):
            chunk = x[i:i + frame]
            if len(chunk):
                energies.append(float(np.sqrt(np.mean(chunk * chunk))))

        if energies:
            activity = float(np.mean(np.asarray(energies) > threshold))
        else:
            activity = 0.0

        output.append(
            {
                "window_start": int(start / sr),
                "audio_activity": round(min(1.0, max(0.0, activity)), 4),
            }
        )

    return output
