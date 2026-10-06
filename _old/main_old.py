from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import tempfile
import shutil

# Force Transformers to use PyTorch instead of TensorFlow to prevent AttributeError
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
from modules.module1_acoustic import AcousticProsodyEngine
from modules.module2_nlp import SemanticSTARAnalyzer
from modules.module3_chatbot import AdaptiveChatbot
from modules.module4_ml import MLScoringEngine

app = FastAPI(title="VoxIQ - Multimodal Interview Coach")

# Initialize the acoustic engine (loads Whisper tiny)
print("Initializing Acoustic Engine...")
acoustic_engine = AcousticProsodyEngine(use_local=True)

# Initialize the NLP engine (loads DistilBART zero-shot)
print("Initializing NLP Engine...")
nlp_engine = SemanticSTARAnalyzer()

# Initialize the Chatbot engine (loads Groq/Ollama)
print("Initializing Chatbot Engine...")
chatbot_engine = AdaptiveChatbot()

# Initialize the ML Scoring Engine (loads RandomForest model)
print("Initializing ML Scoring Engine...")
ml_engine = MLScoringEngine()

# Allow CORS for frontend (HTML/JS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisResponse(BaseModel):
    module1_dl_score: dict
    module2_nlp_score: dict
    module3_chatbot_response: str
    module4_ml_final_score: float

from fastapi.staticfiles import StaticFiles

# The API routes are defined below


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_interview(
    audio: UploadFile = File(None),
    transcript: str = Form(""),
    text_input: str = Form(""),
    job_description: str = Form(""),
    previous_question: str = Form("")
):
    """
    Main pipeline endpoint that orchestrates the 4 modules.
    """
    if text_input:
        transcript = text_input

    if not audio and not transcript:
        raise HTTPException(status_code=400, detail="Must provide audio or transcript.")

    # Module 1 - Deep Learning (Acoustic & Prosody Engine)
    dl_results = {}
    if audio:
        # Save uploaded audio to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            shutil.copyfileobj(audio.file, temp_audio)
            temp_audio_path = temp_audio.name
            
        try:
            dl_results = acoustic_engine.analyze_audio(temp_audio_path)
            # If the user didn't provide a transcript, use Whisper's
            if not transcript and "transcript" in dl_results:
                transcript = dl_results["transcript"]
        finally:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    else:
        # If the user typed their answer, we pass "perfect" acoustic defaults 
        # so the ML model only grades them on their NLP semantic score.
        dl_results = {
            "transcript": transcript,
            "wpm_score": 140.0, 
            "filler_frequency": 0, 
            "pitch_variance_score": 1.0, 
            "acoustic_confidence": 0.95,
            "status": "Text input mode"
        }

    # Module 2 - NLP (Semantic & STAR Analyzer)
    if transcript:
        nlp_results = nlp_engine.analyze_transcript(transcript, job_description)
    else:
        nlp_results = {
            "star_s_score": 0.0, "star_t_score": 0.0, 
            "star_a_score": 0.0, "star_r_score": 0.0,
            "keyword_relevance_score": 0.0,
            "missing_flags": ["No transcript available for NLP analysis."]
        }

    # Module 3 - Adaptive Chatbot
    # Feed transcript and missing_flags to Groq/Ollama
    if transcript:
        chatbot_response = chatbot_engine.generate_follow_up(
            transcript=transcript, 
            missing_flags=nlp_results.get("missing_flags", []),
            previous_question=previous_question
        )
    else:
        chatbot_response = "I couldn't hear you clearly. Could you please repeat your answer?"

    # Module 4 - Machine Learning (Scoring Engine)
    # Feed DL and NLP vectors into Scikit-Learn model
    final_score = ml_engine.predict_score(dl_results, nlp_results)

    return AnalysisResponse(
        module1_dl_score=dl_results,
        module2_nlp_score=nlp_results,
        module3_chatbot_response=chatbot_response,
        module4_ml_final_score=final_score
    )

# Mount the frontend directory at the root so users can just visit 127.0.0.1:8000
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    # Run the server with: python main.py
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
