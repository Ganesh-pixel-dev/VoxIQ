"""Speech to text with word timestamps, using faster-whisper (CTranslate2)."""
import threading
from dataclasses import dataclass

from . import config
from .fillers import Word

# Whisper tends to drop "um" and "uh" because its training transcripts are clean.
# A prompt that contains them nudges it to keep them. It helps, it does not guarantee.
PROMPT = "Um, so, uh, I think, like, you know, basically it was, uh, actually this."


class AudioError(ValueError):
    pass


@dataclass
class Transcript:
    words: list
    duration: float  # seconds of audio
    audio: object = None  # 16 kHz mono float array, kept so the app can store a seekable WAV


class Transcriber:
    def __init__(self, model: str = config.WHISPER_MODEL, device: str = config.WHISPER_DEVICE):
        self.model_name, self.requested = model, device
        self.device = None
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        from faster_whisper import WhisperModel
        if self.requested in ("auto", "cuda"):
            try:
                import torch  # noqa: F401  (its CUDA DLLs are what ctranslate2 finds on Windows)
                self._model = WhisperModel(self.model_name, device="cuda", compute_type="float16")
                self.device = "cuda"
                return
            except Exception as e:
                if self.requested == "cuda":
                    raise
                print(f"CUDA unavailable for Whisper ({type(e).__name__}), using CPU.")
        self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        self.device = "cpu"

    def _run(self, audio):
        segments, _ = self._model.transcribe(
            audio, language="en", beam_size=5, word_timestamps=True,
            initial_prompt=PROMPT, condition_on_previous_text=False,
        )
        return [Word(w.word.strip(), float(w.start), float(w.end)) for s in segments for w in (s.words or [])]

    def transcribe(self, path: str) -> Transcript:
        from faster_whisper import decode_audio
        try:
            audio = decode_audio(path, sampling_rate=16000)
        except Exception as e:
            raise AudioError("I could not decode this audio file. Try WAV, MP3, M4A, OGG or WebM.") from e
        duration = len(audio) / 16000
        if duration < config.MIN_AUDIO_SECONDS:
            raise AudioError(f"The recording is {duration:.1f}s. Answers need at least {config.MIN_AUDIO_SECONDS}s.")
        if duration > config.MAX_AUDIO_SECONDS:
            raise AudioError(f"The recording is {duration:.0f}s. The limit is {config.MAX_AUDIO_SECONDS}s.")
        with self._lock:
            if self._model is None:
                self._load()
            words = self._run(audio)
        if len(words) < 3:
            raise AudioError("I could not hear any speech in this recording. Check the microphone and try again.")
        return Transcript(words, duration, audio)
