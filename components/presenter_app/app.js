const $ = id => document.getElementById(id);
const stages = [
  ["Meet Reachy", "Before the talk, invite volunteers to share a name and one fact. Repeat it and confirm consent before storing it.", ["Agent Memory", "Robot I/O"]],
  ["Where should this go?", "Reachy faces a volunteer, waves, and routes their question. Explain the route shown in the component trail.", ["Decision Router", "Tracking"]],
  ["Do you remember me?", "Choose an opted-in volunteer. Ask: What do you remember about me?", ["Agent Memory"]],
  ["Have I heard this before?", "Ask a public FAQ twice. Show the local similarity-cache miss and hit.", ["LangCache"]],
  ["Find the rule", "Ask for the priority or charging rule. Point to the cited handbook evidence.", ["Redis Search", "Context Retriever"]],
  ["The world changed", "Set the charging station CLOSED, then ask for its current status. Show the direct Redis write badge.", ["Simulated RDI", "Redis JSON"]],
  ["Put it together", "Choose another volunteer and ask: Combine what you remember about me with the priority rule and charging status.", ["Memory", "Search", "Status"]],
];
let stageIndex = 0;
let statusCache = {audio_muted: true};
let readbackPreview = null;

function toast(message) { const el = $("toast"); el.textContent = message; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 4000); }
async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options});
  let data; try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}
function node(tag, className, text) { const n = document.createElement(tag); if(className) n.className=className; if(text!==undefined) n.textContent=text; return n; }
function renderStages() {
  const host = $("stages"); host.replaceChildren();
  stages.forEach((stage, i) => {
    const button = node("button", "stage" + (i === stageIndex ? " active" : ""));
    button.append(node("span", "num", `0${i+1}`), node("span", "", stage[0]));
    button.onclick = () => { stageIndex=i; renderStages(); };
    host.append(button);
  });
  const [title, script, components] = stages[stageIndex];
  $("stage-number").textContent = `SCENE 0${stageIndex+1}`;
  $("stage-title").textContent = title;
  $("stage-script").textContent = script;
  $("stage-components").replaceChildren(...components.map(c => node("span", "badge local", c)));
}
function renderSystems(s) {
  const systems = [
    ["Redis Enterprise", s.redis.reachable ? "CONNECTED" : "PENDING", s.redis.reachable ? "native" : "pending"],
    ["Redis Search + JSON", s.redis.search_json_ready ? "NATIVE" : "PENDING", s.redis.search_json_ready ? "native" : "pending"],
    ["Agent Memory", "LOCAL EQUIVALENT", "local"],
    ["LangCache", "LOCAL SIMILARITY", "local"],
    ["Context Retriever", "LOCAL ASSEMBLER", "local"],
    ["RDI", "DIRECT-WRITE SIM", "simulated"],
    ["Router", s.router_calls_verified && !s.router_error ? "JEV VERIFIED" : s.router_service_configured ? "JEV CONFIGURED" : "RULES FALLBACK", "local"],
    ["Participant tracking", s.vision.startsWith("RT-DETR") ? "RT-DETR + BYTETRACK" : "MOCK / OFF", "local"],
    ["Reachy Mini", s.robot === "physical" ? "PHYSICAL" : "MOCK", "local"],
    ["HF speech recognition", s.hf_asr_configured ? "CONFIGURED" : "PENDING", "pending"],
    ["HF answer model", s.hf_answer_configured ? "CONFIGURED" : "PENDING", "pending"],
    ["Speech output", s.tts_provider ? `${s.tts_provider.toUpperCase()} · ${s.speaker_available ? "LAPTOP READY" : "CONFIGURED"}` : "PENDING", "pending"],
    ["Native Iris APIs", "UNVERIFIED", "pending"],
  ];
  $("systems").replaceChildren(...systems.map(([name,label,kind]) => { const div=node("div","system-item"); div.append(node("strong","",name),node("span",`badge ${kind}`,label)); return div; }));
}
async function refreshStatus() {
  try {
    const s = await api("/api/status"); statusCache=s;
    $("event-name").textContent=s.event_id;
    $("ready-dot").classList.toggle("ok",s.redis.reachable);
    $("ready-text").textContent=s.redis.reachable ? "Redis Enterprise connected" : "Redis Enterprise needs setup";
    $("robot-text").textContent=`Reachy: ${s.robot} · Vision: ${s.vision} · Laptop speaker: ${s.speaker_available ? s.speaker_device : s.audio_muted ? "MUTED" : "UNAVAILABLE"}${s.event_closed ? " · EVENT ENDED" : ""}`;
    $("attention-mode").textContent=s.vision;
    $("speech-note").textContent=s.hf_asr_configured ? "Reachy microphone uses configured HF speech endpoint." : "HF speech endpoint pending: use presenter text for rehearsal.";
    $("listen").disabled=!s.hf_asr_configured || s.robot!=="physical" || s.event_closed;
    $("listen-name").disabled=!s.hf_asr_configured || s.robot!=="physical" || s.event_closed;
    $("listen-fact").disabled=!s.hf_asr_configured || s.robot!=="physical" || s.event_closed;
    $("mock-three").hidden=s.robot!=="mock";
    for(const id of ["name","fact","consent","readback","register","participant","identified","question","ask","station-open","station-closed","mock-three","skip","next","end-event"]){
      $(id).disabled=Boolean(s.event_closed) || (id==="register" && (!readbackPreview || !$("consent").checked));
    }
    $("prompt-chips").querySelectorAll("button").forEach(button=>{button.disabled=Boolean(s.event_closed);});
    renderSystems(s);
    if (s.redis.reachable && !s.event_closed) await api("/api/setup",{method:"POST"});
    await refreshBoard(); await refreshParticipants();
  } catch(error){ toast(error.message); }
}
async function refreshParticipants() {
  try {
    const people=await api("/api/participants"); const select=$("participant"), previous=select.value;
    select.replaceChildren(new Option("Public question / no identified participant",""));
    people.forEach(p=>select.append(new Option(p.name,p.id)));
    select.value=previous;
  } catch { /* Redis may not be provisioned yet. */ }
}
async function refreshBoard() { try { const board=await api("/api/board"); $("station-status").textContent=board.status; } catch { $("station-status").textContent="PENDING"; } }
async function refreshAttention() {
  try {
    const a=await api("/api/attention"); $("attention-state").textContent=a.state; $("active-track").textContent=a.active_track_id===null?"No active target":`Track ${a.active_track_id} invited`;
    const tracks=$("tracks"); tracks.replaceChildren();
    a.tracks.forEach(t=>{ const b=node("button","track"+(t.track_id===a.active_track_id?" active":""),`Person ${t.track_id}${a.served_track_ids.includes(t.track_id)?" · served":""}`); b.onclick=async()=>{ try { await api("/api/attention/select",{method:"POST",body:JSON.stringify({track_id:t.track_id})}); refreshAttention(); }catch(e){toast(e.message);} }; tracks.append(b); });
    if(!a.tracks.length) tracks.append(node("span","muted","No person tracks visible"));
  }catch(error){toast(error.message);}
}
function renderAnswer(result) {
  $("answer").textContent=result.text;
  $("route-badge").textContent=`${result.route.toUpperCase()} · ${result.cache_hit?"CACHE HIT":"NEW ANSWER"}`;
  $("evidence").replaceChildren(...(result.evidence.length?result.evidence.map(e=>{const div=node("div","evidence-item");div.append(node("strong","",e.title),node("small","",`${e.provenance} · ${e.text}`));return div;}):[node("p","muted","No external evidence for this answer.")]));
  $("trace").replaceChildren(...result.trace.map(t=>{const div=node("div","trace-item");div.append(node("strong","",t.component),node("small","",`${t.mode} · ${t.detail}`));return div;}));
  if(!statusCache.audio_muted && result.speech!=="played on laptop" && "speechSynthesis" in window){ speechSynthesis.cancel(); const utterance=new SpeechSynthesisUtterance(result.text); utterance.rate=0.98; speechSynthesis.speak(utterance); toast(`Browser narration used. Laptop speech: ${result.speech}.`); }
}
$("refresh").onclick=refreshStatus;
for (const id of ["name","fact","consent"]) $(id).addEventListener("input",()=>{readbackPreview=null;$("register").disabled=true;});
$("readback").onclick=async()=>{try{const body={name:$("name").value,fact:$("fact").value,consent:$("consent").checked};const result=await api("/api/readback",{method:"POST",body:JSON.stringify(body)});readbackPreview=JSON.stringify(body);$("registration-result").textContent=result.text;$("register").disabled=!body.consent;if(!statusCache.audio_muted&&result.speech!=="played on laptop"&&"speechSynthesis" in window){speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(result.text));toast("Presenter browser readback; laptop speech endpoint pending.");}}catch(e){toast(e.message);}};
$("register").onclick=async()=>{try{const body={name:$("name").value,fact:$("fact").value,consent:$("consent").checked};if(readbackPreview!==JSON.stringify(body))throw new Error("Read back the name and fact again before confirming");const result=await api("/api/register",{method:"POST",body:JSON.stringify(body)});$("registration-result").textContent=`Confirmed: ${result.name} — ${result.fact}. Event-only.`;$("register").disabled=true;readbackPreview=null;await refreshParticipants();}catch(e){toast(e.message);}};
$("ask").onclick=async()=>{try{const result=await api("/api/ask",{method:"POST",body:JSON.stringify({question:$("question").value,participant_id:$("participant").value||null,identified_in_conversation:$("identified").checked})});renderAnswer(result);$("identified").checked=false;await refreshAttention();await refreshStatus();}catch(e){toast(e.message);}};
async function listenInto(id,button){try{button.disabled=true;toast("Listening on Reachy for five seconds…");const result=await api("/api/listen",{method:"POST"});$(id).value=result.text;$(id).dispatchEvent(new Event("input"));}catch(e){toast(e.message);}finally{button.disabled=false;}}
$("listen").onclick=()=>listenInto("question",$("listen"));
$("listen-name").onclick=()=>listenInto("name",$("listen-name"));
$("listen-fact").onclick=()=>listenInto("fact",$("listen-fact"));
$("station-open").onclick=()=>setStation("OPEN");$("station-closed").onclick=()=>setStation("CLOSED");
async function setStation(status){try{await api("/api/board",{method:"POST",body:JSON.stringify({status})});await refreshBoard();toast(`Charging station is ${status}. Direct Redis write: simulated RDI.`);}catch(e){toast(e.message);}}
$("mock-three").onclick=async()=>{try{await api("/api/mock/tracks",{method:"POST",body:JSON.stringify({count:3})});await refreshAttention();}catch(e){toast(e.message);}};
$("skip").onclick=async()=>{try{await api("/api/attention/skip",{method:"POST"});await refreshAttention();}catch(e){toast(e.message);}};
$("next").onclick=async()=>{try{await api("/api/attention/next",{method:"POST"});await refreshAttention();}catch(e){toast(e.message);}};
$("end-event").onclick=async()=>{if(!confirm("Delete all facts, session events, cache entries, and mission data for this event?"))return;try{const result=await api("/api/event/end",{method:"POST"});if("speechSynthesis" in window)speechSynthesis.cancel();for(const id of ["name","fact","question"])$(id).value="";$("consent").checked=false;$("identified").checked=false;$("registration-result").textContent="";$("answer").textContent="Event ended. Participant facts and mission data were deleted.";$("evidence").replaceChildren();$("trace").replaceChildren();$("route-badge").textContent="EVENT ENDED";readbackPreview=null;toast(`Event ended. ${result.deleted_event_keys} event keys deleted.`);await refreshStatus();}catch(e){toast(e.message);}};
const prompts=["What do you remember about me?","What does Redis Iris help an agent do?","What is the priority delivery rule?","Is the charging station open right now?","Combine what you remember about me with the priority rule and charging status."];
$("prompt-chips").replaceChildren(...prompts.map(p=>{const b=node("button","",p);b.onclick=()=>$("question").value=p;return b;}));
renderStages();refreshStatus();refreshAttention();setInterval(refreshAttention,2000);setInterval(refreshStatus,15000);
