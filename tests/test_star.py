from voxiq.star import label_sentence, summarise

GOOD = [
    "Last year I was in my final year project team at college.",
    "My job was to build the image forensics module.",
    "I wrote the error level analysis code and tested it on forty images.",
    "As a result the load time dropped from eight seconds to two.",
]


def test_each_part_is_labelled_with_its_cue():
    assert label_sentence(GOOD[0])[0] == "Situation"
    assert label_sentence(GOOD[1]) == ("Task", "My job")
    assert label_sentence(GOOD[2])[0] == "Action"
    assert label_sentence(GOOD[3]) == ("Result", "As a result")


def test_complete_answer_has_no_missing_parts():
    s = summarise(GOOD)
    assert s["missing"] == [] and s["present_count"] == 4
    assert s["parts"]["Task"]["sentences"][0]["text"] == GOOD[1]


def test_missing_parts_are_reported():
    s = summarise([GOOD[2], "I used Python and Django to build the backend."])
    assert s["missing"] == ["Situation", "Task", "Result"]
    assert not s["parts"]["Result"]["present"] and s["parts"]["Result"]["sentences"] == []


def test_filler_sentence_gets_no_label():
    assert label_sentence("Um, so yeah that is about it.") == (None, "")


def test_numbers_count_as_result_evidence():
    assert label_sentence("Accuracy went from 70% to 85% on my own test set.")[0] == "Result"


def test_empty_input():
    s = summarise([])
    assert s["missing"] == ["Situation", "Task", "Action", "Result"]
