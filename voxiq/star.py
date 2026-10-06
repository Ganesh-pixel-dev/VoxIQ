"""STAR structure: label each sentence Situation, Task, Action or Result, then say which parts are present.

I first tried a zero-shot NLI model (DistilBERT-MNLI, what the old version used). On a handful of
test sentences it called almost everything "action", including "Um, so yeah that is about it", so
I replaced it with cue phrases. Each label now comes with the cue that triggered it, which
makes it checkable. The cues are English patterns I wrote; they miss answers that don't use them.
"""
import re
from dataclasses import dataclass

PARTS = ("Situation", "Task", "Action", "Result")
EXPLAIN = {
    "Situation": "The background: where, when, what the project or team was.",
    "Task": "Your responsibility or the goal you had to reach.",
    "Action": "What you personally did.",
    "Result": "What happened because of it, ideally with something checkable.",
}

_RULES = [
    ("Result", r"\bas a result\b|\bresult(ed|ing)? in\b|\bthe (result|outcome)\b|\bended up\b|\bin the end\b|\bfinally\b|"
               r"\b(reduced|increased|improved|dropped|cut|saved|boosted|raised|lowered|doubled)\b|\bwent from\b|\bfrom \d[\w.,%]* to \d|"
               r"\d\s?%|\bpercent\b|\b(was|got|were) (selected|approved|accepted|appreciated|adopted)\b|\bwon\b|\bhelped (us|the team|them)\b"),
    ("Task", r"\bmy (job|role|task|responsibility|goal)\b|\bi (was|got) (asked|responsible|supposed|assigned|tasked|expected)\b|"
             r"\b(had|needed|have) to\b|\bthe (goal|aim|objective|target) was\b|\bi wanted to\b|\bwe needed\b|\bi decided to\b"),
    ("Situation", r"\b(last|this) (year|semester|summer|month)\b|\bin my (\w+ )?(year|semester|internship|class)\b|\bat (college|my college|university|work|my internship)\b|"
                  r"\bduring\b|\bwhen i was\b|\bback then\b|\bour (team|project|class|college)\b|\bwe were (working|building|doing)\b|"
                  r"\b(kept|was|were|used to) (crashing|failing|slow|breaking|broken|missing)\b|\bthe problem was\b|\bthe issue was\b|\bthere was a\b"),
    ("Action", r"\b(i|we) (just |then |also |first |next |personally |quickly |really )?(\w+ed|built|wrote|used|made|chose|ran|set|did|took|began|led|taught|learnt|"
               r"found|put|split|sent|got|came|gave|kept|read|drew|tried)\b"),
]
RULES = [(part, re.compile(rx, re.I)) for part, rx in _RULES]


def label_sentence(sentence: str):
    """Return (part, cue) for the first matching rule, or (None, '')."""
    for part, rx in RULES:
        m = rx.search(sentence)
        if m:
            return part, m.group(0).strip()
    return None, ""


@dataclass
class Labelled:
    index: int
    text: str
    part: str | None
    cue: str


def label_all(sentences: list) -> list:
    return [Labelled(i, s, *label_sentence(s)) for i, s in enumerate(sentences)]


def summarise(sentences: list) -> dict:
    labelled = label_all(sentences)
    parts = {}
    for p in PARTS:
        ev = [l for l in labelled if l.part == p]
        parts[p] = {
            "present": bool(ev),
            "explain": EXPLAIN[p],
            "sentences": [{"index": l.index, "text": l.text, "cue": l.cue} for l in ev],
        }
    missing = [p for p in PARTS if not parts[p]["present"]]
    return {
        "parts": parts,
        "missing": missing,
        "present_count": len(PARTS) - len(missing),
        "labels": [{"index": l.index, "part": l.part, "cue": l.cue} for l in labelled],
    }
