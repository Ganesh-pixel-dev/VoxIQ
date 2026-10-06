import pytest

from voxiq import llm
from voxiq.questions import generate
from voxiq.resume import ResumeError, extract_text, parse

RESUME = """Ganesh Bera
ganesh@example.com

PROJECTS
Drishti AI | Python, OpenCV
- Detects edited photos with error level analysis.
Mnemo - note search
- BM25 search over my own notes.

SKILLS
Languages: Python, JavaScript, C++
Tools: Git, Django

EDUCATION
BSc Computer Science
"""


def test_parse_finds_projects_skills_and_numbers_lines():
    r = parse(RESUME)
    assert [p["name"] for p in r.projects] == ["Drishti AI", "Mnemo"]
    assert r.projects[0]["line"] == 4 and r.lines[3]["text"].startswith("Drishti AI")
    assert r.skills == ["Python", "JavaScript", "C++", "Git", "Django"]


def test_txt_extract_and_bad_types():
    assert "Drishti" in extract_text(RESUME.encode(), "cv.txt")
    with pytest.raises(ResumeError):
        extract_text(b"x", "cv.exe")
    with pytest.raises(ResumeError):
        extract_text(b"not a pdf", "cv.pdf")


def test_docx_roundtrip(tmp_path):
    import docx
    d = docx.Document()
    for line in RESUME.splitlines():
        d.add_paragraph(line)
    p = tmp_path / "cv.docx"
    d.save(p)
    assert parse(extract_text(p.read_bytes(), "cv.docx")).projects[0]["name"] == "Drishti AI"


def test_too_little_text():
    with pytest.raises(ResumeError):
        parse("hello")


def test_llm_gets_one_project_at_a_time_and_source_line_is_the_projects_own():
    r = parse(RESUME)
    seen = []

    def fake(system, user):
        seen.append(user)
        if user.startswith("Drishti"):
            return {"question": "You list Drishti AI. How did you measure its accuracy?"}
        return {"question": "How did you test the ranking?"}

    out = generate(r, "Python Django Docker", ask=fake)
    assert out["source"] == "llm"
    assert "Mnemo" not in seen[0] and "BM25" in seen[1] and "Detects edited photos" in seen[0]
    first, second = out["questions"][:2]
    assert first["source_line"] == 4 and first["source_text"].startswith("Drishti AI") and first["origin"] == "llm"
    assert second["question"].startswith("On Mnemo:") and second["source_line"] == 6
    gap = out["questions"][2]
    assert gap["kind"] == "jd" and "Docker" in gap["question"] and gap["origin"] == "template"
    assert len(out["hr"]) >= 5 and out["hr"][0]["kind"] == "hr"


def test_unusable_llm_answer_for_one_project_uses_a_labelled_template():
    out = generate(parse(RESUME), "", ask=lambda s, u: {"oops": 1})
    assert out["source"] == "template"
    assert all(q["origin"] == "template" for q in out["questions"])


def test_fallback_templates_when_llm_down():
    def down(system, user):
        raise llm.LLMUnavailable("Ollama is not reachable")

    out = generate(parse(RESUME), "We need Python and Docker", ask=down)
    assert out["source"] == "template" and "not reachable" in out["note"]
    assert all(q["origin"] == "template" for q in out["questions"])
    texts = " ".join(q["question"] for q in out["questions"])
    assert "Drishti AI" in texts and "Docker" in texts
