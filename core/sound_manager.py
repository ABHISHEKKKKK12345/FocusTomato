"""
Cross-platform sound alert system using PyQt6's multimedia or system beeps.
Generates tones procedurally so no audio files are needed.
"""

import logging
import math
import struct
import sys
import threading
import wave
import tempfile
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import multimedia support
_QSoundEffect = None
_QUrl = None
try:
    from PyQt6.QtMultimedia import QSoundEffect
    from PyQt6.QtCore import QUrl
    _QSoundEffect = QSoundEffect
    _QUrl = QUrl
    logger.info("PyQt6 multimedia available")
except ImportError:
    logger.info("PyQt6 multimedia not available, falling back to system beep")


def _generate_tone_wav(filename: str, frequency: float, duration: float,
                        volume: float = 0.7, sample_rate: int = 44100) -> None:
    """Generate a sine-wave WAV file."""
    num_samples = int(sample_rate * duration)
    # Apply a simple envelope (fade in/out)
    fade_samples = min(int(sample_rate * 0.05), num_samples // 4)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        val = math.sin(2 * math.pi * frequency * t)
        # Envelope
        env = 1.0
        if i < fade_samples:
            env = i / fade_samples
        elif i > num_samples - fade_samples:
            env = (num_samples - i) / fade_samples
        samples.append(int(val * env * volume * 32767))

    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def _generate_chime_wav(filename: str, frequencies: list, durations: list,
                         volume: float = 0.7, sample_rate: int = 44100) -> None:
    """Generate a multi-tone chime WAV."""
    all_samples = []
    for freq, dur in zip(frequencies, durations):
        n = int(sample_rate * dur)
        fade = min(int(sample_rate * 0.03), n // 4)
        for i in range(n):
            t = i / sample_rate
            val = math.sin(2 * math.pi * freq * t)
            env = 1.0
            if i < fade:
                env = i / fade
            elif i > n - fade:
                env = (n - i) / fade
            all_samples.append(int(val * env * volume * 32767))

    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(all_samples)}h", *all_samples))


class SoundTheme:
    """Holds WAV file paths for a sound theme."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._tmpfiles: list[str] = []
        self.focus_complete: str = ""
        self.break_complete: str = ""
        self.tick: str = ""
        self._generate()

    def _generate(self) -> None:
        try:
            if self.name == "gentle":
                self.focus_complete = self._make(
                    _generate_chime_wav,
                    [523, 659, 784, 1047],
                    [0.18, 0.18, 0.18, 0.35],
                    volume=0.55,
                )
                self.break_complete = self._make(
                    _generate_chime_wav,
                    [784, 659, 523],
                    [0.18, 0.18, 0.30],
                    volume=0.45,
                )
                self.tick = self._make(
                    _generate_tone_wav,
                    frequency=800, duration=0.04, volume=0.12,
                )
            elif self.name == "classic":
                self.focus_complete = self._make(
                    _generate_tone_wav,
                    frequency=880, duration=0.6, volume=0.65,
                )
                self.break_complete = self._make(
                    _generate_tone_wav,
                    frequency=660, duration=0.5, volume=0.55,
                )
                self.tick = self._make(
                    _generate_tone_wav,
                    frequency=1000, duration=0.03, volume=0.15,
                )
            else:  # minimal
                self.focus_complete = self._make(
                    _generate_tone_wav,
                    frequency=440, duration=0.3, volume=0.4,
                )
                self.break_complete = self._make(
                    _generate_tone_wav,
                    frequency=330, duration=0.3, volume=0.35,
                )
                self.tick = ""
        except Exception as e:
            logger.error(f"Sound generation failed: {e}")

    def _make(self, generator_fn, *args, **kwargs) -> str:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        self._tmpfiles.append(path)
        try:
            generator_fn(path, *args, **kwargs)
        except Exception as e:
            logger.error(f"Failed to generate sound: {e}")
            return ""
        return path

    def cleanup(self) -> None:
        for f in self._tmpfiles:
            try:
                os.unlink(f)
            except OSError:
                pass


class SoundManager:
    """Plays alert sounds with volume control."""

    def __init__(self) -> None:
        self._enabled = True
        self._volume = 0.7
        self._theme_name = "gentle"
        self._theme: Optional[SoundTheme] = None
        self._effects: dict = {}
        self._lock = threading.Lock()
        self._load_theme("gentle")

    def _load_theme(self, name: str) -> None:
        if self._theme:
            self._theme.cleanup()
        self._theme = SoundTheme(name)
        self._effects.clear()
        if _QSoundEffect is None:
            return
        for attr in ("focus_complete", "break_complete", "tick"):
            path = getattr(self._theme, attr, "")
            if path and os.path.exists(path):
                effect = _QSoundEffect()
                effect.setSource(_QUrl.fromLocalFile(path))
                effect.setVolume(self._volume)
                self._effects[attr] = effect

    def set_theme(self, name: str) -> None:
        if name != self._theme_name:
            self._theme_name = name
            self._load_theme(name)

    def set_volume(self, volume: int) -> None:
        """Volume 0–100."""
        self._volume = max(0.0, min(1.0, volume / 100.0))
        for effect in self._effects.values():
            effect.setVolume(self._volume)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def play_focus_complete(self) -> None:
        self._play("focus_complete")

    def play_break_complete(self) -> None:
        self._play("break_complete")

    def play_tick(self) -> None:
        self._play("tick")

    def _play(self, key: str) -> None:
        if not self._enabled:
            return
        effect = self._effects.get(key)
        if effect:
            effect.play()
        else:
            # Fallback: system beep in a thread so UI doesn't block
            threading.Thread(target=self._system_beep, daemon=True).start()

    @staticmethod
    def _system_beep() -> None:
        try:
            if sys.platform == "win32":
                import winsound
                winsound.Beep(880, 300)
            else:
                sys.stdout.write("\a")
                sys.stdout.flush()
        except Exception:
            pass

    def cleanup(self) -> None:
        if self._theme:
            self._theme.cleanup()
