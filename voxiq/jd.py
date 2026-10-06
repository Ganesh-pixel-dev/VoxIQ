"""Job description coverage: which requirements did the answer mention, and which not."""
import re
from collections import Counter

from .skills import SKILLS

STOP = set("""the and for with that this from will you your are our have has can all any not but who what when where
their they them his her about into more than also able work working experience years year role team company
skills ability strong good knowledge understanding required preferred plus must should including such within across
using use used etc looking candidate candidates responsibilities requirements join build building help make need
needs new well part time job position applicants apply""".split())


def _pattern(alias: str) -> re.Pattern:
    return re.compile(r"(?<![\w+#])" + re.escape(alias) + r"(?![\w+#])", re.I)


_COMPILED = {name: [_pattern(a) for a in aliases] for name, aliases in SKILLS.items()}


def find_skills(text: str) -> dict:
    """Canonical skill -> the first matching snippet in `text`."""
    found = {}
    for name, pats in _COMPILED.items():
        for p in pats:
            m = p.search(text)
            if m:
                found[name] = text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ").strip()
                break
    return found


def requirements(jd: str, limit: int = 15) -> list:
    """Requirement terms from a job description: known skills first, then repeated keywords."""
    jd = jd.strip()
    if not jd:
        return []
    skills = list(find_skills(jd))
    if len(skills) < 4:
        words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{3,}", jd.lower().replace(".", " ")) if w not in STOP]
        known = " ".join(skills).lower()
        for w, c in Counter(words).most_common(20):
            if c >= 2 and w not in known and w not in skills:
                skills.append(w)
    return skills[:limit]


def coverage(jd: str, sentences: list) -> dict:
    """Which JD requirements the answer mentions (with the sentence) and which it doesn't."""
    reqs = requirements(jd)
    mentioned, missing = [], []
    for r in reqs:
        pats = _COMPILED.get(r) or [_pattern(r)]
        hit = next((s for s in sentences if any(p.search(s) for p in pats)), None)
        (mentioned if hit else missing).append({"skill": r, "sentence": hit} if hit else {"skill": r})
    return {"requirements": reqs, "mentioned": mentioned, "missing": missing, "has_jd": bool(reqs)}
