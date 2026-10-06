# VoxIQ upgrade notes

## How to review

VoxIQ has no git repo (and I did not create one). The original is untouched at `C:/Users/LENOVO/projects/_backups/VoxIQ-before-upgrade-2026-10-06`.

- See what changed: compare the two folders, for example `diff -rq "<backup>" "<this folder>" --exclude=.venv --exclude=__pycache__`.
- Old code is kept inside this folder under `_old/` (old modules, old frontend, the generated dataset).
- Throw everything away: delete this folder's contents and copy the backup back. (Do this only if you are sure; `.venv/`, `data/` and `eval/data/` are mine and are not in the backup.)

No git commits were made, as agreed.

## What was broken (audit of the old version)

1. The final "interview score" came from a random forest trained on a dataset my script generated (`generate_dataset.py`, random numbers plus a formula). It has no connection to real interview quality. A number that looked like a grade, with nothing behind it.
2. Typed answers were given "perfect" acoustic values (140 wpm, 0 fillers, 0.95 confidence) so they scored well on pace and delivery without any speech.
3. Words per minute divided the word count by the whole file length, including silence at the start and end.
4. Fillers: a regex that counted every "so" and "like" (including "I like Python"), missed Indian English fillers and gave no timestamps.
5. STAR: a DistilBERT zero-shot classifier. On my test sentences it called almost everything "action", including "Um, so yeah that is about it".
6. Job description match: one TF-IDF cosine number, with no way to see which requirements were covered.
7. The follow-up came from SmolLM-135M, too small to write a sensible question.
8. `CORS allow_origins=["*"]` together with credentials, no upload type, size or length checks, uploads written to temp files named by the client suffix, and the Whisper model loaded at import (a failure crashed the app before it could show an error).
9. `requirements.txt` listed `groq` (unused) and spaCy (the model was never installed, the code silently fell back).
10. The UI loaded Tailwind, FontAwesome, Chart.js and html2pdf from CDNs, and drew a "vocal confidence" chart from values that were not measured.
11. No tests.

## What I changed

- Removed the single score and the random forest (moved to `_old/`). Replaced with five checks, each with a status, a reason, the threshold and the evidence: pace, fillers, STAR, job description coverage, length. There is no overall grade.
- New filler detector (`voxiq/fillers.py`) with context rules for actually, like, you know, literally, kind of, sort of, na, right, plus always-counted words (um, uh, basically, so basically, matlab and others). The list is a JSON file you can edit (`VOXIQ_FILLERS_FILE`). 32 test cases, including non-filler uses.
- STAR now uses cue phrases (shown next to each sentence) instead of the zero-shot model. Fillers are removed from a sentence before matching, so "I, um, wrote" still counts as an Action.
- Job description coverage: skills from the JD (vocabulary plus repeated keywords) against the sentences you said, with the sentence as evidence.
- Résumé upload (PDF, DOCX, TXT), parsed into numbered lines. Questions are generated per project by a local Ollama model, so a question can only use that project's own lines, and every question shows its source line. Unusable model output becomes a template question labelled "template". Without Ollama the whole list is templates, with a visible note.
- Practice loop: record in the browser (or upload a file), feedback, "Try again". Attempts are stored in SQLite with the audio as WAV (so click-to-hear works on a seekable file). The comparison of attempt A and B is the top of the review page, with before/after/change per metric and a list of what changed.
- Suggested rewrite of the weakest part, plus one follow-up question, both from the local model and labelled as a suggestion.
- Whisper: faster-whisper `small.en` on the GPU (float16), falling back to CPU. Word timestamps. A prompt containing "um/uh" to stop Whisper deleting fillers.
- Input checks: audio type, size (25 MB), duration (5 to 300 s), speech present, résumé type and size, question length. Clear errors when the mic is denied or missing, when Ollama is down or the model is not pulled, and when the server cannot be reached.
- Server no longer allows any origin; frontend has no CDN dependency; all text is inserted with `textContent` (no HTML injection from résumés or transcripts).
- UI rebuilt as a calm practice tool (screenshots in `docs/screenshots/`). Checked at 390 px and 1280 px: no horizontal scroll, no page errors.
- Tests: 61 pass (`pytest tests`): fillers, STAR mapping, JD coverage, résumé parsing (including a real DOCX), question generation with a fake LLM and with the LLM down, routes with a fake transcriber (analyze, validation errors, attempt storage, comparison, audio, delete, suggest).

## Results

- Tests: 61 passed.
- Whisper WER, LibriSpeech test-clean, first 40 utterances, faster-whisper on the GPU: tiny.en 4.53%, base.en 4.27%, small.en 4.01%. Small clean read-speech sample. Indian English was not measured: I did not find a public Indian-English set I could download without a login within the time, so none is claimed.
- End-to-end run through the real UI (Edge, fake microphone playing a text-to-speech answer, then a second upload): transcription, 11 fillers found in attempt 1 and 0 in attempt 2, STAR parts, comparison page and rewrite all worked. These recordings are synthetic speech, so this shows the pipeline works, not how good it is on a real person.
- Analysis time is a few seconds on the GPU once the models are loaded. Question writing took about 2 seconds per project with `qwen2.5:1.5b`.

## Still not done, or did not work

- The 1.5B model writes mediocre questions. They are grounded in the right project line but often generic, and sometimes the model's output fails my checks and a template is used instead (visible in the screenshot, where two of the three project questions are templates). A bigger model (set `VOXIQ_LLM_MODEL`, for example `llama3.2:3b`) would do better; I stayed under the download budget.
- The rewrite is the same small model. In my test it added an invented detail ("determined the threshold") and mentioned the job description, so I tightened the prompt, but I did not re-verify it at length. Treat it as a draft.
- STAR cues and the filler rules are not validated on a labelled set of real answers. Pace and length targets are my choices.
- Whisper keeps most fillers with the prompt but not all. Real filler counts are probably higher than shown.
- No pitch, tone or "confidence" analysis any more. The old values were not tied to any real judgement, so I removed them rather than keep a meaningless chart.
- Scanned résumés (no OCR). Résumés with unusual headings may not list projects.
- Only one user and one machine: no login, attempts are in `data/`.
- The comparison treats a faster pace as "worse" whenever it moves further from 120 to 160; in my demo the second attempt was a synthetic voice that spoke fast and short, so "2 better, 2 worse" is what the numbers say.

## Decisions I made

- Rules for STAR instead of a model: the zero-shot model was worse and could not explain itself. Rules show their cue.
- `small.en` as default: lowest WER of the three on my sample and cheap on the GPU. `base.en` is a fine choice on weak hardware.
- `qwen2.5:1.5b` through Ollama (about 1 GB), configurable by `VOXIQ_LLM_MODEL`. I also have `qwen2.5:0.5b` from before; I did not delete it.
- One model call per project so questions cannot mix up details between projects, and the source line is set by the code, not by the model.
- Stored audio is converted to 16 kHz mono WAV, because browser WebM is not seekable and click-to-hear would fail.
- Dropped the librosa pitch features and spaCy. They fed only the old score. Fewer dependencies.
- No overall number anywhere, even a "readiness" one. Each check says what it measured and why.
- Thresholds (120 to 160 wpm, 3 fillers per minute, 60 to 120 s, 60% of JD requirements) are mine, from general coaching advice, and the UI says so.
- Torch stays in requirements only because ctranslate2 finds its CUDA DLLs through it on Windows. CPU-only users can drop it.
- Licences: all dependencies are MIT, BSD or Apache. Nothing AGPL or GPL.
- Used Python's global packages through `--system-site-packages` in the venv to avoid re-downloading PyTorch. A broken TensorFlow install on this machine breaks `transformers`, which is one more reason the app no longer imports it.

## Check yourself

- Record with your real microphone in the browser and look at whether the fillers it highlights match what you said. This is the most important check: I only tested synthetic speech and a fake microphone.
- Try your own résumé (PDF and DOCX) and see whether the project names it lists are right.
- Read the generated questions and rewrites for anything false.
- Say an answer with "actually" and "like" used normally and make sure they are not counted.
- Open `docs/screenshots/` and see if the look is what you want.
