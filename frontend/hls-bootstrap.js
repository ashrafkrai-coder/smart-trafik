import Hls from "hls.js";

const HLS_URL = (import.meta.env.VITE_HLS_URL || "").trim();
window.__hlsEnabled = Boolean(HLS_URL);

if (HLS_URL) {
  const image = document.getElementById("videoFeed");
  const player = document.getElementById("player");
  const state = document.getElementById("feedState");
  const placeholder = document.getElementById("feedPlaceholder");
  const refresh = document.getElementById("refreshBtn");
  const play = document.getElementById("playBtn");
  const resume = document.getElementById("resumeBtn");
  const video = document.createElement("video");
  let hls;

  video.className = "video-feed hls-feed";
  video.muted = true;
  video.autoplay = true;
  video.playsInline = true;
  video.setAttribute("aria-label", "Siaran HLS CCTV");
  player.insertBefore(video, image);
  image.hidden = true;

  const setState = (value) => {
    state.textContent = value;
    document.getElementById("liveLabel").classList.toggle("offline", value !== "LIVE FEED ACTIVE");
  };

  const start = () => {
    if (video.dataset.started === "true") return;
    video.dataset.started = "true";
    setState("RECONNECTING");

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = HLS_URL;
      video.play().catch(() => setState("PLAY TEKANAN DIPERLUKAN"));
    } else if (Hls.isSupported()) {
        hls = new Hls({ enableWorker: true, lowLatencyMode: true });
        hls.loadSource(HLS_URL);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play().catch(() => setState("PLAY TEKANAN DIPERLUKAN"));
        });
        hls.on(Hls.Events.ERROR, (_, details) => {
          if (details.fatal) setState("HLS OFFLINE");
        });
    } else {
      setState("HLS TIDAK DISOKONG");
    }
  };

  video.addEventListener("loadeddata", () => {
    placeholder.hidden = true;
    setState("LIVE FEED ACTIVE");
  });
  video.addEventListener("error", () => setState("HLS OFFLINE"));

  const restart = () => {
    if (hls) {
      hls.destroy();
      hls = undefined;
    }
    video.removeAttribute("src");
    video.dataset.started = "false";
    start();
  };

  const togglePlayback = () => {
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  };

  refresh.addEventListener("click", restart);
  document.getElementById("settingsReconnectBtn")?.addEventListener("click", restart);
  play.addEventListener("click", togglePlayback);
  resume?.addEventListener("click", togglePlayback);
  video.addEventListener("play", () => {
    placeholder.hidden = true;
    document.getElementById("paused").classList.remove("show");
    document.getElementById("playBtn").textContent = "\u23f8";
  });
  video.addEventListener("pause", () => {
    document.getElementById("playBtn").textContent = "\u25b6";
  });

  window.addEventListener("load", start, { once: true });
  setTimeout(start, 0);
}
