const F = [
  ["rainfall_mm", "Rainfall", "mm", "cloud-rain", 180, 0, 800],
  ["river_level_m", "River Level", "m", "waves", 3.5, 0, 30],
  ["elevation_m", "Elevation", "m", "mountain", 100, 0, 9000],
  ["soil_moisture_percent", "Soil Moisture", "%", "sprout", 85, 0, 100],
  ["temperature_c", "Temperature", "°C", "thermometer", 24, -30, 60],
  ["humidity_percent", "Humidity", "%", "droplets", 90, 0, 100],
  ["drainage_capacity_percent", "Drainage Capacity", "%", "pipette", 30, 0, 100],
];
const $ = (s) => document.querySelector(s);
const CIRC = 439.8;
let charts = [];

// ---------- helpers ----------
function toast(msg, type = "") {
  const t = document.createElement("div");
  t.className = "toast " + type;
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
function icons() { window.lucide && lucide.createIcons(); }
function toggleTheme() {
  document.body.classList.toggle("light");
  localStorage.setItem("fs-theme", document.body.classList.contains("light") ? "light" : "dark");
  loadStatus();
}
function openModal() { $("#modal").classList.add("open"); $("#up").hidden = true; $("#uerr").hidden = true; }
function closeModal() { $("#modal").classList.remove("open"); }
function animateNumber(el, to, ms = 1100) {
  const t0 = performance.now();
  (function step(t) {
    const k = Math.min((t - t0) / ms, 1);
    el.textContent = (to * (1 - Math.pow(1 - k, 3))).toFixed(1) + "%";
    if (k < 1) requestAnimationFrame(step);
  })(t0);
}

// ---------- sidebar ----------
const drawer = (open) => {
  $("#side").classList.toggle("open", open);
  document.body.classList.toggle("drawer", open);
};
$("#menuBtn").onclick = () => drawer(true);
$("#overlay").onclick = () => drawer(false);
document.querySelectorAll("#nav a").forEach((a) => (a.onclick = () => drawer(false)));
const spy = new IntersectionObserver((es) => es.forEach((e) => {
  if (e.isIntersecting) document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id));
}), { rootMargin: "-40% 0px -55% 0px" });
document.querySelectorAll("section[id]").forEach((s) => spy.observe(s));

// ---------- inputs ----------
$("#fields").innerHTML = F.map(([k, l, u, ic, ex]) => `
  <div class="field" id="f_${k}"><label for="${k}">${l}</label>
    <div class="inp"><i data-lucide="${ic}"></i><input type="number" step="any" id="${k}" value="${ex}"><span>${u}</span></div>
    <div class="err">Please enter a valid ${l.toLowerCase()} value.</div></div>`).join("");
F.forEach(([k]) => ($("#" + k).oninput = () => $("#f_" + k).classList.remove("bad")));

function validate() {
  let ok = true;
  const body = {};
  F.forEach(([k, , , , , min, max]) => {
    const raw = $("#" + k).value.trim(), v = Number(raw);
    const bad = raw === "" || !isFinite(v) || v < min || v > max;
    $("#f_" + k).classList.toggle("bad", bad);
    if (bad) ok = false; else body[k] = v;
  });
  return ok ? body : null;
}

// ---------- prediction ----------
async function runPredict() {
  const body = validate();
  if (!body) return toast("Please correct the highlighted fields.", "err");
  const btn = $("#runBtn"), res = $("#result");
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>Analyzing environmental conditions...';
  res.className = "card result busy";
  $("#rBadge").textContent = "ANALYZING";
  $("#rMsg").innerHTML = "<b>Analyzing environmental conditions...</b><br>Running Logistic Regression.";
  $("#prog").style.strokeDashoffset = CIRC;
  try {
    const [r] = await Promise.all([
      fetch("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
      new Promise((ok) => setTimeout(ok, 900)),
    ]);
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "Prediction failed");
    const high = d.prediction === 1;
    res.className = "card result " + (high ? "high" : "low");
    $("#rBadge").textContent = (high ? "🔴 " : "🟢 ") + d.label;
    $("#rMsg").innerHTML = `<b>${d.message}</b><br>Risk probability: ${d.probability}%`;
    $("#prog").style.strokeDashoffset = CIRC * (1 - d.probability / 100);
    animateNumber($("#rPct"), d.probability);
    toast("Prediction completed", "ok");
  } catch (e) {
    res.className = "card result wait";
    $("#rBadge").textContent = "ERROR";
    $("#rMsg").innerHTML = "<b>Something went wrong</b><br>" + e.message;
    toast(e.message, "err");
  }
  btn.disabled = false;
  btn.textContent = "Run AI Prediction →";
}

// ---------- status / charts ----------
async function loadStatus() {
  try {
    const d = await (await fetch("/api/status")).json();
    $("#sAcc").textContent = d.accuracy + "%";
    $("#sRows").textContent = d.rows;
    $("#sFeat").textContent = d.features;
    $("#sStat").textContent = d.status;
    $("#dName").textContent = d.filename;
    $("#dRows").textContent = d.rows;
    $("#dCols").textContent = d.columns;
    const [[tn, fp], [fn, tp]] = d.confusion;
    Object.entries({ tn, fp, fn, tp }).forEach(([k, v]) => ($("#" + k).textContent = v));
    drawCharts(d);
  } catch (e) {
    $("#sStat").textContent = "Offline";
    toast("Cannot reach the backend. Is app.py running?", "err");
  }
}
function drawCharts(d) {
  charts.forEach((c) => c.destroy());
  const txt = getComputedStyle(document.body).getPropertyValue("--m").trim();
  Chart.defaults.color = txt;
  Chart.defaults.font.family = "Inter";
  const opt = { responsive: true, maintainAspectRatio: false };
  charts = [
    new Chart($("#c1"), { type: "doughnut", data: { labels: ["Correct", "Errors"], datasets: [{ data: [d.accuracy, +(100 - d.accuracy).toFixed(1)], backgroundColor: ["#6366F1", "rgba(142,153,173,.2)"], borderWidth: 0 }] },
      options: { ...opt, cutout: "78%", plugins: { legend: { position: "bottom" } } },
      plugins: [{ id: "t", afterDraw(c) { const { ctx, chartArea: a } = c; ctx.save(); ctx.font = "800 26px Inter"; ctx.fillStyle = getComputedStyle(document.body).getPropertyValue("--t"); ctx.textAlign = "center"; ctx.fillText(d.accuracy + "%", (a.left + a.right) / 2, (a.top + a.bottom) / 2 + 9); ctx.restore(); } }] }),
    new Chart($("#c2"), { type: "doughnut", data: { labels: ["Low Risk", "Flood Risk"], datasets: [{ data: d.distribution, backgroundColor: ["#10B981", "#EF4444"], borderWidth: 0 }] },
      options: { ...opt, cutout: "62%", plugins: { legend: { position: "bottom" } } } }),
    new Chart($("#c3"), { type: "bar", data: { labels: d.importance.map((i) => i.feature.replace(/_(mm|m|percent|c)$/, "").replace(/_/g, " ")), datasets: [{ label: "Coefficient", data: d.importance.map((i) => i.value), backgroundColor: d.importance.map((i) => (i.value >= 0 ? "#8B5CF6" : "#10B981")), borderRadius: 6 }] },
      options: { ...opt, indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { grid: { color: "rgba(142,153,173,.12)" } }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } } } }),
  ];
}
async function loadPreview() {
  try {
    const d = await (await fetch("/api/preview")).json();
    $("#preview").innerHTML = "<table><tr>" + d.columns.map((c) => `<th>${c}</th>`).join("") + "</tr>" +
      d.rows.map((r) => "<tr>" + r.map((v) => `<td>${v}</td>`).join("") + "</tr>").join("") + "</table>";
  } catch (e) {
    $("#preview").innerHTML = '<p class="sub">No dataset uploaded. Upload your CSV dataset to train the Logistic Regression model.</p>';
  }
}

// ---------- upload ----------
const fileIn = $("#file"), drop = $("#drop");
fileIn.onchange = () => fileIn.files[0] && upload(fileIn.files[0]);
["dragover", "dragenter"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));

async function upload(file) {
  const up = $("#up"), err = $("#uerr"), fill = $("#pfill"), txt = $("#ptxt");
  err.hidden = true; up.hidden = false; fill.style.width = "15%"; txt.textContent = "Uploading...";
  const steps = [["Processing...", "55%"], ["Training model...", "85%"]];
  steps.forEach(([t, w], i) => setTimeout(() => { if (!up.hidden && fill.style.width !== "100%") { txt.textContent = t; fill.style.width = w; } }, 600 * (i + 1)));
  const fd = new FormData(); fd.append("file", file);
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) {
      up.hidden = true; err.hidden = false;
      err.innerHTML = `<b>${d.error}</b>` + (d.missing ? "<br><br>Missing columns:<br>" + d.missing.join("<br>") : "");
      return toast(d.error, "err");
    }
    fill.style.width = "100%"; txt.textContent = "✓ Model retrained successfully";
    toast(`Model retrained · accuracy ${d.accuracy}%`, "ok");
    await Promise.all([loadStatus(), loadPreview()]);
    setTimeout(closeModal, 1400);
  } catch (e) { up.hidden = true; err.hidden = false; err.textContent = "Upload failed. Check that the server is running."; }
  fileIn.value = "";
}

// ---------- init ----------
if (localStorage.getItem("fs-theme") === "light") document.body.classList.add("light");
$("#modal").onclick = (e) => e.target.id === "modal" && closeModal();
document.addEventListener("keydown", (e) => e.key === "Escape" && closeModal());
$("#prog").style.strokeDashoffset = CIRC;
icons(); loadStatus(); loadPreview();
