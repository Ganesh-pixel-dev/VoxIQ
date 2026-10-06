// DOM Elements
const recordBtn = document.getElementById('record-btn');
const stopBtn = document.getElementById('stop-btn');
const visualizer = document.getElementById('audio-canvas');
const statusText = document.getElementById('status-text');
const chatContainer = document.getElementById('chat-container');
const exportPdfBtn = document.getElementById('export-pdf-btn');

// New Text Input Elements
const textInput = document.getElementById('text-input');
const sendBtn = document.getElementById('send-btn');

// Chart instance
let confidenceChart;

// Audio Variables
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let currentQuestion = "Tell me about a time you faced a difficult technical challenge and how you overcame it.";

// Web Audio API Variables
let audioContext;
let analyser;
let microphone;
let animationId;

// Timer
let sessionSeconds = 0;
setInterval(() => {
    sessionSeconds++;
    const hrs = Math.floor(sessionSeconds / 3600).toString().padStart(2, '0');
    const mins = Math.floor((sessionSeconds % 3600) / 60).toString().padStart(2, '0');
    const secs = (sessionSeconds % 60).toString().padStart(2, '0');
    document.getElementById('session-timer').innerText = `${hrs}:${mins}:${secs}`;
}, 1000);

// API Endpoint
const API_URL = "/api/analyze";

// Initialize Chart
function initChart() {
    const ctx = document.getElementById('confidence-chart').getContext('2d');
    confidenceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['0s', '5s', '10s', '15s', '20s', '25s', '30s'],
            datasets: [{
                label: 'Vocal Confidence',
                data: [0, 0, 0, 0, 0, 0, 0],
                borderColor: '#2563eb', // brand-blue
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1.0,
                    grid: { color: '#334155' },
                    ticks: { color: '#94a3b8', font: { family: 'Roboto Mono' } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Roboto Mono' } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}
initChart();

// Event Listeners
recordBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);
exportPdfBtn.addEventListener('click', exportToPDF);
sendBtn.addEventListener('click', submitText);
textInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') submitText();
});

async function submitText() {
    const text = textInput.value.trim();
    if (!text) return;
    
    // Clear input
    textInput.value = '';
    
    // Start Progress Simulation (Faster for text since no whisper)
    processingPercentage = 0;
    statusText.classList.remove('text-brand-red', 'animate-strict-pulse', 'text-brand-blue');
    statusText.classList.add('text-brand-amber');
    
    processingInterval = setInterval(() => {
        const remaining = 99 - processingPercentage;
        processingPercentage += Math.max(0.1, remaining * 0.1); // 2x faster
        
        let stage = "ANALYZING SEMANTICS (BART)...";
        if (processingPercentage > 80) stage = "GENERATING CHATBOT RESPONSE (LLAMA)...";
        if (processingPercentage > 95) stage = "COMPILING TELEMETRY...";
        
        statusText.innerText = `[${processingPercentage.toFixed(1)}%] ${stage}`;
    }, 500);

    const formData = new FormData();
    formData.append("text_input", text);
    const jobDesc = document.getElementById('job-desc').value;
    formData.append("job_description", jobDesc);
    formData.append("previous_question", currentQuestion);

    try {
        const response = await fetch(API_URL, { method: "POST", body: formData });
        clearInterval(processingInterval);
        
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();
        updateDashboard(data);
    } catch (err) {
        console.error(err);
        clearInterval(processingInterval);
        statusText.innerText = "CONNECTION ERROR";
        statusText.classList.remove('text-brand-amber');
        statusText.classList.add('text-brand-red');
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstop = processAudio;
        
        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
        
        setupVisualizer(stream);
        
        recordBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
        statusText.innerText = "RECORDING IN PROGRESS";
        statusText.classList.add('animate-strict-pulse', 'text-brand-red');
        
    } catch (err) {
        console.error(err);
        alert("Microphone access is required.");
    }
}

function setupVisualizer(stream) {
    if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 128;
    
    microphone = audioContext.createMediaStreamSource(stream);
    microphone.connect(analyser);
    
    const canvasCtx = visualizer.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    function draw() {
        if (!isRecording) return;
        animationId = requestAnimationFrame(draw);
        
        analyser.getByteFrequencyData(dataArray);
        
        visualizer.width = visualizer.offsetWidth;
        visualizer.height = visualizer.offsetHeight;
        
        const width = visualizer.width;
        const height = visualizer.height;
        
        canvasCtx.clearRect(0, 0, width, height);
        
        const barWidth = (width / bufferLength);
        let x = 0;
        
        canvasCtx.fillStyle = '#2563eb'; // strict blue bar
        
        for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * height;
            const y = height - barHeight;
            canvasCtx.fillRect(x, y, barWidth - 1, barHeight);
            x += barWidth;
        }
    }
    draw();
}

let processingInterval;
let processingPercentage = 0;

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        if (animationId) cancelAnimationFrame(animationId);
        
        const canvasCtx = visualizer.getContext('2d');
        canvasCtx.clearRect(0, 0, visualizer.width, visualizer.height);
        
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        
        stopBtn.classList.add('hidden');
        recordBtn.classList.remove('hidden');
        
        // Start Progress Simulation
        processingPercentage = 0;
        statusText.classList.remove('text-brand-red', 'animate-strict-pulse');
        statusText.classList.add('text-brand-amber');
        
        processingInterval = setInterval(() => {
            // Asymptotic progress approach 99% but never hit 100% until done
            const remaining = 99 - processingPercentage;
            processingPercentage += Math.max(0.1, remaining * 0.05);
            
            let stage = "EXTRACTING AUDIO...";
            if (processingPercentage > 20) stage = "RUNNING WHISPER LARGE-V3...";
            if (processingPercentage > 70) stage = "ANALYZING SEMANTICS (BART)...";
            if (processingPercentage > 90) stage = "COMPILING TELEMETRY...";
            
            statusText.innerText = `[${processingPercentage.toFixed(1)}%] ${stage}`;
        }, 1000);
    }
}

async function processAudio() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    
    formData.append("audio", audioBlob, "recording.webm");
    const jobDesc = document.getElementById('job-desc').value;
    formData.append("job_description", jobDesc);
    formData.append("previous_question", currentQuestion);

    try {
        const response = await fetch(API_URL, { method: "POST", body: formData });
        
        // Clear progress interval on finish
        clearInterval(processingInterval);
        
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();
        updateDashboard(data);
    } catch (err) {
        console.error(err);
        clearInterval(processingInterval);
        statusText.innerText = "CONNECTION ERROR";
        statusText.classList.remove('text-brand-amber');
        statusText.classList.add('text-brand-red');
    }
}

function updateDashboard(data) {
    statusText.innerText = "AWAITING INPUT";
    statusText.classList.remove('text-brand-blue');
    exportPdfBtn.classList.remove('hidden');
    
    // Update Log
    addLogEntry('USER', data.module1_dl_score.transcript || "[Unintelligible]", true);
    
    setTimeout(() => {
        const nextQ = data.module3_chatbot_response || "Could you tell me more?";
        currentQuestion = nextQ;
        addLogEntry('AI', nextQ, false);
    }, 1000);

    // Final Score
    const score = data.module4_ml_final_score;
    animateValue("final-score", 0, score, 1500);
    document.getElementById('score-bar').style.width = `${score}%`;
    
    // Set score bar color semantically
    const scoreBar = document.getElementById('score-bar');
    if (score >= 80) scoreBar.className = "h-full transition-all duration-1000 bg-brand-green";
    else if (score >= 60) scoreBar.className = "h-full transition-all duration-1000 bg-brand-amber";
    else scoreBar.className = "h-full transition-all duration-1000 bg-brand-red";

    // Update NLP Bars
    const nlp = data.module2_nlp_score;
    updateBar('bar-s', 'score-s-text', nlp.star_s_score);
    updateBar('bar-t', 'score-t-text', nlp.star_t_score);
    updateBar('bar-a', 'score-a-text', nlp.star_a_score);
    updateBar('bar-r', 'score-r-text', nlp.star_r_score);
    
    // Update NLP Flags
    const flagsDiv = document.getElementById('nlp-feedback');
    const flagsText = document.getElementById('nlp-flags');
    if (nlp.missing_flags && nlp.missing_flags.length > 0 && nlp.missing_flags[0] !== "STAR structure is solid.") {
        flagsText.innerText = nlp.missing_flags.join(" ");
        flagsDiv.classList.remove('hidden');
    } else {
        flagsDiv.classList.add('hidden');
    }

    // Update Acoustic Metrics
    const dl = data.module1_dl_score;
    document.getElementById('metric-wpm').innerText = dl.wpm_score ? dl.wpm_score.toFixed(1) : "0";
    document.getElementById('metric-fillers').innerText = dl.filler_frequency || "0";
    
    const conf = dl.acoustic_confidence || 0;
    document.getElementById('metric-conf').innerText = conf.toFixed(2) + " AVG";
    
    if (document.getElementById('metric-jitter')) {
        document.getElementById('metric-jitter').innerText = dl.jitter !== undefined ? dl.jitter.toFixed(1) + '%' : "--";
        document.getElementById('metric-shimmer').innerText = dl.shimmer !== undefined ? dl.shimmer.toFixed(1) + '%' : "--";
    }

    // Simulate Chart Data based on average confidence
    const simulatedData = [
        Math.max(0, conf - 0.2), 
        Math.min(1, conf + 0.1), 
        conf, 
        Math.max(0, conf - 0.15), 
        conf, 
        Math.min(1, conf + 0.05), 
        conf
    ];
    confidenceChart.data.datasets[0].data = simulatedData;
    confidenceChart.update();
}

function updateBar(barId, textId, score) {
    const bar = document.getElementById(barId);
    const txt = document.getElementById(textId);
    const percent = Math.round(score * 100);
    
    setTimeout(() => {
        bar.style.width = percent + "%";
        txt.innerText = score.toFixed(2);
        
        // Semantic coloring
        if (score >= 0.8) bar.style.backgroundColor = '#10b981'; // green
        else if (score >= 0.4) bar.style.backgroundColor = '#f59e0b'; // amber
        else bar.style.backgroundColor = '#ef4444'; // red
        
    }, 300);
}

function addLogEntry(sender, text, isUser) {
    const wrapper = document.createElement('div');
    wrapper.className = `log-entry flex gap-2 mt-2`;
    
    const timestamp = document.createElement('span');
    timestamp.className = `timestamp w-14 shrink-0 ${isUser ? 'text-brand-green' : 'text-brand-blue'}`;
    timestamp.innerText = `[${sender}]`;
    
    const content = document.createElement('span');
    content.className = `content text-brand-text`;
    content.innerText = text;
    
    wrapper.appendChild(timestamp);
    wrapper.appendChild(content);
    chatContainer.appendChild(wrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function animateValue(id, start, end, duration) {
    if (start === end) {
        document.getElementById(id).innerHTML = end.toFixed(1);
        return;
    }
    const obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = (progress * (end - start) + start).toFixed(1);
        if (progress < 1) window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
}

function exportToPDF() {
    exportPdfBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> GENERATING';
    
    const element = document.getElementById('report-container');
    const opt = {
        margin:       0.5,
        filename:     'VoxIQ-Telemetry-Report.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'landscape' } // Landscape fits grids better
    };
    
    const originalBg = element.style.background;
    element.style.background = '#0f172a'; // Ensure slate bg is preserved
    element.style.padding = '20px';
    
    html2pdf().set(opt).from(element).save().then(() => {
        element.style.background = originalBg;
        element.style.padding = '0px';
        exportPdfBtn.innerHTML = '<i class="fa-solid fa-download"></i> EXPORT REPORT';
    });
}
