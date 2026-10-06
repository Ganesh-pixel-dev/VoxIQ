"""FastAPI app. Heavy parts (Whisper, the LLM) are injected so the routes can be tested with fakes."""
import io
import tempfile
from pathlib import Path

import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, llm, questions, scoring, suggest
from .compare import compare
from .fillers import load_config
from .resume import ResumeError, extract_text, parse
from .store import Store, question_id
from .transcribe import AudioError, Transcriber

AUDIO_TYPES = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".mp4", ".flac", ".oga"}
FRONTEND = config.ROOT / "frontend"


def _read_limited(upload: UploadFile, max_mb: int) -> bytes:
    data = upload.file.read(max_mb * 1024 * 1024 + 1)
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {max_mb} MB.")
    if not data:
        raise HTTPException(400, "The file is empty.")
    return data


def create_app(transcriber=None, ask_json=None, ask_text=None, data_dir=None) -> FastAPI:
    app = FastAPI(title="VoxIQ")
    transcriber = transcriber or Transcriber()
    ask_json = ask_json or llm.chat_json
    ask_text = ask_text or llm.chat
    store = Store(data_dir or config.DATA_DIR)
    filler_cfg = load_config(config.FILLERS_FILE)

    @app.get("/api/status")
    def status():
        return {
            "llm": llm.available() if ask_json is llm.chat_json else {"up": True, "model": "test", "model_ready": True},
            "whisper": {"model": transcriber.model_name if hasattr(transcriber, "model_name") else "test",
                        "device": getattr(transcriber, "device", None)},
            "limits": {"max_audio_mb": config.MAX_AUDIO_MB, "min_seconds": config.MIN_AUDIO_SECONDS,
                       "max_seconds": config.MAX_AUDIO_SECONDS},
            "thresholds": {"pace": config.PACE_RANGE, "fillers_per_min": config.FILLERS_PER_MIN_MAX, "length": config.LENGTH_RANGE},
        }

    @app.get("/api/hr-questions")
    def hr_questions():
        return {"questions": [{"question": t, "source_line": 0, "source_text": "", "kind": "hr", "origin": "standard"}
                              for t in questions.HR_QUESTIONS]}

    @app.post("/api/questions")
    def make_questions(resume: UploadFile = File(...), job_description: str = Form("")):
        if len(job_description) > config.MAX_JD_CHARS:
            raise HTTPException(413, "The job description is too long.")
        data = _read_limited(resume, config.MAX_RESUME_MB)
        try:
            parsed = parse(extract_text(data, resume.filename or ""))
        except ResumeError as e:
            raise HTTPException(400, str(e))
        out = questions.generate(parsed, job_description, ask=ask_json)
        out["resume"] = {"lines": len(parsed.lines), "projects": [p["name"] for p in parsed.projects], "skills": parsed.skills[:20]}
        return out

    @app.post("/api/analyze")
    def analyze(audio: UploadFile = File(...), question: str = Form(...), job_description: str = Form("")):
        question = question.strip()
        if not question or len(question) > 500:
            raise HTTPException(400, "A question (up to 500 characters) is required.")
        if len(job_description) > config.MAX_JD_CHARS:
            raise HTTPException(413, "The job description is too long.")
        suffix = Path(audio.filename or "").suffix.lower()
        if suffix not in AUDIO_TYPES:
            raise HTTPException(415, "Audio must be one of: " + ", ".join(sorted(AUDIO_TYPES)) + ".")
        data = _read_limited(audio, config.MAX_AUDIO_MB)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
        try:
            transcript = transcriber.transcribe(tmp.name)
        except AudioError as e:
            raise HTTPException(422, str(e))
        finally:
            Path(tmp.name).unlink(missing_ok=True)
        result = scoring.analyse(transcript.words, transcript.duration, job_description, filler_cfg)
        if transcript.audio is not None:
            # browsers record WebM without a seek index, so I store WAV to make "click a filler to hear it" work
            buf = io.BytesIO()
            sf.write(buf, transcript.audio, 16000, format="WAV", subtype="PCM_16")
            data, suffix = buf.getvalue(), ".wav"
        attempt = store.add(question, job_description, data, suffix, result)
        earlier = [a for a in store.for_question(attempt["question_id"]) if a["id"] != attempt["id"]]
        attempt["compare"] = compare(earlier[-1]["result"], result) if earlier else None
        attempt["compared_with"] = earlier[-1]["id"] if earlier else None
        attempt["attempt_number"] = len(earlier) + 1
        return attempt

    @app.get("/api/attempts")
    def attempts(question: str):
        rows = store.for_question(question_id(question))
        return {"attempts": rows}

    @app.get("/api/compare")
    def compare_route(a: int, b: int):
        x, y = store.get(a), store.get(b)
        if not x or not y:
            raise HTTPException(404, "Attempt not found.")
        return {"a": x, "b": y, "compare": compare(x["result"], y["result"])}

    @app.get("/api/attempts/{attempt_id}/audio")
    def attempt_audio(attempt_id: int):
        p = store.audio_path(attempt_id)
        if not p:
            raise HTTPException(404, "No recording for this attempt.")
        return FileResponse(p)

    @app.delete("/api/attempts/{attempt_id}")
    def delete_attempt(attempt_id: int):
        if not store.delete(attempt_id):
            raise HTTPException(404, "Attempt not found.")
        return {"deleted": attempt_id}

    @app.post("/api/attempts/{attempt_id}/suggest")
    def suggest_route(attempt_id: int):
        a = store.get(attempt_id)
        if not a:
            raise HTTPException(404, "Attempt not found.")
        try:
            return suggest.rewrite(a["question"], a["result"], ask=ask_text)
        except llm.LLMUnavailable as e:
            raise HTTPException(503, str(e))

    if FRONTEND.exists():
        app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
    return app
