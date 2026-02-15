(function () {
  const cfg = window.SOFTPHONE_CFG;
  const statusEl = document.getElementById("status");
  const dialEl = document.getElementById("dial");

  const incomingBox = document.getElementById("incoming");
  const callerEl = document.getElementById("caller");

  const remoteAudio = document.getElementById("remoteAudio");

  const btnCall = document.getElementById("btnCall");
  const btnHangup = document.getElementById("btnHangup");
  const btnAnswer = document.getElementById("btnAnswer");
  const btnReject = document.getElementById("btnReject");

  const btnMute = document.getElementById("btnMute");
  const btnHold = document.getElementById("btnHold");

  const transferTo = document.getElementById("transferTo");
  const btnTransfer = document.getElementById("btnTransfer");

  function setStatus(s) { statusEl.textContent = s; }

  if (!window.JsSIP) {
    setStatus("JsSIP not loaded. Put jssip.min.js in /static/telephony/");
    return;
  }

  const socket = new JsSIP.WebSocketInterface(cfg.wss_url);

  const iceServers = [];
  if (cfg.stun_url) iceServers.push({ urls: [cfg.stun_url] });
  if (cfg.turn_url && cfg.turn_user && cfg.turn_pass) {
    iceServers.push({ urls: [cfg.turn_url], username: cfg.turn_user, credential: cfg.turn_pass });
  }

  const configuration = {
    sockets: [socket],
    uri: `sip:${cfg.sip_username}@${cfg.sip_domain}`,
    password: cfg.sip_secret,
    display_name: cfg.display_name,
    session_timers: false,
  };

  const ua = new JsSIP.UA(configuration);

  let currentSession = null;
  let incomingSession = null;
  let muted = false;
  let onHold = false;

  ua.on("connected", () => setStatus("WS connected"));
  ua.on("disconnected", () => setStatus("WS disconnected"));
  ua.on("registered", () => setStatus("Registered"));
  ua.on("unregistered", () => setStatus("Unregistered"));
  ua.on("registrationFailed", (e) => setStatus("Reg failed: " + (e?.cause || "")));

  ua.on("newRTCSession", function (data) {
    const session = data.session;

    session.on("peerconnection", () => {
      const pc = session.connection;
      pc.ontrack = (ev) => { remoteAudio.srcObject = ev.streams[0]; };
    });

    if (data.originator === "remote") {
      incomingSession = session;
      const from = session.remote_identity.uri.toString();
      callerEl.textContent = from;
      incomingBox.style.display = "block";

      session.on("ended", () => resetSessions());
      session.on("failed", () => resetSessions());
    } else {
      currentSession = session;
      session.on("ended", () => resetSessions());
      session.on("failed", () => resetSessions());
    }
  });

  function resetSessions(){
    incomingBox.style.display = "none";
    currentSession = null;
    incomingSession = null;
    muted = false;
    onHold = false;
    btnMute.textContent = "Mute";
    btnHold.textContent = "Hold";
  }

  function makeCall(target) {
    const options = {
      mediaConstraints: { audio: true, video: false },
      pcConfig: { iceServers },
      rtcOfferConstraints: { offerToReceiveAudio: 1, offerToReceiveVideo: 0 },
    };
    ua.call(`sip:${target}@${cfg.sip_domain}`, options);
  }

  btnCall.onclick = () => {
    const t = (dialEl.value || "").trim();
    if (!t) return;
    makeCall(t);
  };

  btnHangup.onclick = () => {
    if (currentSession) currentSession.terminate();
    if (incomingSession) incomingSession.terminate();
    resetSessions();
  };

  btnAnswer.onclick = () => {
    if (!incomingSession) return;
    incomingSession.answer({
      mediaConstraints: { audio: true, video: false },
      pcConfig: { iceServers },
    });
    // after answer, treat it as currentSession
    currentSession = incomingSession;
    incomingSession = null;
    incomingBox.style.display = "none";
  };

  btnReject.onclick = () => {
    if (incomingSession) incomingSession.terminate();
    resetSessions();
  };

  btnMute.onclick = () => {
    if (!currentSession) return;
    muted = !muted;
    if (muted) currentSession.mute({ audio: true });
    else currentSession.unmute({ audio: true });
    btnMute.textContent = muted ? "Unmute" : "Mute";
  };

  btnHold.onclick = () => {
    if (!currentSession) return;
    onHold = !onHold;
    if (onHold) currentSession.hold();
    else currentSession.unhold();
    btnHold.textContent = onHold ? "Unhold" : "Hold";
  };

  btnTransfer.onclick = () => {
    if (!currentSession) return;
    const t = (transferTo.value||"").trim();
    if (!t) return;
    // Blind transfer via REFER (PBX must support it)
    try{
      currentSession.refer(`sip:${t}@${cfg.sip_domain}`);
    }catch(e){
      setStatus("Transfer failed: " + e);
    }
  };

  setStatus("Starting...");
  ua.start();
})();
