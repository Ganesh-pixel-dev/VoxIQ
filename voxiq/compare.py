"""What changed between two attempts at the same question."""
from . import config
from .scoring import check


def _distance(value, lo, hi):
    return 0 if lo <= value <= hi else min(abs(value - lo), abs(value - hi))


def _row(label, before, after, better, unit=""):
    if before == after:
        verdict = "same"
    else:
        verdict = "better" if better(before, after) else "worse"
    return {"label": label, "before": before, "after": after, "unit": unit, "verdict": verdict}


def compare(a: dict, b: dict) -> dict:
    """a is the earlier attempt, b the later one."""
    fa, fb = check(a, "fillers"), check(b, "fillers")
    pa, pb = check(a, "pace"), check(b, "pace")
    sa, sb = check(a, "star"), check(b, "star")
    ja, jb = check(a, "jd"), check(b, "jd")
    la, lb = check(a, "length"), check(b, "length")
    plo, phi = config.PACE_RANGE
    llo, lhi = config.LENGTH_RANGE

    rows = [
        _row("Fillers per minute", fa["per_minute"], fb["per_minute"], lambda x, y: y < x),
        _row("Filler count", fa["value"], fb["value"], lambda x, y: y < x),
        _row("STAR parts present", sa["value"], sb["value"], lambda x, y: y > x, "of 4"),
    ]
    both_jd = ja["status"] != "skipped" and jb["status"] != "skipped"
    if both_jd:
        rows.append(_row("Job requirements mentioned", ja["value"], jb["value"], lambda x, y: y > x))
    rows.append(_row("Pace (words per minute)", pa["value"], pb["value"],
                     lambda x, y: _distance(y, plo, phi) < _distance(x, plo, phi)))
    rows.append(_row("Length (seconds)", la["value"], lb["value"],
                     lambda x, y: _distance(y, llo, lhi) < _distance(x, llo, lhi)))

    notes = []
    parts_a, parts_b = sa["evidence"]["parts"], sb["evidence"]["parts"]
    gained = [p for p in parts_b if parts_b[p]["present"] and not parts_a[p]["present"]]
    lost = [p for p in parts_a if parts_a[p]["present"] and not parts_b[p]["present"]]
    if gained:
        notes.append("Added STAR parts: " + ", ".join(gained) + ".")
    if lost:
        notes.append("Lost STAR parts: " + ", ".join(lost) + ".")
    if both_jd:
        ma = {m["skill"] for m in ja["evidence"]["mentioned"]}
        mb = {m["skill"] for m in jb["evidence"]["mentioned"]}
        if mb - ma:
            notes.append("Now mentioned from the job description: " + ", ".join(sorted(mb - ma)) + ".")
        if ma - mb:
            notes.append("No longer mentioned: " + ", ".join(sorted(ma - mb)) + ".")
    ca, cb = fa["evidence"]["by_label"], fb["evidence"]["by_label"]
    for label in sorted(set(ca) | set(cb)):
        if ca.get(label, 0) != cb.get(label, 0):
            notes.append(f'"{label}": {ca.get(label, 0)} to {cb.get(label, 0)}.')
    return {
        "rows": rows,
        "notes": notes,
        "better": sum(r["verdict"] == "better" for r in rows),
        "worse": sum(r["verdict"] == "worse" for r in rows),
    }
