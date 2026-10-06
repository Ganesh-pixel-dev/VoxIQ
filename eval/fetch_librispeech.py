"""Download 40 LibriSpeech test-clean utterances (streamed, a few MB) to eval/data."""
import json, pathlib, soundfile as sf
from datasets import load_dataset

out = pathlib.Path(__file__).parent / "data"
out.mkdir(exist_ok=True)
ds = load_dataset("openslr/librispeech_asr", "clean", split="test", streaming=True)
ref = {}
for i, ex in enumerate(ds):
    if i >= 40:
        break
    name = f"{ex['id']}.wav"
    sf.write(out / name, ex["audio"]["array"], ex["audio"]["sampling_rate"])
    ref[name] = ex["text"].lower()
(out / "references.json").write_text(json.dumps(ref, indent=1))
print(len(ref), "utterances")
