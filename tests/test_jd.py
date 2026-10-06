from voxiq.jd import coverage, find_skills, requirements

JD = """We need a backend developer. Requirements: Python, Django, SQL, REST APIs,
Git and Docker. Good communication and teamwork."""


def test_requirements_pulled_from_jd():
    r = requirements(JD)
    for s in ["Python", "Django", "SQL", "Git", "Docker", "Communication", "Teamwork"]:
        assert s in r


def test_coverage_splits_mentioned_and_missing():
    sents = ["I built the backend in Django with a Postgres database.", "We used GitHub for reviews."]
    c = coverage(JD, sents)
    got = {m["skill"]: m["sentence"] for m in c["mentioned"]}
    assert got["Django"] == sents[0] and got["SQL"] == sents[0] and got["Git"] == sents[1]
    missing = [m["skill"] for m in c["missing"]]
    assert "Docker" in missing and "Python" in missing and "Django" not in missing


def test_spoken_variants_match():
    assert "SQL" in find_skills("I wrote queries in sequel")
    assert "Node.js" in find_skills("backend in node js")


def test_word_boundaries():
    assert "Java" not in find_skills("I like JavaScript")
    assert "Go" not in find_skills("let's go ahead")
    assert "C++" in find_skills("a parser in C++ and")


def test_fallback_to_repeated_keywords():
    r = requirements("We value kaizen. Kaizen drives our kitchen. Kitchen robots matter.")
    assert "kaizen" in r


def test_no_jd():
    c = coverage("", ["anything"])
    assert not c["has_jd"] and c["mentioned"] == []
