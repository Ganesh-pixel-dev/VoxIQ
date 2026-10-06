"""Filler word detection on timestamped words.

Whisper gives words with start/end times. A word is only a filler by how it is used,
so the contextual rules look at neighbours and punctuation ("actually" opening a
sentence is a filler, "what actually happened" is not). These are heuristics, tested
on the examples in tests/test_fillers.py, not a measured detector.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_FILE = Path(__file__).with_name("fillers_default.json")
CLAUSE_END = (".", "?", "!", ",", ";", ":")
SENTENCE_END = (".", "?", "!")


@dataclass
class Word:
    text: str
    start: float = 0.0
    end: float = 0.0

    @property
    def norm(self) -> str:
        return re.sub(r"^[^\w']+|[^\w']+$", "", self.text.lower())

    @property
    def ends_clause(self) -> bool:
        return self.text.rstrip("\"')").endswith(CLAUSE_END)

    @property
    def ends_sentence(self) -> bool:
        return self.text.rstrip("\"')").endswith(SENTENCE_END)


@dataclass
class Filler:
    label: str
    first: int  # index of first word
    last: int   # index of last word
    start: float
    end: float


@dataclass
class FillerConfig:
    always: list = field(default_factory=list)
    contextual: dict = field(default_factory=dict)


def load_config(path: str = "") -> FillerConfig:
    p = Path(path) if path else DEFAULT_FILE
    data = json.loads(p.read_text(encoding="utf-8"))
    return FillerConfig(
        always=[a.lower().strip() for a in data.get("always", [])],
        contextual={k.lower(): bool(v) for k, v in data.get("contextual", {}).items()},
    )


NOT_FILLER_BEFORE_KIND = {
    "what", "which", "this", "that", "these", "those", "same", "a", "an", "any", "some", "every",
    "each", "different", "another", "the", "one", "other", "whatever", "all", "no", "of", "my", "your",
    "kinds", "sorts",
}
KNOW_COMPLEMENT = {
    "how", "what", "that", "who", "where", "when", "why", "if", "whether", "which", "about",
    "the", "a", "an", "my", "your", "his", "her", "their", "our", "this", "these", "those",
}
LIKE_LEAD_IN = {"was", "were", "is", "are", "it's", "i'm", "he's", "she's", "and", "but", "so", "just", "be", "been"}
LIKE_VERB_BEFORE = {"would", "i", "we", "you", "they", "looks", "look", "feel", "feels", "something", "much", "more", "most"}
LITERALLY_INTENSIFIED = {
    "i", "we", "it", "they", "he", "she", "every", "everything", "everyone", "everybody",
    "nothing", "nobody", "so", "just", "like", "my", "the", "no",
}


def _at(words, i):
    return words[i] if 0 <= i < len(words) else None


def _sentence_start(words, i):
    p = _at(words, i - 1)
    return p is None or p.ends_sentence


def _contextual(name, words, i):
    """Number of words the filler spans if words[i:] is a filler use of `name`, else 0."""
    parts = name.split()
    span = len(parts)
    if [w.norm for w in words[i:i + span]] != parts:
        return 0
    j = i + span - 1
    if any(w.ends_clause for w in words[i:j]):
        return 0
    p, n = _at(words, i - 1), _at(words, j + 1)
    pn, nn = (p.norm if p else ""), (n.norm if n else "")
    after_clause = p is not None and p.ends_clause
    before_clause = words[j].ends_clause
    opens = _sentence_start(words, i) or after_clause

    if name == "like":
        if pn in LIKE_VERB_BEFORE:
            return 0
        if nn == "to" and not after_clause:
            return 0
        return span if (after_clause or before_clause or pn in LIKE_LEAD_IN) else 0
    if name == "you know":
        if before_clause or after_clause:
            return span
        return span if nn and nn not in KNOW_COMPLEMENT else 0
    if name == "actually":
        return span if (opens or before_clause) else 0
    if name == "literally":
        return span if (opens or before_clause or nn in LITERALLY_INTENSIFIED) else 0
    if name in ("kind of", "sort of"):
        return 0 if pn in NOT_FILLER_BEFORE_KIND else span
    if name == "na":
        return span if (before_clause or n is None) else 0
    if name == "right":
        return span if words[j].text.rstrip("\"'").endswith("?") else 0
    return 0


def detect(words: list, config: FillerConfig | None = None) -> list:
    config = config or load_config()
    always = sorted(config.always, key=lambda s: -len(s.split()))
    contextual = sorted((k for k, on in config.contextual.items() if on), key=lambda s: -len(s.split()))
    found, i = [], 0
    while i < len(words):
        hit = None
        for phrase in always:
            parts = phrase.split()
            if [w.norm for w in words[i:i + len(parts)]] == parts:
                hit = (phrase, len(parts))
                break
        if not hit:
            for name in contextual:
                span = _contextual(name, words, i)
                if span:
                    hit = (name, span)
                    break
        if hit:
            label, span = hit
            found.append(Filler(label, i, i + span - 1, words[i].start, words[i + span - 1].end))
            i += span
        else:
            i += 1
    return found


def words_from_text(text: str) -> list:
    """Words without timing, for tests and typed answers."""
    return [Word(t) for t in text.split()]
