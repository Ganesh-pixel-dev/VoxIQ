import os
import requests
from groq import Groq
import warnings

warnings.filterwarnings("ignore")

from transformers import pipeline

class AdaptiveChatbot:
    def __init__(self, model_id="HuggingFaceTB/SmolLM-135M-Instruct", use_local=True):
        """
        Initializes the Adaptive Chatbot Engine.
        Uses an ultra-lightweight LLM (SmolLM ~270MB) for fast text generation
        without blowing up CPU/RAM usage.
        """
        self.use_local = use_local
        if self.use_local:
            print(f"Loading local Chatbot LLM ({model_id})...")
            self.generator = pipeline(
                "text-generation", 
                model=model_id,
                max_new_tokens=40,
                temperature=0.7,
                do_sample=True
            )
        else:
            self.generator = None

    def generate_follow_up(self, transcript: str, missing_flags: list, previous_question: str = "") -> str:
        """
        Generates an adaptive follow-up question based on the user's answer and the NLP flags.
        """
        if not self.use_local or not self.generator:
            return "Could you elaborate a bit more on the specific outcome of your actions? (Offline)"

        # Construct a universal messages payload
        user_content = f"My answer to the question '{previous_question}' was: {transcript}\n\n"
        
        if missing_flags and "STAR structure is solid" not in missing_flags[0]:
            user_content += f"My weaknesses according to the S.T.A.R. framework were: {', '.join(missing_flags)}.\nPlease ask a follow up question targeting these weaknesses."
        else:
            user_content += "My answer was solid. Please ask a deeper technical follow-up."

        messages = [
            {"role": "system", "content": "You are a technical interviewer. Ask exactly one concise follow-up question based on the user's answer. Keep it under 2 sentences."},
            {"role": "user", "content": user_content}
        ]

        try:
            # Generate response using automatic chat templating
            result = self.generator(messages)
            
            # The pipeline returns the entire conversation including the new assistant message at the end
            assistant_response = result[0]['generated_text'][-1]['content']
            
            return assistant_response.strip()
        except Exception as e:
            print(f"Chatbot Generation Error: {e}")
            return "Could you elaborate a bit more on the specific outcome of your actions? (Error fallback)"

if __name__ == "__main__":
    bot = AdaptiveChatbot()
    test_transcript = "I built a web server in Python."
    test_flags = ["Missing or weak Result/Outcome.", "Missing or weak Situation."]
    q = "Tell me about a time you had to build a system from scratch."
    print("Next Question:", bot.generate_follow_up(test_transcript, test_flags, q))
