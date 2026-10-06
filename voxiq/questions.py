"""Interview questions grounded in the resume and the job description.

An LLM (Ollama) writes them from the numbered resume lines and must say which line each one
came from. Lines that don't exist are dropped, so a question can't cite something that isn't there.
If the LLM is down, I fall back to templates built from the project names and skills, labelled as such.
"""
from . import config, llm
from . import jd as jdmod
from .resume import Resume

HR_QUESTIONS = [
    "Tell me about yourself.",
    "Why do you want this role?",
    "Tell me about a time you worked in a team and something went wrong.",
    "What is your biggest weakness, and what are you doing about it?",
    "Describe a time you had to learn something quickly.",
    "Where do you see yourself in three years?",
]

SYSTEM = (
    "You write one interview question for a student preparing for campus placements. "
    "You get a project from their resume. Ask about a decision, a measurement, a bug or a trade-off, "
    "using only details written in the project text. Name the project. Do not ask what the project is. "
    "Do not invent problems the text does not mention. "
    "Example of the style: 'You built a spam detector with Naive Bayes. How did you check it worked on emails it had not seen?' "
    'Reply as JSON: {"question": "..."}.'
)


def _line_with(resume: Resume, term: str) -> int:
    return next((l["n"] for l in resume.lines if not l["heading"] and term.lower() in l["text"].lower()), 0)


def _fallback(resume: Resume, jd_text: str, count: int) -> list:
    qs = []
    for p in resume.projects:
        qs.append({"question": f"You list {p['name']}. What problem did it solve, and what was your part in it?", "source_line": p["line"], "kind": "resume"})
        qs.append({"question": f"What was the hardest bug or decision in {p['name']}, and how did you handle it?", "source_line": p["line"], "kind": "resume"})
    for req in jdmod.requirements(jd_text)[:6]:
        line = _line_with(resume, req)
        if line:
            qs.append({"question": f"The role asks for {req}. Tell me about something you built or fixed using it.", "source_line": line, "kind": "jd"})
        else:
            qs.append({"question": f"The role asks for {req}, which I don't see on your resume. How would you get up to speed on it?", "source_line": 0, "kind": "jd"})
    for s in resume.skills[:3]:
        qs.append({"question": f"You list {s} as a skill. Where have you actually used it?", "source_line": _line_with(resume, s), "kind": "resume"})
    # interleave so projects and requirements both show up in a short list
    jd_qs = [q for q in qs if q["kind"] == "jd"]
    rest = [q for q in qs if q["kind"] != "jd"]
    mixed = []
    while (jd_qs or rest) and len(mixed) < count:
        for bucket in (rest, jd_qs):
            if bucket and len(mixed) < count:
                mixed.append(bucket.pop(0))
    return mixed


def _block(resume: Resume, project: dict) -> str:
    """The project's own line plus the bullets under it, up to the next project or heading."""
    out = []
    for l in resume.lines:
        if l["n"] < project["line"]:
            continue
        if l["n"] > project["line"] and (l["heading"] or any(l["n"] == p["line"] for p in resume.projects)):
            break
        out.append(l["text"])
    return "\n".join(out)


def _jd_gap_questions(resume: Resume, jd_text: str, limit: int = 2) -> list:
    qs = []
    for req in jdmod.requirements(jd_text):
        if len(qs) >= limit:
            break
        if _line_with(resume, req):
            continue
        qs.append({"question": f"The role asks for {req}, which I don't see on your resume. Have you worked with it, or how would you get up to speed?",
                   "source_line": 0, "kind": "jd", "origin": "template"})
    return qs


def generate(resume: Resume, jd_text: str, count: int = 8, ask=llm.chat_json) -> dict:
    """One LLM call per project, so each question can only draw on that project's own lines."""
    qs, note = [], ""
    for p in resume.projects[:6]:
        try:
            raw = ask(SYSTEM, _block(resume, p))
            text = raw.get("question", "").strip() if isinstance(raw, dict) else ""
        except llm.LLMUnavailable as e:
            note = str(e)
            break
        if len(text) >= 15 and text.endswith("?"):
            if p["name"].lower() not in text.lower():
                text = f"On {p['name']}: {text}"
            qs.append({"question": text, "source_line": p["line"], "kind": "resume", "origin": "llm"})
        else:
            qs.append({"question": f"You list {p['name']}. How did you check that it worked?", "source_line": p["line"],
                       "kind": "resume", "origin": "template"})
    if note or not qs:
        qs = _fallback(resume, jd_text, count)
        for q in qs:
            q["origin"] = "template"
    else:
        qs = (qs + _jd_gap_questions(resume, jd_text))[:count]
    line_text = {l["n"]: l["text"] for l in resume.lines}
    for q in qs:
        q["source_text"] = line_text.get(q["source_line"], "")
    source = "llm" if any(q["origin"] == "llm" for q in qs) else "template"
    if source == "template" and not note:
        note = "The model did not give usable questions, so these are built from templates."
    hr = [{"question": t, "source_line": 0, "source_text": "", "kind": "hr", "origin": "standard"} for t in HR_QUESTIONS]
    return {"source": source, "note": note, "model": config.LLM_MODEL if source == "llm" else None, "questions": qs, "hr": hr}
