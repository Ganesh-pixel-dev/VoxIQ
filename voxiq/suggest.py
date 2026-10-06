"""A suggested rewrite of an answer, written by the local LLM.

It is a suggestion. The model is told to use only facts from the transcript and to leave
placeholders where the answer has nothing to say, so it can't invent a result for you.
"""
from . import llm
from .scoring import check

SYSTEM = (
    "You are an interview coach for a student. Rewrite the answer so it is clearer and follows the STAR order "
    "(Situation, Task, Action, Result), in first person, in under 130 words. Use ONLY facts that are in the "
    "student's answer. Do not invent numbers, tools, results or names. Where a part is missing, write a "
    "placeholder in square brackets that says what to add, for example [add: what happened as a result, with a number if you have one]. "
    "Never write about the job description or about what the answer lacks, and do not describe what the student did beyond what they said. Remove filler words. Plain words, short sentences."
)


def weakest(result: dict) -> str:
    star = check(result, "star")
    if star["evidence"]["missing"]:
        return "The answer has no " + " or ".join(star["evidence"]["missing"]) + " part."
    fill = check(result, "fillers")
    if fill["status"] != "met":
        return f"Too many fillers ({fill['per_minute']} per minute)."
    jd = check(result, "jd")
    if jd["status"] in ("miss", "close"):
        return "It does not mention enough of the job requirements: " + ", ".join(m["skill"] for m in jd["evidence"]["missing"][:4]) + "."
    return "No clear weak spot. Tighten the wording."


def rewrite(question: str, result: dict, ask=llm.chat) -> dict:
    problem = weakest(result)
    text = ask(SYSTEM, f"Question: {question}\n\nStudent's answer (transcript):\n{result['transcript']}\n\nBiggest problem: {problem}")
    follow = ask(
        "You are an interviewer. Ask ONE short follow-up question about something specific the candidate said. Output only the question.",
        f"Question: {question}\nAnswer: {result['transcript']}",
    )
    return {"weakest": problem, "suggestion": text, "follow_up": follow.strip().split("\n")[0],
            "label": "Suggestion written by a local language model. These are not your words and it can be wrong. Keep what is true and say it your own way."}
