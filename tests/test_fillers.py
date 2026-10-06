import pytest

from voxiq.fillers import detect, load_config, words_from_text, FillerConfig


def labels(text, config=None):
    words = words_from_text(text)
    return [f.label for f in detect(words, config or load_config())]


@pytest.mark.parametrize("text,expected", [
    ("Um, I built a server.", ["um"]),
    ("I was uh working on it and umm it broke.", ["uh", "umm"]),
    ("So basically I fixed the bug.", ["so basically"]),
    ("It is basically a wrapper.", ["basically"]),
    ("Matlab I wrote the parser myself.", ["matlab"]),
    ("It was slow, you know, because of the join.", ["you know"]),
    ("Actually, I changed the schema.", ["actually"]),
    ("I changed it. Actually I rewrote it.", ["actually"]),
    ("It was kind of slow.", ["kind of"]),
    ("It was sort of a mess.", ["sort of"]),
    ("We tested it, na?", ["na"]),
    ("I fixed the login, right? Then I deployed.", ["right"]),
    ("It was, like, really slow.", ["like"]),
    ("The page was like loading forever.", ["like"]),
    ("Literally, nobody used it.", ["literally"]),
    ("Literally everything broke.", ["literally"]),
])
def test_filler_uses_are_counted(text, expected):
    assert labels(text) == expected


@pytest.mark.parametrize("text", [
    "Tell me what actually happened.",
    "It actually happened last week.",
    "I like Python and I would like to learn Rust.",
    "That is what kind of project it was.",
    "It was a different kind of problem.",
    "You know how to use Git.",
    "You know the team well.",
    "The word was literally translated.",
    "I turned right at the corner.",
    "It is right now in production.",
    "I did not know na the answer",
    "The model is basic and the sorting is fast.",
])
def test_non_filler_uses_are_ignored(text):
    assert labels(text) == []


def test_timestamps_follow_the_words():
    words = words_from_text("I was um stuck")
    for i, w in enumerate(words):
        w.start, w.end = float(i), i + 0.5
    (f,) = detect(words, load_config())
    assert (f.start, f.end) == (2.0, 2.5)


def test_so_basically_is_one_filler_not_two():
    assert labels("So basically it worked.") == ["so basically"]


def test_list_is_configurable():
    cfg = FillerConfig(always=["innit"], contextual={"actually": False})
    assert labels("Actually, it works innit", cfg) == ["innit"]


def test_custom_file(tmp_path):
    p = tmp_path / "f.json"
    p.write_text('{"always": ["yaar"], "contextual": {}}')
    assert labels("It broke yaar. Um.", load_config(str(p))) == ["yaar"]
