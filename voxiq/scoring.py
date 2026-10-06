"""Turn a transcript into sub-scores. Each one has a status, a reason and the evidence behind it.

There is no overall grade. The thresholds are in config.py and are shown in the UI;
they are my choices from common coaching advice, not measured standards.
"""
from . import config, fillers, jd, star


def split_sentences(words: list) -> list:
    """Sentences as (first_word_index, last_word_index). Falls back to 25-word chunks if Whisper gave no punctuation."""
    out, start = [], 0
    for i, w in enumerate(words):
        if w.ends_sentence or i == len(words) - 1:
            out.append((start, i))
            start = i + 1
    if len(out) == 1 and len(words) > 40:
        out = [(i, min(i + 24, len(words) - 1)) for i in range(0, len(words), 25)]
    return out


def _without_fillers(words, a, b, filler_idx):
    out = []
    for i in range(a, b + 1):
        if i in filler_idx:
            if out and out[-1].endswith(","):
                out[-1] = out[-1][:-1]
            continue
        out.append(words[i].text)
    return " ".join(out).strip(" ,")


def _speech_minutes(words: list, duration: float) -> float:
    span = words[-1].end - words[0].start if words else 0
    return max(span if span > 1 else duration, 1.0) / 60.0


def _context(words, f, pad=4):
    a, b = max(0, f.first - pad), min(len(words), f.last + pad + 1)
    return " ".join(w.text for w in words[a:b])


def pace(words, duration):
    minutes = _speech_minutes(words, duration)
    wpm = round(len(words) / minutes)
    lo, hi = config.PACE_RANGE
    status = "met" if lo <= wpm <= hi else ("close" if lo - 20 <= wpm <= hi + 20 else "miss")
    if wpm < lo:
        reason = f"{wpm} words per minute is slower than the {lo} to {hi} range. Slow can sound careful, but long gaps lose people."
    elif wpm > hi:
        reason = f"{wpm} words per minute is faster than the {lo} to {hi} range. Fast speech is harder to follow, especially over a call."
    else:
        reason = f"{wpm} words per minute is inside the {lo} to {hi} range."
    return {"key": "pace", "title": "Pace", "status": status, "value": wpm, "unit": "words per minute",
            "reason": reason,
            "threshold": f"Target {lo} to {hi} words per minute, measured from your first word to your last. Within 20 of the range counts as close.",
            "evidence": {"words": len(words), "speaking_seconds": round(minutes * 60, 1)}}


def filler_check(words, found, duration):
    minutes = _speech_minutes(words, duration)
    per_min = round(len(found) / minutes, 1)
    mx = config.FILLERS_PER_MIN_MAX
    status = "met" if per_min <= mx else ("close" if per_min <= mx * 2 else "miss")
    by_label = {}
    for f in found:
        by_label[f.label] = by_label.get(f.label, 0) + 1
    if not found:
        reason = "No filler words found."
    else:
        top = ", ".join(f'"{k}" x{v}' for k, v in sorted(by_label.items(), key=lambda kv: -kv[1])[:4])
        reason = f"{len(found)} fillers, {per_min} per minute. Most common: {top}."
    return {"key": "fillers", "title": "Filler words", "status": status, "value": len(found), "unit": "fillers",
            "per_minute": per_min, "reason": reason,
            "threshold": (f"Target at most {mx:g} per minute. Up to {mx * 2:g} counts as close. "
                          "Words like \"actually\" and \"like\" count only when used as fillers, "
                          "so a few uses may be missed or wrongly counted. Whisper also drops some \"um\" and \"uh\"."),
            "evidence": {"by_label": by_label,
                         "items": [{"label": f.label, "start": round(f.start, 2), "end": round(f.end, 2),
                                    "context": _context(words, f), "first": f.first, "last": f.last} for f in found]}}


def star_check(summary):
    n = summary["present_count"]
    status = "met" if n == 4 else ("close" if n >= 3 else "miss")
    if n == 4:
        reason = "All four parts are there: Situation, Task, Action, Result."
    else:
        reason = "Missing: " + ", ".join(summary["missing"]) + ". " + " ".join(star.EXPLAIN[m] for m in summary["missing"][:2])
    return {"key": "star", "title": "STAR structure", "status": status, "value": n, "unit": "of 4 parts",
            "reason": reason,
            "threshold": ("A part counts as present when at least one sentence has a cue for it, for example "
                          "\"my job was\" for Task, \"as a result\" or a number for Result. The cue is shown next to each sentence. "
                          "The cues are patterns I wrote, so an answer can contain a part without using them."),
            "evidence": summary}


def jd_check(cov):
    if not cov["has_jd"]:
        return {"key": "jd", "title": "Job description coverage", "status": "skipped", "value": None, "unit": "",
                "reason": "No job description was added, so there is nothing to compare against.",
                "threshold": "Needs a pasted job description.", "evidence": cov}
    total, hit = len(cov["requirements"]), len(cov["mentioned"])
    share = hit / total if total else 0
    status = "met" if share >= 0.6 else ("close" if share >= 0.3 else "miss")
    miss = ", ".join(m["skill"] for m in cov["missing"][:6])
    reason = f"You mentioned {hit} of {total} requirements from the job description." + (f" Not mentioned: {miss}." if miss else "")
    return {"key": "jd", "title": "Job description coverage", "status": status, "value": hit, "unit": f"of {total} requirements",
            "reason": reason,
            "threshold": ("Requirements are the skills found in the job description. Met at 60% or more mentioned, close at 30%. "
                          "One answer is not expected to cover everything, so judge this against the question asked."),
            "evidence": cov}


def length_check(duration):
    lo, hi = config.LENGTH_RANGE
    status = "met" if lo <= duration <= hi else ("close" if lo - 20 <= duration <= hi + 30 else "miss")
    if duration < lo:
        reason = f"{duration:.0f} seconds is short for a behavioural answer. There may be room for the Result or more detail on what you did."
    elif duration > hi:
        reason = f"{duration:.0f} seconds is long. Interviewers often lose the thread after about two minutes."
    else:
        reason = f"{duration:.0f} seconds is inside the {lo} to {hi} second range."
    return {"key": "length", "title": "Length", "status": status, "value": round(duration), "unit": "seconds",
            "reason": reason,
            "threshold": f"Target {lo} to {hi} seconds for a behavioural question. Short factual questions can be shorter.",
            "evidence": {"seconds": round(duration, 1)}}


def analyse(words: list, duration: float, job_description: str = "", filler_config=None) -> dict:
    found = fillers.detect(words, filler_config)
    spans = split_sentences(words)
    filler_idx = {i for f in found for i in range(f.first, f.last + 1)}
    # cues are matched on the sentence without its fillers, so "I, um, wrote" still reads as "I wrote"
    sentences = [_without_fillers(words, a, b, filler_idx) for a, b in spans]
    keep = [(s, sp) for s, sp in zip(sentences, spans) if s]
    sentences, spans = [k[0] for k in keep], [k[1] for k in keep]
    star_summary = star.summarise(sentences)
    cov = jd.coverage(job_description, sentences)
    return {
        "transcript": " ".join(w.text for w in words),
        "words": [{"t": w.text, "s": round(w.start, 2), "e": round(w.end, 2), "f": i in filler_idx} for i, w in enumerate(words)],
        "sentences": [{"text": t, "first": a, "last": b} for t, (a, b) in zip(sentences, spans)],
        "duration": round(duration, 1),
        "checks": [pace(words, duration), filler_check(words, found, duration), star_check(star_summary),
                   jd_check(cov), length_check(duration)],
    }


def check(result: dict, key: str) -> dict:
    return next(c for c in result["checks"] if c["key"] == key)
