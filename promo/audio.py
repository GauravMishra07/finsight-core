"""Generates the promo's voiceover (edge-tts) and an original ambient music bed (numpy).

Run: .venv/Scripts/python audio.py   (writes public/voice/*.mp3, public/music.wav, src/voice.json)
"""
import asyncio
import json
import subprocess
import wave
from pathlib import Path

import edge_tts
import numpy as np

VOICE = "en-US-AndrewNeural"
RATE = "+12%"
# One line per scene, in scene order (see SCENES in src/Promo.tsx).
LINES = [
    "Writing a credit memo takes analysts days. FinSight does it in two minutes.",
    "Meet FinSight, your AI credit underwriter.",
    "Just type a ticker. FinSight pulls the latest 10-K from the SEC.",
    "Four AI agents read the filing, crunch the numbers, scan the news, and write the memo.",
    "Every figure comes from audited SEC data. Never guessed.",
    "You get a lender-ready credit memo, with a clear verdict.",
    "Competitors, benchmarked side by side.",
    "And a copilot that answers follow-ups, straight from the filing.",
    "Grounded. Audited. Fast.",
    "FinSight. From annual report to credit memo, in two minutes.",
]

ROOT = Path(__file__).parent
SR = 48000


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout)


async def voice():
    out = ROOT / "public" / "voice"
    out.mkdir(parents=True, exist_ok=True)
    meta = []
    for i, text in enumerate(LINES):
        path = out / f"line{i}.mp3"
        await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))
        meta.append({"file": f"voice/{path.name}", "scene": i, "seconds": round(duration(path), 3), "text": text})
        print(f"{meta[-1]['seconds']:5.2f}s  {text}")
    (ROOT / "src" / "voice.json").write_text(json.dumps(meta, indent=2))


def music(seconds=42.0, bpm=100):
    """Ambient tech bed: Am-F-C-G pads, plucked arpeggio, soft kick and hats."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    beat = 60 / bpm
    bar = beat * 4
    mix = np.zeros(n)
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G

    def env(length, attack, release):
        k = np.ones(length)
        a, r = int(attack * SR), int(release * SR)
        k[:a] = np.linspace(0, 1, a)
        k[-r:] *= np.linspace(1, 0, r)
        return k

    # Pads: detuned sines with a couple of harmonics, crossfaded per bar.
    for b in range(int(seconds / bar) + 1):
        s = int(b * bar * SR)
        length = min(int(bar * 1.25 * SR), n - s)
        if length <= 0:
            break
        tt = np.arange(length) / SR
        tone = np.zeros(length)
        for m in chords[b % 4]:
            for det in (-0.12, 0.12):
                f = midi(m) * 2 ** (det / 12)
                tone += np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) + 0.1 * np.sin(6 * np.pi * f * tt)
        tone += 0.8 * np.sin(2 * np.pi * midi(chords[b % 4][0] - 12) * tt)  # bass root
        mix[s : s + length] += 0.05 * tone * env(length, 0.6, 0.6)

    # Arpeggio: 8th-note plucks over the chord, an octave up.
    step = beat / 2
    for k in range(int(seconds / step)):
        s = int(k * step * SR)
        length = min(int(0.45 * SR), n - s)
        if length <= 0:
            break
        ch = chords[int(k * step / bar) % 4]
        f = midi(ch[[0, 1, 2, 1][k % 4]] + 12)
        tt = np.arange(length) / SR
        mix[s : s + length] += 0.06 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9)

    # Kick on every beat, hats on off-beats; drums enter after the 2-bar intro.
    rng = np.random.default_rng(7)
    for k in range(int(seconds / beat)):
        if k < 8:
            continue
        s = int(k * beat * SR)
        length = min(int(0.3 * SR), n - s)
        tt = np.arange(length) / SR
        mix[s : s + length] += 0.35 * np.sin(2 * np.pi * (45 + 80 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12)
        h = s + int(beat / 2 * SR)
        hl = min(int(0.05 * SR), n - h)
        if hl > 0:
            mix[h : h + hl] += 0.04 * rng.standard_normal(hl) * np.exp(-np.arange(hl) / SR * 80)

    # Simple stereo widening via a short delay, then fade and normalise.
    left = mix
    right = np.concatenate([np.zeros(int(0.012 * SR)), mix[: -int(0.012 * SR)]])
    stereo = np.stack([left, right], axis=1)
    stereo *= env(n, 1.5, 3.0)[:, None]
    stereo /= np.abs(stereo).max() / 0.85
    with wave.open(str(ROOT / "public" / "music.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype("<i2").tobytes())
    print("music.wav written")


if __name__ == "__main__":
    asyncio.run(voice())
    music()
