'use strict';

// --- Utilities ---
function uuid() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

async function recordEvent(evt) {
  const sessionId = getSessionId();
  const payload = {
    event_type: evt.event_type,
    session_id: sessionId,
    artwork_id: evt.artwork_id ?? null,
    timestamp: new Date().toISOString(),
    ...(evt.duration_seconds != null ? { duration_seconds: evt.duration_seconds } : {})
  };

  // respect analytics consent
  if (!getAnalyticsConsent()) {
    return;
  }

  try {
    // Queue locally
    const q = JSON.parse(localStorage.getItem('scanart_events') || '[]');
    q.push(payload);
    localStorage.setItem('scanart_events', JSON.stringify(q));

    // Try sync immediately if online
    if (navigator.onLine) {
      await flushAnalyticsQueue();
    }
  } catch (e) {
    console.warn('recordEvent failed', e);
  }
}

async function flushAnalyticsQueue() {
  if (!getAnalyticsConsent()) return;
  const q = JSON.parse(localStorage.getItem('scanart_events') || '[]');
  if (!q.length) return;
  try {
    if (q.length === 1) {
      await fetch('/analytics', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(q[0]) });
      localStorage.setItem('scanart_events', JSON.stringify([]));
      return;
    }
    const res = await fetch('/sync-analytics', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ events: q }) });
    if (res.ok) {
      localStorage.setItem('scanart_events', JSON.stringify([]));
    }
  } catch (e) {
    // keep queue
  }
}

function getSessionId() {
  let sid = localStorage.getItem('scanart_session_id');
  if (!sid) {
    sid = `sess-${uuid()}`;
    localStorage.setItem('scanart_session_id', sid);
  }
  return sid;
}

function getAnalyticsConsent() {
  return localStorage.getItem('scanart_consent') === 'yes';
}

function setAnalyticsConsent(val) {
  localStorage.setItem('scanart_consent', val ? 'yes' : 'no');
}

// --- DOM refs ---
const videoEl = document.getElementById('video');
const canvasEl = document.getElementById('canvas');
const captureBtn = document.getElementById('captureBtn');
const testModeBtn = document.getElementById('testModeBtn');
const statusMsg = document.getElementById('statusMsg');

const resultSection = document.getElementById('resultSection');
const artTitle = document.getElementById('artTitle');
const artMeta = document.getElementById('artMeta');
const artShort = document.getElementById('artShort');
const paletteEl = document.getElementById('palette');
const textureVal = document.getElementById('textureVal');
const distanceVal = document.getElementById('distanceVal');
const confidenceBadge = document.getElementById('confidenceBadge');
const playAudioBtn = document.getElementById('playAudioBtn');
const addToTourBtn = document.getElementById('addToTourBtn');
const viewMoreLink = document.getElementById('viewMoreLink');
const lastPreview = document.getElementById('lastPreview');

const tourList = document.getElementById('tourList');
const tourNextBtn = document.getElementById('tourNextBtn');
const tourClearBtn = document.getElementById('tourClearBtn');

const consentModal = document.getElementById('consentModal');
const consentAccept = document.getElementById('consentAccept');
const consentDecline = document.getElementById('consentDecline');

const viewTimeContainer = document.getElementById('viewTimeContainer');
const viewTime = document.getElementById('viewTime');

// --- Page tracking ---
let currentArtworkViewStart = null;
let resultViewStart = null;
let viewTimerInterval = null;

function formatDuration(seconds) {
  if (seconds < 60) {
    return `${seconds}s`;
  } else {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
}

function updateViewTimer() {
  if (resultViewStart && viewTimeContainer && viewTime) {
    const elapsed = Math.round((Date.now() - resultViewStart) / 1000);
    viewTime.textContent = formatDuration(elapsed);
    viewTimeContainer.classList.remove('hidden');
  }
}

function startTrackingResultView(artworkId) {
  if (artworkId) {
    resultViewStart = Date.now();
    recordEvent({ event_type: 'view_result', artwork_id: artworkId });
    
    // Show timer and start updating it
    if (viewTimeContainer && viewTime) {
      viewTimeContainer.classList.remove('hidden');
      viewTime.textContent = '0s';
    }
    
    // Update immediately, then every second
    updateViewTimer();
    viewTimerInterval = setInterval(updateViewTimer, 1000);
  }
}

function endTrackingResultView() {
  // Clear the timer interval
  if (viewTimerInterval) {
    clearInterval(viewTimerInterval);
    viewTimerInterval = null;
  }
  
  if (resultViewStart) {
    const dur = Math.round((Date.now() - resultViewStart) / 1000);
    if (dur > 0) {
      // Show final duration briefly
      if (viewTime && viewTimeContainer) {
        viewTime.textContent = formatDuration(dur);
        // Keep showing for 2 more seconds, then fade out
        setTimeout(() => {
          if (viewTimeContainer) {
            viewTimeContainer.classList.add('hidden');
          }
        }, 2000);
      }
      
      recordEvent({ 
        event_type: 'result_view_duration', 
        artwork_id: sessionStorage.getItem('last_viewed_artwork_id'),
        duration_seconds: dur 
      });
    }
    resultViewStart = null;
  } else {
    // Hide timer if no tracking was active
    if (viewTimeContainer) {
      viewTimeContainer.classList.add('hidden');
    }
  }
}

// --- Consent and session init ---
function initConsent() {
  getSessionId();
  const c = localStorage.getItem('scanart_consent');
  if (!c) {
    consentModal.classList.remove('hidden');
  } else {
    consentModal.classList.add('hidden');
  }
}

consentAccept.addEventListener('click', async () => {
  setAnalyticsConsent(true);
  consentModal.classList.add('hidden');
  await recordEvent({ event_type: 'page_open' });
});

consentDecline.addEventListener('click', () => {
  setAnalyticsConsent(false);
  consentModal.classList.add('hidden');
});

window.addEventListener('beforeunload', async () => {
  const start = parseInt(sessionStorage.getItem('scanart_open_ts') || String(Date.now()), 10);
  const dur = Math.round((Date.now() - start) / 1000);
  endTrackingResultView(); // End any active result view tracking
  try { await recordEvent({ event_type: 'page_close', duration_seconds: dur }); } catch {}
});

// Track visibility changes to pause/resume time tracking
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    endTrackingResultView();
  }
});

window.addEventListener('online', () => { flushAnalyticsQueue(); });

// --- Camera ---
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
    videoEl.srcObject = stream;
    statusMsg.textContent = 'Camera ready.';
  } catch (e) {
    statusMsg.textContent = 'Camera permission denied or not available.';
  }
}

function snapshotToDataURL() {
  const vw = videoEl.videoWidth;
  const vh = videoEl.videoHeight;
  if (!vw || !vh) return null;
  canvasEl.width = vw; canvasEl.height = vh;
  const ctx = canvasEl.getContext('2d');
  ctx.drawImage(videoEl, 0, 0, vw, vh);
  return canvasEl.toDataURL('image/jpeg', 0.9);
}

// --- Analyze ---
async function analyzeDataURL(dataUrl) {
  statusMsg.textContent = 'Analyzing…';
  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: dataUrl })
    });
    if (!res.ok) throw new Error('Server error');
    const data = await res.json();
    populateResult(data, dataUrl);
    const artId = data.matched ? data.match_id : null;
    await recordEvent({ event_type: 'scan', artwork_id: artId });
  } catch (e) {
    statusMsg.textContent = 'Network/server error.';
  }
}

function populateResult(data, previewDataUrl) {
  // End previous result view tracking if any
  endTrackingResultView();
  
  resultSection.classList.remove('hidden');
  // Always show the last captured preview for context
  if (previewDataUrl) {
    lastPreview.src = previewDataUrl;
    lastPreview.classList.remove('hidden');
  }
  if (data.metadata) {
    const m = data.metadata;
    artTitle.textContent = m.title;
    artMeta.textContent = `${m.artist} • ${m.year}`;
    artShort.textContent = m.description_short || '';
    confidenceBadge.textContent = data.match_confidence != null ? `${Math.round(data.match_confidence * 100)}%` : '—';
    viewMoreLink.href = `/artwork-page/${m.id}`;
    viewMoreLink.onclick = (e) => {
      e.preventDefault();
      window.open(`/artwork-page/${m.id}`, '_blank');
    };
    addToTourBtn.onclick = () => addToTour(m.id);
    playAudioBtn.onclick = () => playAudioOrTTS(m);
    
    // Track that user is viewing this artwork result
    sessionStorage.setItem('last_viewed_artwork_id', m.id);
    startTrackingResultView(m.id);
  } else {
    artTitle.textContent = 'No match';
    artMeta.textContent = '';
    artShort.textContent = '';
    confidenceBadge.textContent = '—';
    addToTourBtn.onclick = null;
    playAudioBtn.onclick = null;
    sessionStorage.removeItem('last_viewed_artwork_id');
    // Hide timer for no match
    if (viewTimeContainer) {
      viewTimeContainer.classList.add('hidden');
    }
  }
  distanceVal.textContent = data.hamming_distance != null ? String(data.hamming_distance) : '—';
  textureVal.textContent = data.texture_edge_density != null ? String(data.texture_edge_density) : '—';

  // palette
  paletteEl.innerHTML = '';
  (data.palette || []).forEach(p => {
    const div = document.createElement('div');
    div.className = 'swatch';
    div.title = `${p.hex} · ${p.percent}%`;
    div.style.background = p.hex;
    paletteEl.appendChild(div);
  });

  statusMsg.textContent = 'Done.';
}

// --- Test Mode ---
async function runTestMode() {
  try {
    const res = await fetch('/demo_mode_images/test1.jpg');
    const blob = await res.blob();
    const dataUrl = await new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(blob);
    });
    await analyzeDataURL(dataUrl);
  } catch (e) {
    statusMsg.textContent = 'Failed to load test image.';
  }
}

// --- Tour ---
function getTour() {
  return JSON.parse(localStorage.getItem('scanart_tour') || '[]');
}
function saveTour(arr) {
  localStorage.setItem('scanart_tour', JSON.stringify(arr));
  renderTour();
}
function addToTour(id) { const t = getTour(); if (!t.includes(id)) { t.push(id); saveTour(t); recordEvent({ event_type: 'add_to_tour', artwork_id: id }); } }
function nextInTour() {
  const t = getTour();
  if (!t.length) return;
  const id = t[0];
  try {
    const win = window.open(`/artwork-page/${id}`, '_blank');
    if (!win) {
      statusMsg.textContent = 'Popup blocked. Allow popups for Next.';
    } else {
      statusMsg.textContent = `Opening ${id}…`;
    }
  } catch (e) {
    statusMsg.textContent = 'Unable to open artwork page.';
  }
}
function clearTour() { saveTour([]); statusMsg.textContent = 'Tour cleared.'; }
function renderTour() {
  const t = getTour();
  tourList.innerHTML = '';
  t.forEach(id => {
    const li = document.createElement('li');
    li.textContent = id;
    tourList.appendChild(li);
  });
}

// --- Audio ---
function playAudioOrTTS(meta) {
  if (meta && meta.audio_url) {
    const a = new Audio(meta.audio_url);
    a.play().then(() => recordEvent({ event_type: 'play_audio', artwork_id: meta.id })).catch(() => tts(meta));
  } else {
    tts(meta);
  }
}
function tts(meta) {
  try {
    const utter = new SpeechSynthesisUtterance(`${meta?.title || 'Unknown artwork'}. ${meta?.description_short || ''}`);
    window.speechSynthesis.speak(utter);
  } catch {}
}

// --- Bindings ---
captureBtn.addEventListener('click', async () => {
  const dataUrl = snapshotToDataURL();
  if (!dataUrl) {
    statusMsg.textContent = 'Camera not ready.';
    return;
  }
  await analyzeDataURL(dataUrl);
});
testModeBtn.addEventListener('click', () => { runTestMode(); });
tourNextBtn.addEventListener('click', () => { nextInTour(); });
tourClearBtn.addEventListener('click', () => { clearTour(); });

// --- Startup ---
(async function() {
  sessionStorage.setItem('scanart_open_ts', String(Date.now()));
  initConsent();
  renderTour();
  await startCamera();
  // try to warm cache of artworks
  fetch('/artworks.json').catch(() => {});
})();


