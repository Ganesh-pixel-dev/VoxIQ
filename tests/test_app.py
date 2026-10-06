import pytest
from fastapi.testclient import TestClient

from voxiq import config, llm, scoring
from voxiq.app import create_app
from voxiq.fillers import words_from_text
from voxiq.transcribe import AudioError, Transcript

RESUME = b"""Ganesh
ganesh@example.com
PROJECTS
Drishti AI | Python
- Finds edited photos.
SKILLS
Python, Django
"""

FIRST = ("Um, last year I was in my final year at college. Basically my job was to build a photo checker. "
         "So basically I wrote the analysis code in Python, you know, and tested it. It was kind of slow.")
SECOND = ("Last year I was in my final year at college. My job was to build a photo checker. "
          "I wrote the analysis code in Python and Django and tested it on forty images. As a result the checker caught 38 of 40 edits.")


class FakeTranscriber:
    model_name, device = "fake", "cpu"

    def __init__(self):
        self.texts = [FIRST, SECOND]
        self.error = None

    def transcribe(self, path):
        if self.error:
            raise self.error
        words = words_from_text(self.texts.pop(0))
        for i, w in enumerate(words):
            w.start, w.end = i * 0.5, i * 0.5 + 0.4
        return Transcript(words, words[-1].end + 1)


def llm_down(system, user, *a, **k):
    raise llm.LLMUnavailable("Ollama is not reachable")


@pytest.fixture
def setup(tmp_path):
    t = FakeTranscriber()
    app = create_app(transcriber=t, ask_json=llm_down, ask_text=llm_down, data_dir=tmp_path)
    return TestClient(app), t


def post_audio(client, name="a.wav", data=b"RIFFxxxx", question="Tell me about Drishti AI.", jd="Python, Django, Docker"):
    return client.post("/api/analyze", files={"audio": (name, data, "audio/wav")},
                       data={"question": question, "job_description": jd})


def test_analyze_returns_all_five_checks_and_no_overall_score(setup):
    client, _ = setup
    r = post_audio(client)
    assert r.status_code == 200
    body = r.json()
    assert [c["key"] for c in body["result"]["checks"]] == ["pace", "fillers", "star", "jd", "length"]
    assert "score" not in body["result"] and body["attempt_number"] == 1 and body["compare"] is None
    fillers = next(c for c in body["result"]["checks"] if c["key"] == "fillers")
    assert fillers["evidence"]["by_label"] == {"um": 1, "so basically": 1, "basically": 1, "you know": 1, "kind of": 1}
    assert all("start" in i for i in fillers["evidence"]["items"])


def test_second_attempt_is_compared_with_first(setup):
    client, _ = setup
    first = post_audio(client).json()
    second = post_audio(client).json()
    assert second["attempt_number"] == 2 and second["compared_with"] == first["id"]
    rows = {r["label"]: r for r in second["compare"]["rows"]}
    assert rows["Filler count"]["verdict"] == "better" and rows["Filler count"]["after"] == 0
    assert rows["STAR parts present"]["after"] > rows["STAR parts present"]["before"]
    assert rows["Job requirements mentioned"]["verdict"] == "better"
    assert any("Added STAR parts" in n for n in second["compare"]["notes"])
    listed = client.get("/api/attempts", params={"question": "tell me about drishti ai. "}).json()["attempts"]
    assert [a["id"] for a in listed] == [first["id"], second["id"]]


def test_audio_is_stored_and_served_and_deletable(setup):
    client, _ = setup
    a = post_audio(client, data=b"abc123").json()
    assert client.get(f"/api/attempts/{a['id']}/audio").content == b"abc123"
    assert client.delete(f"/api/attempts/{a['id']}").status_code == 200
    assert client.get(f"/api/attempts/{a['id']}/audio").status_code == 404


def test_upload_validation(setup, monkeypatch):
    client, t = setup
    assert post_audio(client, name="a.exe").status_code == 415
    assert post_audio(client, data=b"").status_code == 400
    assert post_audio(client, question="  ").status_code == 400
    monkeypatch.setattr(config, "MAX_AUDIO_MB", 0)
    assert post_audio(client, data=b"x").status_code == 413
    monkeypatch.setattr(config, "MAX_AUDIO_MB", 25)
    t.error = AudioError("The recording is 2.0s.")
    r = post_audio(client)
    assert r.status_code == 422 and "2.0s" in r.json()["detail"]


def test_questions_route_falls_back_and_labels_it(setup):
    client, _ = setup
    r = client.post("/api/questions", files={"resume": ("cv.txt", RESUME, "text/plain")}, data={"job_description": "Python and Docker"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "template" and body["note"]
    assert any("Drishti AI" in q["question"] and q["source_text"].startswith("Drishti AI") for q in body["questions"])
    assert body["resume"]["projects"] == ["Drishti AI"]


def test_questions_route_rejects_bad_resume(setup):
    client, _ = setup
    assert client.post("/api/questions", files={"resume": ("cv.exe", b"x", "x")}).status_code == 400
    assert client.post("/api/questions", files={"resume": ("cv.txt", b"", "x")}).status_code == 400


def test_suggest_route_reports_llm_down(setup):
    client, _ = setup
    a = post_audio(client).json()
    r = client.post(f"/api/attempts/{a['id']}/suggest")
    assert r.status_code == 503 and "Ollama" in r.json()["detail"]
    assert client.post("/api/attempts/999/suggest").status_code == 404


def test_suggest_route_labels_the_text(tmp_path):
    t = FakeTranscriber()
    client = TestClient(create_app(transcriber=t, ask_json=llm_down, ask_text=lambda s, u: "A rewrite. [add: the result]", data_dir=tmp_path))
    a = post_audio(client).json()
    body = client.post(f"/api/attempts/{a['id']}/suggest").json()
    assert body["suggestion"].startswith("A rewrite") and "not your words" in body["label"]
    assert "Result" in body["weakest"]


def test_pace_and_length_thresholds():
    words = words_from_text(" ".join(["word"] * 100))
    for i, w in enumerate(words):
        w.start, w.end = i * 0.6, i * 0.6 + 0.5   # 100 words in 60s = 100 wpm
    r = scoring.analyse(words, 61)
    pace = scoring.check(r, "pace")
    assert pace["value"] == 100 and pace["status"] == "close"
    assert scoring.check(r, "length")["status"] == "met"
    assert scoring.check(scoring.analyse(words, 20), "length")["status"] == "miss"


def test_fillers_inside_a_sentence_do_not_hide_star_cues():
    words = words_from_text("So basically I, um, wrote the code in Python. As a result it ran faster.")
    r = scoring.analyse(words, 30)
    star = scoring.check(r, "star")
    assert star["evidence"]["parts"]["Action"]["present"] and star["evidence"]["parts"]["Result"]["present"]
