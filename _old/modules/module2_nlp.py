import spacy
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings("ignore")

class SemanticSTARAnalyzer:
    def __init__(self, model_id="typeform/distilbert-base-uncased-mnli"):
        """
        Initializes the NLP Engine for STAR method classification and keyword matching.
        Uses a lightweight distilbert model (~250MB) for extremely fast zero-shot classification on CPU.
        """
        print(f"Loading local Zero-Shot Classifier ({model_id})...")
        self.classifier = pipeline("zero-shot-classification", model=model_id)
        
        # We need a basic sentence tokenizer. Since spacy's en_core_web_sm might need to be downloaded,
        # we'll use a simple fallback if it's not installed, but try to use spacy if possible.
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Spacy model 'en_core_web_sm' not found. Falling back to basic sentence splitting.")
            self.nlp = None

        self.star_labels = ["Situation", "Task", "Action", "Result", "Irrelevant"]

    def analyze_transcript(self, transcript: str, job_description: str = ""):
        """
        Analyzes the transcript for STAR completeness and keyword relevance.
        """
        if not transcript or not transcript.strip():
            return {
                "star_s_score": 0.0,
                "star_t_score": 0.0,
                "star_a_score": 0.0,
                "star_r_score": 0.0,
                "keyword_relevance_score": 0.0,
                "missing_flags": ["No transcript provided."],
                "status": "error"
            }

        sentences = self._split_into_sentences(transcript)
        
        # 1. STAR Classification
        star_scores = self._classify_star(sentences)
        
        # 2. Missing Flags
        missing_flags = self._generate_missing_flags(star_scores)
        
        # 3. Keyword Relevance
        keyword_score = 0.0
        if job_description:
            keyword_score = self._calculate_keyword_relevance(transcript, job_description)

        return {
            "star_s_score": round(star_scores.get("Situation", 0.0), 4),
            "star_t_score": round(star_scores.get("Task", 0.0), 4),
            "star_a_score": round(star_scores.get("Action", 0.0), 4),
            "star_r_score": round(star_scores.get("Result", 0.0), 4),
            "keyword_relevance_score": round(keyword_score, 4),
            "missing_flags": missing_flags,
            "status": "success"
        }

    def _split_into_sentences(self, text: str):
        if self.nlp:
            doc = self.nlp(text)
            return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5]
        else:
            # Basic fallback splitting
            import re
            sentences = re.split(r'(?<=[.!?]) +', text)
            return [s.strip() for s in sentences if len(s.strip()) > 5]

    def _classify_star(self, sentences: list):
        """
        Classifies each sentence into the STAR categories and aggregates the scores.
        """
        aggregate_scores = {label: 0.0 for label in self.star_labels}
        
        if not sentences:
            return aggregate_scores

        for sentence in sentences:
            # Perform zero-shot classification
            result = self.classifier(sentence, self.star_labels)
            
            # Get the top predicted label and its score
            top_label = result['labels'][0]
            top_score = result['scores'][0]
            
            # If the confidence is somewhat high, add it to the aggregate
            if top_score > 0.35:
                aggregate_scores[top_label] += top_score
                
        # Normalize the scores relative to the number of sentences (max cap at 1.0)
        num_sents = len(sentences)
        for label in aggregate_scores:
            aggregate_scores[label] = min(1.0, aggregate_scores[label] / max(1, (num_sents / 4)))

        return aggregate_scores

    def _generate_missing_flags(self, star_scores: dict):
        """
        Determines which parts of the STAR method are missing or weak.
        """
        flags = []
        threshold = 0.2  # If the normalized score is below 0.2, consider it weak/missing

        if star_scores.get("Situation", 0) < threshold:
            flags.append("Missing or weak Context/Situation.")
        if star_scores.get("Task", 0) < threshold:
            flags.append("Missing or weak Task explanation.")
        if star_scores.get("Action", 0) < threshold:
            flags.append("Missing or weak Action description.")
        if star_scores.get("Result", 0) < threshold:
            flags.append("Missing or weak Result/Outcome.")

        if not flags:
            flags.append("STAR structure is solid.")

        return flags

    def _calculate_keyword_relevance(self, transcript: str, job_description: str):
        """
        Calculates cosine similarity between the transcript and the job description using TF-IDF.
        """
        vectorizer = TfidfVectorizer(stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform([transcript, job_description])
            # tfidf_matrix[0] is transcript, tfidf_matrix[1] is JD
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0])
        except ValueError:
            # Happens if texts are empty or only contain stop words
            return 0.0

if __name__ == "__main__":
    analyzer = SemanticSTARAnalyzer()
    test_text = "The server was crashing every hour. I was tasked to fix it. I analyzed the logs, found a memory leak in the database query, and rewrote the SQL join. The crashing stopped and CPU usage dropped by 40%."
    test_jd = "Looking for a backend engineer experienced with SQL, database optimization, and debugging server crashes."
    
    res = analyzer.analyze_transcript(test_text, test_jd)
    print(res)
