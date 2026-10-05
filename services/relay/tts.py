"""Windows offline TTS, generated in a temporary directory and never uploaded."""
import io
import os
from pathlib import Path
import subprocess
import tempfile
import wave


class WindowsTTS:
    def synthesize(self, text):
        if os.name != "nt":
            raise RuntimeError("WINDOWS_TTS_ONLY")
        if not isinstance(text, str) or not 1 <= len(text) <= 80:
            raise ValueError("INVALID_TTS_TEXT")
        with tempfile.TemporaryDirectory(prefix="effmeet-tts-") as folder:
            output = Path(folder) / "speech.wav"
            env = {**os.environ, "EFFMEET_TTS_TEXT": text, "EFFMEET_TTS_OUTPUT": str(output)}
            # Fixed script: text/path are data via environment, never interpolated shell code.
            script = Path(__file__).with_name("synthesize.ps1")
            completed = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script.read_text(encoding="utf-8")],
                env=env, capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if completed.returncode != 0:
                raise RuntimeError("WINDOWS_TTS_FAILED")
            with wave.open(io.BytesIO(output.read_bytes()), "rb") as wav:
                if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
                    raise RuntimeError("TTS_FORMAT_MISMATCH")
                if wav.getnframes() > 480000:
                    raise RuntimeError("TTS_TOO_LONG")
                return wav.readframes(wav.getnframes())
