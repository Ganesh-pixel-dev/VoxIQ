import numpy as np
from sklearn.ensemble import RandomForestRegressor
import warnings

warnings.filterwarnings("ignore")

class MLScoringEngine:
    def __init__(self):
        """
        Initializes the Machine Learning Scoring Engine.
        Uses a RandomForestRegressor. Since we lack a massive labeled dataset,
        we pre-train it with synthetic data to establish logical feature weights 
        and prove the pipeline works end-to-end.
        """
        print("Initializing ML Scoring Engine...")
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.dataset_path = "dataset/interview_data.csv"
        self._train_model()

    def _train_model(self):
        """
        Trains the model on a dataset representing various interview performances.
        Feature Vector: [
            wpm_diff (distance from optimal 140 WPM), 
            filler_freq, 
            pitch_variance, 
            acoustic_confidence,
            star_s, star_t, star_a, star_r, 
            keyword_relevance
        ]
        """
        import pandas as pd
        import os
        
        if not os.path.exists(self.dataset_path):
            print(f"Warning: Dataset not found at {self.dataset_path}. Falling back to basic synthetic data.")
            self._train_fallback_model()
            return
            
        print(f"Loading dataset from {self.dataset_path}...")
        try:
            df = pd.read_csv(self.dataset_path)
            
            # The exact order matters and must match predict_score
            feature_cols = [
                'wpm_diff', 
                'filler_frequency', 
                'pitch_variance', 
                'acoustic_confidence',
                'star_s', 'star_t', 'star_a', 'star_r', 
                'keyword_relevance'
            ]
            
            X = df[feature_cols].values
            y = df['interview_score'].values
            
            print(f"Training model on {len(X)} samples...")
            self.model.fit(X, y)
            print("Model trained successfully.")
            
        except Exception as e:
            print(f"Error training model from dataset: {e}")
            self._train_fallback_model()

    def _train_fallback_model(self):
        """Fallback small synthetic dataset if CSV is missing."""
        print("Training fallback model...")
        x1 = [0.0, 0, 1.2, 0.95, 1.0, 1.0, 1.0, 1.0, 0.8]
        y1 = 98.0
        x2 = [20.0, 2, 0.8, 0.85, 1.0, 1.0, 1.0, 0.0, 0.6]
        y2 = 75.0
        x3 = [80.0, 15, 0.1, 0.4, 0.2, 0.0, 0.2, 0.0, 0.1]
        y3 = 25.0
        x4 = [40.0, 5, 0.5, 0.7, 0.6, 0.5, 0.7, 0.4, 0.4]
        y4 = 55.0
        x5 = [10.0, 1, 1.0, 0.9, 0.9, 0.9, 0.9, 0.9, 0.7]
        y5 = 92.0

        X = np.array([x1, x2, x3, x4, x5])
        y = np.array([y1, y2, y3, y4, y5])

        self.model.fit(X, y)

    def predict_score(self, dl_results: dict, nlp_results: dict) -> float:
        """
        Predicts the overall Interview Readiness score (0-100) based on DL and NLP metrics.
        """
        try:
            # 1. Acoustic Features
            wpm = dl_results.get("wpm_score", 140)
            # Optimal WPM is around 140. We calculate the absolute difference.
            wpm_diff = abs(140 - wpm) if wpm > 0 else 140.0 
            
            filler = dl_results.get("filler_frequency", 0)
            pitch = dl_results.get("pitch_variance_score", 0.0)
            conf = dl_results.get("acoustic_confidence", 0.0)
            
            # 2. NLP Features
            s = nlp_results.get("star_s_score", 0.0)
            t = nlp_results.get("star_t_score", 0.0)
            a = nlp_results.get("star_a_score", 0.0)
            r = nlp_results.get("star_r_score", 0.0)
            kw = nlp_results.get("keyword_relevance_score", 0.0)
            
            # Create feature vector matching training data
            features = np.array([[wpm_diff, filler, pitch, conf, s, t, a, r, kw]])
            
            # Predict
            score = self.model.predict(features)[0]
            
            # Bound the score between 0 and 100
            final_score = max(0.0, min(100.0, score))
            return round(final_score, 1)
        
        except Exception as e:
            print(f"ML Engine Error: {e}")
            return 0.0

if __name__ == "__main__":
    ml = MLScoringEngine()
    test_dl = {"wpm_score": 135, "filler_frequency": 1, "pitch_variance_score": 0.9, "acoustic_confidence": 0.9}
    test_nlp = {"star_s_score": 0.9, "star_t_score": 0.9, "star_a_score": 1.0, "star_r_score": 0.9, "keyword_relevance_score": 0.8}
    print("Final Score:", ml.predict_score(test_dl, test_nlp))
