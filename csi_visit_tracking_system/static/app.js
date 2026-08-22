// Voice dictation via the browser's built-in Web Speech API.
// Works in Chrome/Edge (desktop + Android). Safari/Firefox support is
// spotty, so we fall back to a plain text box automatically if the API
// isn't available or errors out.
function initDictation(micBtnId, transcriptId, hintId) {
  const micBtn = document.getElementById(micBtnId);
  const transcriptEl = document.getElementById(transcriptId);
  const hintEl = document.getElementById(hintId);
  if (!micBtn || !transcriptEl) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (hintEl) hintEl.textContent = "Voice dictation isn't supported in this browser — type your note below instead.";
    micBtn.style.display = "none";
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  let recording = false;
  let finalTranscript = transcriptEl.value || "";

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      if (res.isFinal) {
        finalTranscript += res[0].transcript + " ";
      } else {
        interim += res[0].transcript;
      }
    }
    transcriptEl.value = (finalTranscript + interim).trim();
  };

  recognition.onerror = (event) => {
    if (hintEl) hintEl.textContent = "Could not capture audio, try again. (" + event.error + ")";
    stop();
  };

  recognition.onend = () => {
    if (recording) {
      // Some browsers stop after a pause; restart if the user hasn't tapped stop.
      try { recognition.start(); } catch (e) { /* already started */ }
    }
  };

  function start() {
    recording = true;
    micBtn.classList.add("recording");
    if (hintEl) hintEl.textContent = "Listening… tap the mic again to stop.";
    try { recognition.start(); } catch (e) { /* no-op if already running */ }
  }

  function stop() {
    recording = false;
    micBtn.classList.remove("recording");
    if (hintEl) hintEl.textContent = "Tap the mic to dictate your visit note.";
    try { recognition.stop(); } catch (e) { /* no-op */ }
  }

  micBtn.addEventListener("click", () => {
    if (recording) stop(); else start();
  });
}

// Lightweight CSS-only confetti burst for the celebration screen.
function launchConfetti(containerId, count) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const colors = ["var(--celebrate-1)", "var(--celebrate-2)", "var(--celebrate-3)", "var(--celebrate-4)", "var(--celebrate-5)"];
  for (let i = 0; i < (count || 60); i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "%";
    piece.style.background = colors[i % colors.length];
    piece.style.animationDuration = (2 + Math.random() * 2) + "s";
    piece.style.animationDelay = (Math.random() * 0.6) + "s";
    piece.style.transform = "rotate(" + Math.floor(Math.random() * 360) + "deg)";
    container.appendChild(piece);
  }
}
