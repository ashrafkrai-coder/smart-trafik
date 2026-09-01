const HLS_URL = (import.meta.env.VITE_HLS_URL || "").trim();

if (HLS_URL) {
  const image = document.getElementById("videoFeed");
  const player = document.getElementById("player");
  const state = document.getElementById("feedState");
  const placeholder = document.getElementById("feedPlaceholder");
  const refresh = document.getElementById("refreshBtn");
  const play = document.getElementById("playBtn");
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
    } else if (window.Hls?.isSupported()) {
      hls = new window.Hls({ enableWorker: true, lowLatencyMode: true });
      hls.loadSource(HLS_URL);
      hls.attachMedia(video);
      hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => setState("PLAY TEKANAN DIPERLUKAN"));
      });
      hls.on(window.Hls.Events.ERROR, (_, details) => {
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
  refresh.addEventListener("click", () => {
    if (hls) hls.stopLoad();
    video.dataset.started = "false";
    start();
  });
  play.addEventListener("click", () => {
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  });

  window.addEventListener("load", start, { once: true });
  setTimeout(start, 0);
}
