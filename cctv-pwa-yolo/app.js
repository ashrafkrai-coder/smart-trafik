const CAMERAS = [
  { id: "pintu_depan", title: "Pintu Depan", traffic: true },
  { id: "halaman", title: "Halaman", traffic: false },
  { id: "dapur", title: "Dapur", traffic: false },
];

const SNAPSHOT_INTERVAL_MS = 3000;
const TRAFFIC_INTERVAL_MS = 3000;

const cameraGrid = document.getElementById("camera-grid");
const backendPill = document.getElementById("backend-pill");
const backendLabel = document.getElementById("backend-label");
const clockEl = document.getElementById("clock");
const trafficHero = document.getElementById("traffic-hero");
const trafficBadge = document.getElementById("traffic-badge");
const trafficUpdated = document.getElementById("traffic-updated");
const liveModal = document.getElementById("live-modal");
const liveFrame = document.getElementById("live-frame");
const modalTitle = document.getElementById("modal-title");
const modalClose = document.getElementById("modal-close");

const cameraState = new Map();

function formatTime(date = new Date()) {
  return date.toLocaleTimeString("ms-MY", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function snapshotUrl(cameraId) {
  return `/api/frame.jpeg?src=${encodeURIComponent(cameraId)}&t=${Date.now()}`;
}

function webrtcUrl(cameraId) {
  return `/stream.html?src=${encodeURIComponent(cameraId)}&mode=webrtc`;
}

function setBackendStatus(online) {
  backendPill.classList.toggle("online", online);
  backendPill.classList.toggle("offline", !online);
  backendLabel.textContent = online ? "go2rtc ONLINE" : "go2rtc OFFLINE";
}

function setCameraStatus(card, online) {
  const badge = card.querySelector(".status-badge");
  badge.textContent = online ? "ONLINE" : "OFFLINE";
  badge.classList.toggle("online", online);
  badge.classList.toggle("offline", !online);
  card.querySelector(".live-btn").disabled = !online;
}

function renderCameras() {
  cameraGrid.innerHTML = CAMERAS.map((cam) => `
    <article class="camera-card" data-camera="${cam.id}">
      <div class="camera-head">
        <h2 class="camera-title">${cam.title}</h2>
        <span class="status-badge offline">OFFLINE</span>
      </div>
      <div class="frame-wrap">
        <iframe data-role="stream" src="" frameborder="0" allow="autoplay" style="display:none;"></iframe>
        <div class="overlay">
          <div class="traffic-chip" data-role="traffic">${cam.traffic ? "Menunggu analisis…" : "Tiada overlay AI"}</div>
          <div class="timestamp" data-role="stamp">Dikemas kini pada: --:--:--</div>
        </div>
      </div>
      <div class="camera-actions">
        <button type="button" class="btn live-btn" data-live="${cam.id}" disabled>Live Stream</button>
      </div>
    </article>
  `).join("");

  CAMERAS.forEach((cam) => {
    const card = cameraGrid.querySelector(`[data-camera="${cam.id}"]`);
    const iframe = card.querySelector('iframe[data-role="stream"]');
    cameraState.set(cam.id, { card, iframe, online: false });
  });
}

async function refreshSnapshot(cameraId) {
  const state = cameraState.get(cameraId);
  if (!state) return;

  try {
    // Check stream status via go2rtc API
    const response = await fetch(`/api/streams`, { cache: "no-store" });
    const data = await response.json();
    const stream = data[cameraId];
    const hasProducer = stream?.producers?.some(p => p.url) ?? false;

    if (hasProducer) {
      // Use WebRTC/MSE stream in iframe
      state.iframe.src = webrtcUrl(cameraId);
      state.iframe.style.display = "block";
      state.online = true;
      setCameraStatus(state.card, true);
      state.card.querySelector('[data-role="stamp"]').textContent =
        `Dikemas kini pada: ${formatTime()}`;
    } else {
      state.iframe.style.display = "none";
      state.online = false;
      setCameraStatus(state.card, false);
    }
  } catch (_err) {
    state.iframe.style.display = "none";
    state.online = false;
    setCameraStatus(state.card, false);
  }
  updateGlobalBackend();
}

function updateGlobalBackend() {
  const anyOnline = [...cameraState.values()].some((item) => item.online);
  setBackendStatus(anyOnline);
}

function applyTraffic(data) {
  const counts = data.counts || {};
  trafficBadge.textContent = data.badge || `🚗 ${counts.total || 0} Kenderaan | Kepadatan: ${data.density || "Rendah"}`;
  trafficUpdated.textContent = `Dikemas kini pada: ${data.updated_at || formatTime()}`;
  document.getElementById("count-car").textContent = String(counts.car || 0);
  document.getElementById("count-motorcycle").textContent = String(counts.motorcycle || 0);
  document.getElementById("count-bus").textContent = String(counts.bus || 0);
  document.getElementById("count-truck").textContent = String(counts.truck || 0);

  trafficHero.classList.remove("density-low", "density-medium", "density-high");
  trafficHero.classList.add(`density-${data.density_level || "low"}`);

  const target = cameraState.get(data.camera || "pintu_depan");
  if (target) {
    target.card.querySelector('[data-role="traffic"]').textContent =
      data.badge || `🚗 ${counts.total || 0} Kenderaan | Kepadatan: ${data.density || "Rendah"}`;
  }
}

async function refreshTraffic() {
  try {
    const response = await fetch(`/traffic_data.json?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error("traffic_data.json tidak tersedia");
    const data = await response.json();
    applyTraffic(data);
  } catch (_err) {
    trafficUpdated.textContent = "Dikemas kini pada: --:--:-- (menunggu analyzer)";
  }
}

function openLive(cameraId) {
  const cam = CAMERAS.find((item) => item.id === cameraId);
  modalTitle.textContent = `Live Stream — ${cam ? cam.title : cameraId}`;
  liveFrame.src = webrtcUrl(cameraId);
  liveModal.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeLive() {
  liveModal.hidden = true;
  liveFrame.src = "";
  document.body.style.overflow = "";
}

function tickClock() {
  clockEl.textContent = formatTime();
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => {
      /* Abaikan ralat SW semasa dibuka sebagai fail tempatan */
    });
  });
}

function init() {
  renderCameras();
  tickClock();
  setInterval(tickClock, 1000);

  CAMERAS.forEach((cam) => refreshSnapshot(cam.id));
  setInterval(() => {
    CAMERAS.forEach((cam) => refreshSnapshot(cam.id));
  }, SNAPSHOT_INTERVAL_MS);

  refreshTraffic();
  setInterval(refreshTraffic, TRAFFIC_INTERVAL_MS);

  cameraGrid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-live]");
    if (!button || button.disabled) return;
    openLive(button.getAttribute("data-live"));
  });

  modalClose.addEventListener("click", closeLive);
  liveModal.querySelector("[data-close-modal]").addEventListener("click", closeLive);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !liveModal.hidden) closeLive();
  });

  registerServiceWorker();
}

init();
