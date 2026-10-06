const $ = (id) => document.getElementById(id);

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const state = { jd: "", question: null, attempts: [], status: null, recorder: null, stream: null, timer: null };
const STATUS_LABEL = { met: "Within range", close: "Close", miss: "Outside range", skipped: "Not checked" };

async function api(path, opts) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch {
    throw new Error("Cannot reach the VoxIQ server. Is it still running?");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try { const j = await res.json(); if (typeof j.detail === "string") detail = j.detail; } catch { /* keep default */ }
    throw new Error(detail);
  }
  return res.json();
}

function say(el, text, kind) {
  el.textContent = text || "";
  el.hidden = !text;
  if (kind) el.className = "notice " + kind;
}

/* status chips */
async function loadStatus() {
  try {
    const s = await api("/api/status");
    state.status = s;
    const chips = [
      h("span", { class: "chip" }, `speech: ${s.whisper.model}`),
      h("span", { class: "chip" + (s.llm.up && s.llm.model_ready ? "" : " bad") },
        s.llm.up ? (s.llm.model_ready ? `questions: ${s.llm.model}` : `model ${s.llm.model} not pulled`) : "Ollama is off: template questions"),
    ];
    $("status").replaceChildren(...chips);
    $("limits").textContent = `Recordings must be ${s.limits.min_seconds} to ${s.limits.max_seconds} seconds.`;
  } catch (e) {
    $("status").replaceChildren(h("span", { class: "chip bad" }, "server not reachable"));
  }
}

/* step 1 and 2: questions */
$("setup-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const file = $("resume").files[0];
  const msg = $("setup-msg");
  if (!file) { msg.textContent = "Choose your résumé first, or use the standard questions."; return; }
  state.jd = $("jd").value;
  const fd = new FormData();
  fd.append("resume", file);
  fd.append("job_description", state.jd);
  $("make-q").disabled = true;
  msg.textContent = "Reading your résumé and writing questions. This takes a few seconds per project.";
  try {
    renderQuestions(await api("/api/questions", { method: "POST", body: fd }));
    msg.textContent = "";
  } catch (e) {
    msg.textContent = e.message;
  } finally {
    $("make-q").disabled = false;
  }
});

$("hr-only").addEventListener("click", async () => {
  state.jd = $("jd").value;
  try {
    const r = await api("/api/hr-questions");
    renderQuestions({ source: "standard", note: "", questions: [], hr: r.questions });
  } catch (e) { $("setup-msg").textContent = e.message; }
});

$("custom-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const t = $("custom-q").value.trim();
  if (t) choose({ question: t, source_text: "", kind: "custom", origin: "yours" });
});

function questionRow(q) {
  const origin = q.origin === "llm" ? `written by ${state.status?.llm.model || "the local model"}`
    : q.origin === "template" ? "template, not the model" : "standard question";
  return h("div", { class: "q" },
    h("div", {},
      h("p", { class: "q-text" }, q.question),
      h("p", { class: "q-src" },
        h("span", { class: "tagline" }, origin),
        q.source_text ? ["From résumé line ", q.source_line, ": ", h("q", {}, q.source_text)] : (q.kind === "jd" ? "From a requirement in the job description" : ""))),
    h("button", { class: "btn small", type: "button", onclick: () => choose(q) }, "Practise"));
}

function renderQuestions(data) {
  const box = $("q-list");
  box.replaceChildren();
  const groups = [
    ["From your résumé", data.questions.filter((q) => q.kind === "resume")],
    ["From the job description", data.questions.filter((q) => q.kind === "jd")],
    ["Standard HR questions", data.hr],
  ];
  for (const [title, qs] of groups) {
    if (qs.length) box.append(h("div", { class: "q-group" }, h("h3", {}, title), qs.map(questionRow)));
  }
  const note = $("q-note");
  if (data.source === "template") {
    say(note, `Language model unavailable (${data.note}) so the résumé questions below come from templates built from your project names and skills.`, "warn");
  } else if (data.source === "llm") {
    say(note, `Résumé questions were written by ${data.model}, a small local model. They can be off, so skip any that miss the point.`, "");
  } else say(note, "");
  $("questions").hidden = false;
  $("questions").scrollIntoView({ behavior: "smooth", block: "start" });
}

/* step 3: practise */
async function choose(q) {
  state.question = q;
  $("p-question").textContent = q.question;
  $("p-source").textContent = q.source_text ? `From résumé line ${q.source_line}: ${q.source_text}` : "";
  $("practice").hidden = false;
  say($("p-msg"), "");
  $("busy").hidden = true;
  await refreshAttempts();
  $("practice").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function refreshAttempts() {
  const r = await api("/api/attempts?question=" + encodeURIComponent(state.question.question));
  state.attempts = r.attempts;
  renderReview();
}

function stopTracks() {
  state.stream?.getTracks().forEach((t) => t.stop());
  clearInterval(state.timer);
  $("level").style.width = "0";
}

async function startRecording() {
  say($("p-msg"), "");
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    say($("p-msg"), "This browser cannot record from a microphone here (it needs https or localhost). Upload a recording instead.", "error");
    return;
  }
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    const why = e.name === "NotAllowedError" ? "Microphone permission was denied. Allow it in the address bar, or upload a recording instead."
      : e.name === "NotFoundError" ? "No microphone was found. Plug one in, or upload a recording instead."
      : `The microphone could not be opened (${e.name}). Upload a recording instead.`;
    say($("p-msg"), why, "error");
    return;
  }
  const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((m) => MediaRecorder.isTypeSupported(m)) || "";
  const chunks = [];
  const rec = new MediaRecorder(state.stream, mime ? { mimeType: mime } : {});
  state.recorder = rec;
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.onstop = () => {
    stopTracks();
    document.body.classList.remove("recording");
    $("rec").textContent = "Start recording";
    const type = rec.mimeType || "audio/webm";
    send(new Blob(chunks, { type }), "answer." + (type.includes("mp4") ? "m4a" : "webm"));
  };
  // level meter
  try {
    const ctx = new AudioContext();
    const an = ctx.createAnalyser();
    ctx.createMediaStreamSource(state.stream).connect(an);
    const buf = new Uint8Array(an.fftSize);
    const tick = () => {
      if (rec.state !== "recording") { ctx.close(); return; }
      an.getByteTimeDomainData(buf);
      let peak = 0;
      for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
      $("level").style.width = Math.min(100, peak / 64 * 100) + "%";
      requestAnimationFrame(tick);
    };
    tick();
  } catch { /* the meter is optional */ }
  rec.start();
  const t0 = Date.now();
  const max = state.status?.limits.max_seconds || 300;
  document.body.classList.add("recording");
  $("rec").textContent = "Stop and get feedback";
  state.timer = setInterval(() => {
    const s = Math.floor((Date.now() - t0) / 1000);
    $("timer").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    if (s >= max) rec.stop();
  }, 250);
}

$("rec").addEventListener("click", () => {
  if (state.recorder?.state === "recording") state.recorder.stop();
  else startRecording();
});

$("file").addEventListener("change", (ev) => {
  const f = ev.target.files[0];
  ev.target.value = "";
  if (f) send(f, f.name);
});

async function send(blob, name) {
  if (!state.question) return;
  const fd = new FormData();
  fd.append("audio", blob, name);
  fd.append("question", state.question.question);
  fd.append("job_description", state.jd);
  $("busy").hidden = false;
  $("rec").disabled = true;
  say($("p-msg"), "");
  try {
    const a = await api("/api/analyze", { method: "POST", body: fd });
    await refreshAttempts();
    $("review").scrollIntoView({ behavior: "smooth", block: "start" });
    return a;
  } catch (e) {
    say($("p-msg"), e.message, "error");
  } finally {
    $("busy").hidden = true;
    $("rec").disabled = false;
    $("timer").textContent = "0:00";
  }
}

/* review */
function playFrom(attemptId, start, end) {
  const p = $("player");
  const src = `/api/attempts/${attemptId}/audio`;
  if (!p.src.endsWith(src)) p.src = src;
  const go = () => {
    p.currentTime = Math.max(0, start - 0.6);
    p.play().catch(() => {});
    p.ontimeupdate = () => { if (p.currentTime > end + 0.7) { p.pause(); p.ontimeupdate = null; } };
  };
  p.readyState >= 1 ? go() : p.addEventListener("loadedmetadata", go, { once: true });
}

function transcriptView(attempt) {
  const words = attempt.result.words;
  const out = [];
  for (let i = 0; i < words.length; i++) {
    if (words[i].f) {
      let j = i;
      while (j + 1 < words.length && words[j + 1].f) j++;
      const text = words.slice(i, j + 1).map((w) => w.t).join(" ");
      out.push(h("button", {
        class: "fill", type: "button", title: "Play this part",
        "aria-label": `Filler: ${text}. Play from ${words[i].s} seconds`,
        onclick: () => playFrom(attempt.id, words[i].s, words[j].e),
      }, text), " ");
      i = j;
    } else out.push(h("span", { class: "w" }, words[i].t), " ");
  }
  return h("div", {},
    h("p", { class: "transcript" }, out),
    h("p", { class: "legend" }, "Highlighted words are counted as fillers. Click one to hear it. This transcript is Whisper's, so it can differ from what you said, and it sometimes leaves out an \"um\"."));
}

function fmt(v, unit) {
  return v == null ? "-" : v;
}

function checkEvidence(c) {
  const ev = c.evidence;
  if (c.key === "fillers") {
    if (!ev.items.length) return null;
    return h("ul", { class: "ev" }, ev.items.map((i) => h("li", {}, h("span", { class: "time" }, `${i.start}s `), h("strong", {}, i.label), ` in "${i.context}"`)));
  }
  if (c.key === "star") {
    return h("div", {}, Object.entries(ev.parts).map(([name, p]) =>
      h("div", { class: "parts-row" },
        h("span", { class: "pill " + (p.present ? "yes" : "no") }, `${name}: ${p.present ? "found" : "missing"}`),
        h("div", {}, p.sentences.length
          ? p.sentences.map((s) => h("div", {}, `"${s.text}" `, h("span", { class: "cue" }, `cue: ${s.cue}`)))
          : h("span", { class: "muted" }, p.explain)))));
  }
  if (c.key === "jd" && ev.has_jd) {
    return h("div", {},
      ev.mentioned.map((m) => h("div", {}, h("span", { class: "pill yes" }, m.skill), ` "${m.sentence}"`)),
      h("div", {}, ev.missing.map((m) => h("span", { class: "pill no" }, m.skill + " (not mentioned)"))));
  }
  return null;
}

function checklist(attempt) {
  return h("ul", { class: "checks" }, attempt.result.checks.map((c) => {
    const ev = checkEvidence(c);
    return h("li", { class: "check" },
      h("div", { class: "check-head" },
        h("span", { class: "mark " + c.status, "aria-hidden": "true" }),
        h("div", {}, h("h3", {}, c.title), h("span", { class: "status" }, STATUS_LABEL[c.status])),
        h("span", { class: "value" }, c.value == null ? "" : `${c.value} ${c.unit}`)),
      h("p", { class: "reason" }, c.reason),
      h("details", {}, h("summary", {}, "How this is judged"), h("p", {}, c.threshold), ev));
  }));
}

function deltaText(r) {
  if (r.verdict === "same") return "no change";
  return r.verdict === "better" ? "better" : "worse";
}

function compareHero(a, b, cmp) {
  const idx = (x) => state.attempts.findIndex((t) => t.id === x.id) + 1;
  const verdict = cmp.better === 0 && cmp.worse === 0 ? "Nothing measurable changed."
    : `${cmp.better} better, ${cmp.worse} worse${cmp.worse === 0 ? ". Every change went the right way." : "."}`;
  return h("section", { class: "compare-hero", "aria-labelledby": "cmp-h" },
    h("h2", { id: "cmp-h" }, `Attempt ${idx(a)} vs attempt ${idx(b)}`),
    h("p", { class: "verdict" }, verdict),
    state.attempts.length > 2 ? h("div", { class: "pick" }, "Compare",
      select("from", a), "with", select("to", b)) : null,
    h("table", { class: "cmp" },
      h("thead", {}, h("tr", {}, h("th", {}, "What"), h("th", {}, `Attempt ${idx(a)}`), h("th", { class: "arrow" }), h("th", {}, `Attempt ${idx(b)}`), h("th", {}, "Change"))),
      h("tbody", {}, cmp.rows.map((r) => h("tr", {},
        h("td", {}, r.label), h("td", { class: "num" }, fmt(r.before)), h("td", { class: "arrow", "aria-hidden": "true" }, "→"),
        h("td", { class: "num" }, fmt(r.after)), h("td", {}, h("span", { class: "delta " + r.verdict }, deltaText(r))))))),
    cmp.notes.length ? h("ul", { class: "notes" }, cmp.notes.map((n) => h("li", {}, n))) : null,
    h("div", { class: "two", style: "margin-top:16px" },
      h("div", {}, h("h3", {}, `Attempt ${idx(a)} transcript`), transcriptView(a)),
      h("div", {}, h("h3", {}, `Attempt ${idx(b)} transcript`), transcriptView(b))));
}

function select(which, current) {
  return h("select", { "aria-label": `Compare ${which} attempt`, onchange: (e) => { state.pick = state.pick || {}; state.pick[which] = Number(e.target.value); renderReview(); } },
    state.attempts.map((t, i) => h("option", { value: t.id, selected: t.id === current.id }, `Attempt ${i + 1}`)));
}

async function renderReview() {
  const root = $("r-body");
  const list = state.attempts;
  if (!list.length) { $("review").hidden = true; return; }
  $("review").hidden = false;
  const latest = list[list.length - 1];
  const pick = state.pick || {};
  let a = list.find((t) => t.id === pick.from) || list[list.length - 2];
  let b = list.find((t) => t.id === pick.to) || latest;
  if (a && b && a.id >= b.id) { a = list[list.length - 2]; b = latest; }
  const nodes = [];
  if (a) {
    try {
      const r = await api(`/api/compare?a=${a.id}&b=${b.id}`);
      nodes.push(compareHero(a, b, r.compare));
    } catch (e) { nodes.push(h("div", { class: "notice error" }, e.message)); }
  }
  nodes.push(h("div", { class: "card" },
    h("h2", {}, `Feedback on attempt ${list.indexOf(b) + 1}`),
    h("p", { class: "muted small" }, `${b.result.duration} seconds. A checklist, not a grade: each line says what it measured and why.`),
    checklist(b)));
  if (!a) nodes.push(h("div", { class: "card" }, h("h2", {}, "Your transcript"), transcriptView(b)));
  nodes.push(h("div", { class: "card", id: "suggest-box" },
    h("h2", {}, "Suggested rewrite"),
    h("p", { class: "muted" }, "A local model rewrites your weakest part using only what you said. It is a suggestion, not your words."),
    h("button", { class: "btn", type: "button", id: "suggest-btn", onclick: () => suggest(b) }, "Suggest a rewrite")));
  nodes.push(h("div", { class: "next-row" },
    h("button", { class: "btn primary big", type: "button", onclick: () => { $("practice").scrollIntoView({ behavior: "smooth" }); $("rec").focus(); } }, "Try again"),
    h("button", { class: "btn", type: "button", onclick: () => { $("questions").scrollIntoView({ behavior: "smooth" }); } }, "Pick another question"),
    h("button", { class: "btn", type: "button", onclick: () => removeAttempt(b) }, "Delete this attempt")));
  root.replaceChildren(...nodes);
}

async function suggest(attempt) {
  const box = $("suggest-box");
  const btn = $("suggest-btn");
  btn.disabled = true;
  btn.textContent = "Writing, a few seconds";
  try {
    const r = await api(`/api/attempts/${attempt.id}/suggest`, { method: "POST" });
    box.append(h("div", { class: "suggest" },
      h("p", { class: "muted small" }, `Weakest spot: ${r.weakest}`),
      h("blockquote", {}, r.suggestion),
      h("p", { class: "muted small" }, r.label),
      r.follow_up ? h("p", {}, h("strong", {}, "A follow-up an interviewer might ask: "), r.follow_up) : null));
    btn.remove();
  } catch (e) {
    box.append(h("div", { class: "notice error" }, e.message));
    btn.disabled = false;
    btn.textContent = "Try again";
  }
}

async function removeAttempt(attempt) {
  if (!confirm("Delete this attempt and its recording?")) return;
  await api(`/api/attempts/${attempt.id}`, { method: "DELETE" });
  state.pick = null;
  await refreshAttempts();
}

loadStatus();
