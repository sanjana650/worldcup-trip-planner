/* ============================================================
   World Cup 2026 · Fan Trip Planner · frontend logic
   API contract UNCHANGED:  POST /api/chat  { message } -> { reply }
   ============================================================ */

const API_URL = "/api/chat";
const $ = (id) => document.getElementById(id);
const stream = $("stream"), input = $("input"), sendBtn = $("send"), clearBtn = $("clear-btn"),
  statusMeta = $("status-meta"), teamsEl = $("teams"), teamSearch = $("team-search"),
  teamBlock = $("team-block"), departureEl = $("departure"), citizenEl = $("citizenship"),
  budgetEl = $("budget"), budgetOut = $("budget-out"), planBtn = $("plan-btn"),
  planSummary = $("plan-summary"), modeSeg = $("mode-seg");

let mode = "team", selectedTeam = "England", busy = false;
let MAP_PROJECT = null;

/* Example prompts used by the welcome chips */
const EX = {
  england: "I want to follow England in the World Cup 2026. I am a British citizen flying from London Heathrow with a budget of USD 5000.",
  final:   "I want to plan a trip to watch the World Cup Final in July 2026. I am a British citizen flying from London Heathrow with a budget of USD 5000.",
  argentina:"I want to follow Argentina in the World Cup 2026. I am a British citizen flying from London Heathrow with a budget of USD 10000.",
};
const WELCOME_HTML = `<div class="welcome">
  <h2>Where are we headed?</h2>
  <p>Pick a team and your details on the right, or just describe the trip below. You'll get a structured
    itinerary with costs, visas, a budget verdict, plus your route drawn on the map.</p>
  <div class="hint">
    <button class="ex" data-ex="england">Follow England</button>
    <button class="ex" data-ex="final">Plan the Final</button>
    <button class="ex" data-ex="argentina">Argentina, $10k</button>
  </div>
</div>`;

/* ---------- Nations ---------- */
const TEAMS = [
  ["🏴\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}", "England"],
  ["🇦🇷", "Argentina"], ["🇧🇷", "Brazil"], ["🇫🇷", "France"], ["🇪🇸", "Spain"],
  ["🇵🇹", "Portugal"], ["🇳🇱", "Netherlands"], ["🇩🇪", "Germany"], ["🇧🇪", "Belgium"],
  ["🇭🇷", "Croatia"], ["🇮🇹", "Italy"], ["🇺🇸", "USA"], ["🇲🇽", "Mexico"],
  ["🇨🇦", "Canada"], ["🇯🇵", "Japan"], ["🇰🇷", "South Korea"], ["🇲🇦", "Morocco"],
  ["🇸🇳", "Senegal"], ["🇺🇾", "Uruguay"], ["🇨🇴", "Colombia"], ["🇨🇭", "Switzerland"],
  ["🇩🇰", "Denmark"], ["🇦🇺", "Australia"], ["🇵🇱", "Poland"], ["🇷🇸", "Serbia"],
  ["🇬🇭", "Ghana"], ["🇳🇬", "Nigeria"], ["🇪🇨", "Ecuador"], ["🇸🇦", "Saudi Arabia"],
  ["🇶🇦", "Qatar"], ["🇳🇴", "Norway"], ["🇪🇬", "Egypt"], ["🇨🇮", "Ivory Coast"],
  ["🇦🇹", "Austria"], ["🇹🇷", "Turkey"], ["🇸🇪", "Sweden"], ["🇨🇲", "Cameroon"],
  ["🇩🇿", "Algeria"], ["🇵🇪", "Peru"], ["🇨🇱", "Chile"], ["🇵🇾", "Paraguay"],
  ["🇺🇿", "Uzbekistan"], ["🇮🇷", "Iran"], ["🇯🇴", "Jordan"], ["🇳🇿", "New Zealand"],
  ["🇿🇦", "South Africa"], ["🇵🇦", "Panama"], ["🇨🇷", "Costa Rica"],
];
const flagFor = (name) => {
  if (!name) return "🏟️";
  const t = TEAMS.find(([, n]) => n.toLowerCase() === name.toLowerCase());
  return t ? t[0] : "🏟️";
};

/* ---------- 16 host cities: [name, country, lng, lat] ---------- */
const HOST_CITIES = [
  ["Vancouver","ca",-123.12,49.28],["Seattle","us",-122.33,47.61],["San Francisco","us",-122.00,37.40],
  ["Los Angeles","us",-118.34,33.95],["Kansas City","us",-94.48,39.05],["Dallas","us",-97.09,32.75],
  ["Houston","us",-95.41,29.68],["Atlanta","us",-84.40,33.76],["Miami","us",-80.24,25.96],
  ["Toronto","ca",-79.42,43.63],["Boston","us",-71.26,42.09],["New York / NJ","us",-74.07,40.81],
  ["Philadelphia","us",-75.17,39.90],["Monterrey","mx",-100.24,25.67],["Guadalajara","mx",-103.46,20.68],
  ["Mexico City","mx",-99.15,19.30],
];

/* ============================================================
   MAP
   ============================================================ */
const PIN_PATH = "M0,0 C-6,-9 -11,-13 -11,-20 A11,11 0 1,1 11,-20 C11,-13 6,-9 0,0 Z";
const pinSVG = (name, cc, x, y) => `<g class="pin ${cc}" data-city="${name}" transform="translate(${x.toFixed(1)},${y.toFixed(1)})">
  <g class="body" filter="url(#pinshadow)"><path d="${PIN_PATH}"/><circle cx="0" cy="-20" r="4.3" fill="#fff"/></g>
  <text class="lbl" y="-36" text-anchor="middle">${name}</text></g>`;
const defsSVG = () => `<defs><filter id="pinshadow" x="-60%" y="-60%" width="220%" height="220%">
  <feDropShadow dx="0" dy="2" stdDeviation="1.8" flood-color="rgba(27,26,22,.32)"/></filter></defs>`;
const MAP_W = 420, MAP_H = 320;

async function renderMap() {
  const host = $("map");
  try {
    if (!window.d3 || !window.topojson) throw new Error("map libs unavailable");
    const topo = await Promise.race([
      fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then((r) => { if (!r.ok) throw new Error("bad status"); return r.json(); }),
      new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), 8000)),
    ]);
    const feats = topojson.feature(topo, topo.objects.countries).features;
    const wanted = { "United States of America": "us", "Canada": "ca", "Mexico": "mx" };
    const picks = feats.filter((f) => wanted[f.properties.name]);
    if (!picks.length) throw new Error("no features");
    const frame = { type: "Polygon", coordinates: [[[-128, 60], [-66, 60], [-66, 14], [-128, 14], [-128, 60]]] };
    const proj = d3.geoMercator().fitExtent([[14, 40], [MAP_W - 14, MAP_H - 16]], frame);
    const path = d3.geoPath(proj);
    MAP_PROJECT = (lng, lat) => proj([lng, lat]);
    let svg = `<svg viewBox="0 0 ${MAP_W} ${MAP_H}" xmlns="http://www.w3.org/2000/svg">${defsSVG()}`;
    picks.forEach((f) => { svg += `<path class="country ${wanted[f.properties.name]}" d="${path(f)}"/>`; });
    svg += `<g id="wc-route"></g>`;
    HOST_CITIES.forEach(([name, cc, lng, lat]) => { const p = proj([lng, lat]); if (p) svg += pinSVG(name, cc, p[0], p[1]); });
    svg += `<g id="wc-route-top"></g></svg>`;
    host.innerHTML = svg;
  } catch (err) { renderMapFallback(host); }
}
function renderMapFallback(host) {
  const pad = 26, L = -128, R = -66, T = 60, B = 14;
  const X = (lng) => pad + ((lng - L) / (R - L)) * (MAP_W - 2 * pad);
  const Y = (lat) => pad + ((T - lat) / (T - B)) * (MAP_H - 2 * pad);
  MAP_PROJECT = (lng, lat) => [X(lng), Y(lat)];
  let svg = `<svg viewBox="0 0 ${MAP_W} ${MAP_H}" xmlns="http://www.w3.org/2000/svg">${defsSVG()}<g id="wc-route"></g>`;
  HOST_CITIES.forEach(([name, cc, lng, lat]) => { svg += pinSVG(name, cc, X(lng), Y(lat)); });
  svg += `<g id="wc-route-top"></g></svg>`;
  host.innerHTML = svg;
}

/* ---------- Route drawing ---------- */
function matchHost(cell) {
  const c = (cell || "").toLowerCase();
  return HOST_CITIES.find(([nm]) => {
    const k = nm.toLowerCase(), first = k.split(" / ")[0];
    return c.includes(k) || c.includes(first) || (k.startsWith("new york") && c.includes("new york"));
  }) || null;
}
function citiesFromTable(mdEl) {
  const table = mdEl.querySelector("table"); if (!table) return [];
  const heads = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim().toLowerCase());
  let idx = heads.findIndex((h) => h.includes("city")); if (idx < 0) return [];
  return [...table.querySelectorAll("tbody tr")].map((tr) => (tr.children[idx]?.textContent || "").trim()).filter(Boolean);
}
function resetRoute() {
  const map = $("map"); if (!map) return;
  map.classList.remove("has-route");
  const cap = $("map-caption"); if (cap) cap.innerHTML = "";
  const svg = map.querySelector("svg"); if (!svg) return;
  const a = svg.querySelector("#wc-route"), b = svg.querySelector("#wc-route-top");
  if (a) a.innerHTML = ""; if (b) b.innerHTML = "";
  svg.querySelectorAll(".pin.on-route").forEach((p) => p.classList.remove("on-route"));
}function drawRoute(cells) {
  const map = $("map"), svg = map && map.querySelector("svg");
  if (!svg || !MAP_PROJECT) return;
  const routeG = svg.querySelector("#wc-route"), topG = svg.querySelector("#wc-route-top"), cap = $("map-caption");
  routeG.innerHTML = ""; topG.innerHTML = "";

  const stops = [];
  cells.forEach((cell) => {
    const city = matchHost(cell); if (!city) return;
    const [x, y0] = MAP_PROJECT(city[2], city[3]); const y = y0 - 20;
    if (!stops.length || stops[stops.length - 1].name !== city[0]) stops.push({ name: city[0], x, y });
  });

  const names = new Set(stops.map((s) => s.name));
  svg.querySelectorAll(".pin").forEach((p) => p.classList.toggle("on-route", names.has(p.getAttribute("data-city"))));

  if (!stops.length) { map.classList.remove("has-route"); if (cap) cap.innerHTML = ""; return; }
  map.classList.add("has-route");

  if (stops.length >= 2) {
    const pts = stops.map((s) => `${s.x.toFixed(1)},${s.y.toFixed(1)}`).join(" ");
    routeG.innerHTML = `<polyline class="route-line" points="${pts}"></polyline>`
      + stops.map((s) => `<circle class="route-ring" cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="13"></circle>`).join("");
    const line = routeG.querySelector(".route-line");
    const len = line.getTotalLength();
    line.style.strokeDasharray = len; line.style.strokeDashoffset = len;
    requestAnimationFrame(() => { line.style.strokeDashoffset = 0; });
  }
  topG.innerHTML = stops.map((s, i) =>
    `<g class="route-badge"><circle cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="7"></circle>
     <text x="${s.x.toFixed(1)}" y="${s.y.toFixed(1)}" text-anchor="middle" dominant-baseline="central">${i + 1}</text></g>`).join("");

  if (cap) cap.innerHTML = "Your route: " + stops.map((s) => `<b>${s.name}</b>`).join(" &rarr; ");
}

/* ============================================================
   TEAM PICKER
   ============================================================ */
function renderTeams(filter = "") {
  const f = filter.trim().toLowerCase();
  teamsEl.innerHTML = "";
  TEAMS.filter(([, name]) => name.toLowerCase().includes(f)).forEach(([flag, name]) => {
    const b = document.createElement("button");
    b.className = "chip" + (name === selectedTeam ? " active" : "");
    b.innerHTML = `<span class="flag">${flag}</span>${name}`;
    b.onclick = () => { selectedTeam = name; renderTeams(teamSearch.value); updateSummary(); };
    teamsEl.appendChild(b);
  });
}
teamSearch.addEventListener("input", (e) => renderTeams(e.target.value));

/* ============================================================
   TRIP BUILDER
   ============================================================ */
function composedMessage() {
  const dep = (departureEl.value || "London Heathrow").trim();
  const cit = (citizenEl.value || "British").trim();
  const bud = parseInt(budgetEl.value, 10);
  return mode === "final"
    ? `I want to plan a trip to watch the World Cup Final in July 2026. I am a ${cit} citizen flying from ${dep} with a budget of USD ${bud}.`
    : `I want to follow ${selectedTeam} in the World Cup 2026. I am a ${cit} citizen flying from ${dep} with a budget of USD ${bud}.`;
}
function updateSummary() {
  const dep = (departureEl.value || "London Heathrow").trim();
  const bud = Number(budgetEl.value).toLocaleString();
  planSummary.innerHTML = mode === "final"
    ? `Plan a route to the <b>World Cup Final</b> from <b>${dep}</b>, capped at <b>USD ${bud}</b>.`
    : `Follow <b>${selectedTeam}</b> from <b>${dep}</b>, capped at <b>USD ${bud}</b>.`;
}
function paintBudget() {
  const min = +budgetEl.min, max = +budgetEl.max, val = +budgetEl.value;
  const pct = ((val - min) / (max - min)) * 100;
  budgetEl.style.background = `linear-gradient(90deg, var(--accent) 0%, var(--accent) ${pct}%, rgba(27,26,22,.14) ${pct}%, rgba(27,26,22,.14) 100%)`;
  budgetOut.textContent = val.toLocaleString();
}
modeSeg.addEventListener("click", (e) => {
  const btn = e.target.closest("button"); if (!btn) return;
  mode = btn.dataset.mode;
  [...modeSeg.children].forEach((c) => c.classList.toggle("active", c === btn));
  teamBlock.style.display = mode === "team" ? "" : "none";
  updateSummary();
});
budgetEl.addEventListener("input", () => { paintBudget(); updateSummary(); });
departureEl.addEventListener("input", updateSummary);
citizenEl.addEventListener("input", updateSummary);
planBtn.addEventListener("click", () => { if (!busy) sendMessage(composedMessage()); });

/* ============================================================
   COMPOSER
   ============================================================ */
input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 130) + "px"; });
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (!busy && input.value.trim()) sendMessage(input.value.trim()); }
});
sendBtn.addEventListener("click", () => { if (!busy && input.value.trim()) sendMessage(input.value.trim()); });
clearBtn.addEventListener("click", () => { if (!busy) { renderWelcome(); resetRoute(); setDefaultCountdown(); } });

/* clickable welcome example chips (event delegation) */
stream.addEventListener("click", (e) => {
  const chip = e.target.closest(".ex"); if (!chip || busy) return;
  const msg = EX[chip.dataset.ex]; if (msg) sendMessage(msg);
});

/* ============================================================
   STREAM / MESSAGES
   ============================================================ */
function renderWelcome() { stream.innerHTML = WELCOME_HTML; }
function clearWelcome() { const w = stream.querySelector(".welcome"); if (w) w.remove(); }
function scrollToTopOf(el) { stream.scrollTop = Math.max(0, el.offsetTop - 14); }
function scrollDown() { stream.scrollTop = stream.scrollHeight; }

function addUser(text) {
  clearWelcome();
  const el = document.createElement("div");
  el.className = "msg user";
  el.innerHTML = `<div class="who"><span class="dot"></span> You</div><div class="bubble"></div>`;
  el.querySelector(".bubble").textContent = text;
  stream.appendChild(el); scrollDown();
}
function addLoading() {
  const el = document.createElement("div");
  el.className = "msg bot"; el.id = "loading-msg";
  el.innerHTML = `<div class="who"><span class="dot"></span> Planner</div>
    <div class="bubble"><div class="typing"><span></span><span></span><span></span></div>
    <span style="color:var(--muted);font-size:.85rem;margin-left:6px">Plotting your route…</span></div>`;
  stream.appendChild(el); scrollDown();
}
const looksLikeError = (t) => /RESOURCE_EXHAUSTED|quota|^error\b|\b429\b|traceback|exception/i.test(t);

function preprocessReply(t) {
  if (!t) return t;
  const lines = t.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i].trim(); if (!ln) continue;
    if (!/^[#|>*\-\d]/.test(ln) && !ln.includes(":") && ln.length >= 12 && ln.length <= 90 && /\s/.test(ln)) lines[i] = "## " + ln;
    break;
  }
  let out = lines.join("\n");
  out = out.replace(/^([A-Za-z][A-Za-z0-9 .,&/()'-]{2,34}):\s*$/gm, "### $1");
  out = out.replace(/^([A-Za-z][A-Za-z0-9 .,&/()'-]{1,34}):[ \t]+(?=\S)/gm, "**$1:** ");
  return out;
}

const money = (n) => "$" + Number(n).toLocaleString();
function numFrom(re, t) { const m = t.match(re); return m ? parseInt(m[1].replace(/,/g, ""), 10) : null; }
function buildMeter(reply, mdEl) {
  const budget = numFrom(/budget(?:\s*status)?[:\s]+(?:of\s+)?USD\s*([\d,]+)/i, reply);
  const total  = numFrom(/total\s+estimated\s+cost[:\s]+USD\s*([\d,]+)/i, reply)
              || numFrom(/estimated\s+total\s+cost\s+of\s+USD\s*([\d,]+)/i, reply);
  if (budget == null || total == null) return null;
  const remaining = budget - total, over = remaining < 0;
  const pct = Math.max(2, Math.min(100, Math.round((total / budget) * 100)));
  let team = (reply.match(/team[:\s]+([A-Za-z ]{2,30})/i) || [])[1];
  team = team ? team.trim() : (mode === "final" ? "World Cup Final" : null);
  const stops = mdEl.querySelector("tbody") ? mdEl.querySelectorAll("tbody tr").length : null;

  const wrap = document.createElement("div");
  wrap.className = "meter";
  wrap.innerHTML = `
    <div class="meter-top">
      <div class="meter-team"><span class="flag">${flagFor(team)}</span>${team || "Your trip"}</div>
      <span class="verdict ${over ? "over" : "ok"}">${over ? "Over budget" : "Within budget"}</span>
    </div>
    <div class="meter-stats">
      <div class="ss"><div class="ss-l">Total cost</div><div class="ss-v">${money(total)}</div></div>
      <div class="ss"><div class="ss-l">Budget</div><div class="ss-v">${money(budget)}</div></div>
      <div class="ss"><div class="ss-l">${over ? "Over by" : "Remaining"}</div><div class="ss-v">${money(Math.abs(remaining))}</div></div>
      <div class="ss"><div class="ss-l">Stops</div><div class="ss-v">${stops != null ? stops : "n/a"}</div></div>
    </div>
    <div class="bar"><div class="bar-fill ${over ? "over" : ""}"></div></div>
    <div class="bar-cap">${money(total)} of ${money(budget)} used${over ? ", exceeds budget" : ""}</div>`;
  requestAnimationFrame(() => { const f = wrap.querySelector(".bar-fill"); if (f) f.style.width = pct + "%"; });
  return wrap;
}

function addBot(reply) {
  const isErr = looksLikeError(reply);
  const el = document.createElement("div");
  el.className = "msg bot" + (isErr ? " error" : "");
  let html;
  try { marked.setOptions({ gfm: true, breaks: true }); html = DOMPurify.sanitize(marked.parse(preprocessReply(reply || "*(empty response)*"))); }
  catch (_) { html = DOMPurify.sanitize((reply || "").replace(/\n/g, "<br>")); }

  el.innerHTML = `<div class="who"><span class="dot"></span> Planner</div>
    <div class="bubble"><div class="md">${html}</div>
      <div class="bubble-tools"><button class="copy-btn">copy</button></div></div>`;

  const mdEl = el.querySelector(".md");
  mdEl.querySelectorAll("table").forEach((t) => {
    const w = document.createElement("div"); w.className = "table-wrap";
    t.parentNode.insertBefore(w, t); w.appendChild(t);
  });
  mdEl.querySelectorAll("a").forEach((a) => { a.target = "_blank"; a.rel = "noopener noreferrer"; });

  if (!isErr) {
    const meter = buildMeter(reply, mdEl); if (meter) mdEl.parentNode.insertBefore(meter, mdEl);
    const cities = citiesFromTable(mdEl);
    if (cities.length) drawRoute(cities); else resetRoute();
    const fm = firstMatchFromTable(mdEl); if (fm) setTripCountdown(fm);
  }

  const btn = el.querySelector(".copy-btn");
  btn.onclick = () => navigator.clipboard.writeText(reply).then(() => { btn.textContent = "copied ✓"; setTimeout(() => (btn.textContent = "copy"), 1500); });

  stream.appendChild(el);
  requestAnimationFrame(() => scrollToTopOf(el));
}

/* ============================================================
   SEND -> /api/chat
   ============================================================ */
async function sendMessage(text) {
  if (busy || !text) return;
  busy = true; setBusy(true);
  addUser(text);
  if (input.value) { input.value = ""; input.style.height = "auto"; }
  addLoading();
  try {
    const res = await fetch(API_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text }) });
    $("loading-msg")?.remove();
    if (!res.ok) addBot(`**Error ${res.status}.** The planner responded with \`${res.status} ${res.statusText}\`. Please try again in a moment.`);
    else { const data = await res.json().catch(() => ({})); addBot(data.reply ?? "*(no reply field in response)*"); }
  } catch (err) {
    $("loading-msg")?.remove();
    addBot(`**Connection error.** Could not reach the planner.\n\n\`${err.message}\`\n\nCheck that the server is running on this host.`);
  } finally { busy = false; setBusy(false); }
}
function setBusy(on) {
  sendBtn.disabled = on; planBtn.disabled = on;
  statusMeta.textContent = on ? "thinking…" : "ready";
  if (sendBtn.childNodes[0]) sendBtn.childNodes[0].nodeValue = on ? "…" : "Send ";
}

/* ============================================================
   COUNTDOWN (default = opening match; switches to the user's
   first selected fixture once a trip is planned)
   ============================================================ */
const CD_BLOCKS = `<div class="cd"><span class="cd-n" id="cd-d">--</span><span class="cd-l">Days</span></div>
  <div class="cd"><span class="cd-n" id="cd-h">--</span><span class="cd-l">Hrs</span></div>
  <div class="cd"><span class="cd-n" id="cd-m">--</span><span class="cd-l">Min</span></div>
  <div class="cd"><span class="cd-n" id="cd-s">--</span><span class="cd-l">Sec</span></div>`;
let cdTimer = null;
function runCountdown(target, liveLabel) {
  if (cdTimer) { clearInterval(cdTimer); cdTimer = null; }
  const cd = $("countdown"); if (!cd) return;
  cd.innerHTML = CD_BLOCKS;
  const dEl = $("cd-d"), hEl = $("cd-h"), mEl = $("cd-m"), sEl = $("cd-s");
  const pad = (n) => String(n).padStart(2, "0");
  function tick() {
    let diff = Math.floor((target - new Date()) / 1000);
    if (diff <= 0) {
      cd.innerHTML = `<div class="cd live"><span class="cd-n">${liveLabel || "Underway"}</span><span class="cd-l">It's go time</span></div>`;
      clearInterval(cdTimer); cdTimer = null; return;
    }
    const d = Math.floor(diff / 86400); diff %= 86400;
    const h = Math.floor(diff / 3600); diff %= 3600;
    const m = Math.floor(diff / 60); const s = diff % 60;
    if (dEl) dEl.textContent = d; if (hEl) hEl.textContent = pad(h); if (mEl) mEl.textContent = pad(m); if (sEl) sEl.textContent = pad(s);
  }
  tick(); cdTimer = setInterval(tick, 1000);
}
function setDefaultCountdown() {
  $("cd-title").textContent = "Kick-off countdown";
  $("cd-desc").textContent = "Counting down to the opening match of the tournament.";
  $("keydates").innerHTML =
    `<div class="kd"><span>Opening match</span><b>Jun 11 · Mexico City</b></div>
     <div class="kd"><span>Final</span><b>Jul 19 · New York / NJ</b></div>
     <div class="kd"><span>Hosts</span><b>USA · Canada · Mexico</b></div>`;
  runCountdown(new Date("2026-06-11T00:00:00"), "Underway");
}
function setTripCountdown(fm) {
  $("cd-title").textContent = "Your first match";
  $("cd-desc").textContent = "Counting down to your opening fixture.";
  const rows = [];
  if (fm.match) rows.push(`<div class="kd"><span>Match</span><b>${fm.match}</b></div>`);
  rows.push(`<div class="kd"><span>Kick-off</span><b>${fm.dateLabel}${fm.city ? " · " + fm.city : ""}</b></div>`);
  if (fm.stops) rows.push(`<div class="kd"><span>Trip length</span><b>${fm.stops} stop${fm.stops > 1 ? "s" : ""}</b></div>`);
  $("keydates").innerHTML = rows.join("");
  runCountdown(fm.date, "Kick-off!");
}
function firstMatchFromTable(mdEl) {
  const table = mdEl.querySelector("table"); if (!table) return null;
  const heads = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim().toLowerCase());
  const di = heads.findIndex((h) => h.includes("date"));
  const mi = heads.findIndex((h) => h.includes("match") || h.includes("fixture"));
  const ci = heads.findIndex((h) => h.includes("city"));
  if (di < 0) return null;
  let best = null;
  const rows = [...table.querySelectorAll("tbody tr")];
  rows.forEach((tr) => {
    const m = (tr.children[di]?.textContent || "").match(/(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return;
    const dt = new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00`);
    if (!best || dt < best.date) {
      best = { date: dt,
        match: mi >= 0 ? (tr.children[mi]?.textContent || "").trim() : "",
        city: ci >= 0 ? (tr.children[ci]?.textContent || "").replace(/,.*$/, "").trim() : "" };
    }
  });
  if (!best) return null;
  best.dateLabel = best.date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  best.stops = rows.length;
  return best;
}

/* ---------- Init ---------- */
renderWelcome();
renderTeams();
renderMap();
paintBudget();
updateSummary();
setDefaultCountdown();

/* ============================================================
   FLIGHT PANEL  ·  click a host-city pin -> side drawer
   Client-only. API contract unchanged.
   ============================================================ */
const CITY_INFO = {
  "Vancouver":      { iata: "YVR", stadium: "BC Place" },
  "Seattle":        { iata: "SEA", stadium: "Lumen Field" },
  "San Francisco":  { iata: "SFO", stadium: "Levi's Stadium" },
  "Los Angeles":    { iata: "LAX", stadium: "SoFi Stadium" },
  "Kansas City":    { iata: "MCI", stadium: "Arrowhead Stadium" },
  "Dallas":         { iata: "DFW", stadium: "AT&T Stadium" },
  "Houston":        { iata: "IAH", stadium: "NRG Stadium" },
  "Atlanta":        { iata: "ATL", stadium: "Mercedes-Benz Stadium" },
  "Miami":          { iata: "MIA", stadium: "Hard Rock Stadium" },
  "Toronto":        { iata: "YYZ", stadium: "BMO Field" },
  "Boston":         { iata: "BOS", stadium: "Gillette Stadium" },
  "New York / NJ":  { iata: "EWR", stadium: "MetLife Stadium" },
  "Philadelphia":   { iata: "PHL", stadium: "Lincoln Financial Field" },
  "Monterrey":      { iata: "MTY", stadium: "Estadio BBVA" },
  "Guadalajara":    { iata: "GDL", stadium: "Estadio Akron" },
  "Mexico City":    { iata: "MEX", stadium: "Estadio Azteca" },
};
const COUNTRY_NAME = { us: "United States", ca: "Canada", mx: "Mexico" };

/* a few common departure airports so we can show distance + est. time */
const ORIGIN_COORDS = [
  [["heathrow", "london"], 51.47, -0.4543, "LHR"],
  [["gatwick"], 51.15, -0.18, "LGW"],
  [["changi", "singapore"], 1.3644, 103.9915, "SIN"],
  [["jfk", "new york"], 40.64, -73.78, "JFK"],
  [["los angeles", "lax"], 33.94, -118.40, "LAX"],
  [["dubai"], 25.25, 55.36, "DXB"],
  [["doha"], 25.27, 51.61, "DOH"],
  [["haneda", "tokyo"], 35.55, 139.78, "HND"],
  [["sydney"], -33.95, 151.18, "SYD"],
  [["paris", "charles de gaulle", "cdg"], 49.01, 2.55, "CDG"],
  [["frankfurt"], 50.03, 8.56, "FRA"],
  [["madrid"], 40.47, -3.56, "MAD"],
  [["amsterdam", "schiphol"], 52.31, 4.76, "AMS"],
];
function originGuess(dep) {
  const d = (dep || "").toLowerCase();
  for (const [keys, lat, lng, code] of ORIGIN_COORDS) if (keys.some((k) => d.includes(k))) return { lat, lng, code };
  return null;
}
function haversineKm(aLat, aLng, bLat, bLng) {
  const R = 6371, t = Math.PI / 180;
  const dLa = (bLat - aLat) * t, dLo = (bLng - aLng) * t;
  const x = Math.sin(dLa / 2) ** 2 + Math.cos(aLat * t) * Math.cos(bLat * t) * Math.sin(dLo / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(x)));
}
function estDuration(km) {
  const hrs = km / 820 + 0.5;               // cruise speed + taxi/climb buffer
  const h = Math.floor(hrs), m = Math.round((hrs - h) * 60);
  return `${h}h ${String(m).padStart(2, "0")}m`;
}

const fpOverlay = $("fp-overlay"), flightPanel = $("flightpanel"), fpBody = $("fp-body"),
      fpCity = $("fp-city"), fpSub = $("fp-sub"), fpClose = $("fp-close");
let fpLastFocus = null;

function openFlightPanel(cityName) {
  const city = HOST_CITIES.find(([n]) => n === cityName);
  if (!city || !flightPanel) return;
  const [name, cc, lng, lat] = city;
  const info = CITY_INFO[name] || { iata: "", stadium: "" };
  const dep = (departureEl.value || "London Heathrow").trim();
  const org = originGuess(dep);

  fpCity.textContent = name;
  fpSub.textContent = `${COUNTRY_NAME[cc] || ""} · Host venue: ${info.stadium || "TBC"}`;

  let rows = "";
  if (org) {
    const km = haversineKm(org.lat, org.lng, lat, lng);
    rows += `<div class="row"><span class="k">Great-circle distance</span><span class="v">${km.toLocaleString()} km</span></div>`;
    rows += `<div class="row"><span class="k">Est. nonstop time</span><span class="v">${estDuration(km)}</span></div>`;
  }
  rows += `<div class="row"><span class="k">Destination airport</span><span class="v">${info.iata || "TBC"}</span></div>`;
  rows += `<div class="row"><span class="k">Stadium</span><span class="v">${info.stadium || "TBC"}</span></div>`;

  const gf = `https://www.google.com/travel/flights?q=${encodeURIComponent(`Flights from ${dep} to ${name} ${info.iata}`)}`;
  const planMsg = `I want to plan a World Cup 2026 trip to ${name} (${info.stadium}). I am flying from ${dep}.`;

  fpBody.innerHTML = `
    <div class="fp-route">
      <div class="node"><div class="code">${org ? org.code : "YOU"}</div><div class="place">${dep}</div></div>
      <div class="arrow" aria-hidden="true"><svg width="34" height="14" viewBox="0 0 34 14" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M0 7h31M25 2l6 5-6 5"/></svg></div>
      <div class="node" style="text-align:right"><div class="code">${info.iata || "•"}</div><div class="place">${name}</div></div>
    </div>
    <div class="fp-meta">${rows}</div>
    <div class="fp-actions">
      <a class="fp-btn primary" href="${gf}" target="_blank" rel="noopener noreferrer">Search flights on Google Flights &rarr;</a>
      <button class="fp-btn ghost" id="fp-plan" type="button">Plan my trip to ${name}</button>
    </div>
    <p class="fp-note">${org
      ? "Distance and time are great-circle estimates for a nonstop flight."
      : "Add your departure airport in &ldquo;Flying from&rdquo; to see distance and flight-time estimates."}</p>`;

  const planEl = $("fp-plan");
  if (planEl) planEl.addEventListener("click", () => {
    input.value = planMsg;
    closeFlightPanel();
    input.focus();
  });

  fpLastFocus = document.activeElement;
  fpOverlay.hidden = false;
  requestAnimationFrame(() => { fpOverlay.classList.add("open"); flightPanel.classList.add("open"); });
  flightPanel.setAttribute("aria-hidden", "false");
  fpClose.focus();
}
function closeFlightPanel() {
  if (!flightPanel) return;
  fpOverlay.classList.remove("open");
  flightPanel.classList.remove("open");
  flightPanel.setAttribute("aria-hidden", "true");
  setTimeout(() => { fpOverlay.hidden = true; }, 340);
  if (fpLastFocus && fpLastFocus.focus) fpLastFocus.focus();
}

const mapHost = $("map");
if (mapHost) mapHost.addEventListener("click", (e) => {
  const pin = e.target.closest && e.target.closest(".pin");
  if (!pin) return;
  const name = pin.getAttribute("data-city");
  if (name) openFlightPanel(name);
});
if (fpClose) fpClose.addEventListener("click", closeFlightPanel);
if (fpOverlay) fpOverlay.addEventListener("click", closeFlightPanel);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && flightPanel && flightPanel.classList.contains("open")) closeFlightPanel();
});
