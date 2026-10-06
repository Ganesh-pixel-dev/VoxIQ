"""Settings, all overridable with environment variables (see .env.example)."""
import os

# A broken TensorFlow install on the machine breaks transformers imports; we only use PyTorch.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


WHISPER_MODEL = os.environ.get("VOXIQ_WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.environ.get("VOXIQ_WHISPER_DEVICE", "auto")  # auto, cuda or cpu
OLLAMA_URL = os.environ.get("VOXIQ_OLLAMA_URL", "http://127.0.0.1:11434")
LLM_MODEL = os.environ.get("VOXIQ_LLM_MODEL", "qwen2.5:1.5b")
LLM_TIMEOUT = _int("VOXIQ_LLM_TIMEOUT", 120)
DATA_DIR = Path(os.environ.get("VOXIQ_DATA_DIR", ROOT / "data"))
FILLERS_FILE = os.environ.get("VOXIQ_FILLERS_FILE", "")

MAX_AUDIO_MB = _int("VOXIQ_MAX_AUDIO_MB", 25)
MIN_AUDIO_SECONDS = _int("VOXIQ_MIN_AUDIO_SECONDS", 5)
MAX_AUDIO_SECONDS = _int("VOXIQ_MAX_AUDIO_SECONDS", 300)
MAX_RESUME_MB = _int("VOXIQ_MAX_RESUME_MB", 5)
MAX_JD_CHARS = _int("VOXIQ_MAX_JD_CHARS", 20000)

# Thresholds shown in the UI. They are my choices from common coaching advice, not measured standards.
PACE_RANGE = (120, 160)          # words per minute
FILLERS_PER_MIN_MAX = 3.0
LENGTH_RANGE = (60, 120)         # seconds, for a behavioural answer
