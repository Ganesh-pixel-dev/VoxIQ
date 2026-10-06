"""Word error rate of faster-whisper models on the LibriSpeech test-clean sample in eval/data."""
import json, pathlib, re, sys, time
import torch  # noqa: puts torch CUDA DLLs on the path for ctranslate2
import jiwer
from faster_whisper import WhisperModel

data = pathlib.Path(__file__).parent / "data"
refs = json.loads((data / "references.json").read_text())

def norm(s):
    return re.sub(r"[^a-z' ]", " ", s.lower()).split()

results = {}
for name in sys.argv[1:] or ["tiny.en", "base.en", "small.en"]:
    model = WhisperModel(name, device="cuda", compute_type="float16")
    hyps, rs, t0 = [], [], time.time()
    for f, ref in refs.items():
        segs, _ = model.transcribe(str(data / f), language="en", beam_size=5)
        hyps.append(" ".join(norm(" ".join(s.text for s in segs))))
        rs.append(" ".join(norm(ref)))
    results[name] = {"wer": round(jiwer.wer(rs, hyps), 4), "utterances": len(rs), "seconds": round(time.time() - t0, 1)}
    print(name, results[name], flush=True)
(pathlib.Path(__file__).parent / "wer_results.json").write_text(json.dumps(results, indent=1))
