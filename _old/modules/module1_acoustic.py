import librosa
import numpy as np
import re
import warnings
from transformers import pipeline

# Suppress warnings from librosa/transformers for cleaner output
warnings.filterwarnings("ignore")

class AcousticProsodyEngine:
    def __init__(self, model_id="openai/whisper-tiny.en", use_local=True):
        """
        Initializes the Deep Learning Engine for Acoustic & Prosody analysis.
        Uses an ultra-lightweight Whisper model (~150MB) for maximum speed on low-RAM CPUs.
        """
        self.use_local = use_local
        if self.use_local:
            print(f"Loading local Whisper model ({model_id}) for transcription...")
            # We use Whisper to get transcript and word-level timestamps
            self.transcriber = pipeline(
                "automatic-speech-recognition",
                model=model_id,
                chunk_length_s=30,
                return_timestamps="word",
                generate_kwargs={"language": "english"}
            )
        else:
            # Placeholder for Groq API fallback if needed
            self.transcriber = None

        # Common filler words to detect
        self.filler_words = [r'\bumm?\b', r'\buhh?\b', r'\blike\b', r'\byou know\b', r'\bso\b']

    def analyze_audio(self, audio_path: str):
        """
        Main pipeline to analyze an audio file.
        Returns a dictionary containing WPM, filler frequency, pitch variance, etc.
        """
        try:
            # 1. Transcription & Timestamps
            transcript_data = self._transcribe(audio_path)
            text = transcript_data.get("text", "")
            chunks = transcript_data.get("chunks", [])

            # 2. Acoustic Features (Librosa)
            pitch_variance, acoustic_confidence, jitter, shimmer = self._extract_acoustic_features(audio_path)

            # 3. Pacing (WPM)
            wpm = self._calculate_wpm(chunks, audio_path)

            # 4. Filler Words
            filler_count = self._count_filler_words(text)

            return {
                "transcript": text,
                "wpm_score": round(wpm, 2),
                "filler_frequency": filler_count,
                "pitch_variance_score": round(pitch_variance, 4),
                "acoustic_confidence": round(acoustic_confidence, 4),
                "jitter": round(jitter, 2),
                "shimmer": round(shimmer, 2),
                "status": "success"
            }
        except Exception as e:
            print(f"Error in Acoustic Engine: {e}")
            return {"status": "error", "message": str(e)}

    def _transcribe(self, audio_path: str):
        if self.use_local:
            return self.transcriber(audio_path)
        return {"text": "", "chunks": []}

    def _extract_acoustic_features(self, audio_path: str):
        """
        Extracts pitch (F0) variance and energy confidence using Librosa.
        High pitch variance indicates expressive speech; low indicates monotone.
        """
        # Load audio with librosa
        y, sr = librosa.load(audio_path, sr=16000)
        
        # Calculate Pitch (F0) using pyin
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, 
            fmin=librosa.note_to_hz('C2'), 
            fmax=librosa.note_to_hz('C7')
        )
        
        # Filter out unvoiced frames (NaNs)
        f0_voiced = f0[~np.isnan(f0)]
        
        if len(f0_voiced) > 0:
            pitch_variance = float(np.var(f0_voiced) / 1000.0) # Normalize slightly
        else:
            pitch_variance = 0.0
            
        # Acoustic confidence can be correlated with average voice probabilities
        acoustic_confidence = float(np.nanmean(voiced_probs)) if len(voiced_probs) > 0 else 0.0
        
        # Jitter approximation (frequency variation)
        if len(f0_voiced) > 1:
            f0_diff = np.abs(np.diff(f0_voiced))
            jitter = float(np.mean(f0_diff) / np.mean(f0_voiced)) * 100
        else:
            jitter = 0.0
            
        # Shimmer approximation (amplitude variation)
        rms = librosa.feature.rms(y=y)[0]
        if len(rms) > 1:
            rms_diff = np.abs(np.diff(rms))
            shimmer = float(np.mean(rms_diff) / np.mean(rms)) * 100
        else:
            shimmer = 0.0
        
        return pitch_variance, acoustic_confidence, jitter, shimmer

    def _calculate_wpm(self, chunks: list, audio_path: str):
        """
        Calculates Words Per Minute using Whisper's word-level timestamps.
        """
        if not chunks:
            return 0.0
            
        # Number of words is roughly the number of chunks returned by Whisper word timestamps
        word_count = len(chunks)
        
        # Get total duration
        duration_sec = librosa.get_duration(path=audio_path)
        duration_min = duration_sec / 60.0
        
        if duration_min > 0:
            return word_count / duration_min
        return 0.0

    def _count_filler_words(self, text: str):
        """
        Counts occurrences of filler words using regex.
        """
        count = 0
        text_lower = text.lower()
        for pattern in self.filler_words:
            matches = re.findall(pattern, text_lower)
            count += len(matches)
        return count

# Example usage for standalone testing
if __name__ == "__main__":
    import os
    engine = AcousticProsodyEngine()
    test_audio = "test_sample.wav"
    if os.path.exists(test_audio):
        results = engine.analyze_audio(test_audio)
        print("Analysis Results:", results)
    else:
        print(f"Provide a {test_audio} file in the directory to test.")
