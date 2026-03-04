// DARYL Web UI - minimal (migrated from buralux/dsm)
function displayOutput(data, error) {
  var out = document.getElementById("out");
  if (error) {
    out.textContent = "❌ Erreur: " + error;
    out.style.color = "#e74c3c";
  } else if (data && data.error) {
    out.textContent = "⚠️ Erreur: " + data.error;
    out.style.color = "#e67e22";
  } else {
    out.textContent = JSON.stringify(data, null, 2);
    out.style.color = "#2ecc71";
  }
}
function setStatus(s) {
  var el = document.getElementById("status");
  if (el) el.textContent = s;
}
function displayResultsCards(results) {
  var c = document.getElementById("results-cards");
  if (!c) return;
  c.innerHTML = "";
  (results || []).forEach(function(r) {
    var card = document.createElement("div");
    card.className = "glass card-item p-4";
    card.innerHTML = "<div><strong>" + (r.shard_name || r.shard_id) + "</strong> " + ((r.score * 100) || 0).toFixed(1) + "%</div><div class=\"text-sm\">" + (r.content || "").substring(0, 100) + "...</div>";
    c.appendChild(card);
  });
}
function displayStatsCards(data) {
  var c = document.getElementById("results-cards");
  if (!c) return;
  c.innerHTML = "";
  if (data.shards && data.shards.length > 0) {
    data.shards.forEach(function(s) {
      var card = document.createElement("div");
      card.className = "glass p-4";
      card.innerHTML = "<div><strong>" + (s.shard_id || s.name) + "</strong> " + (s.transactions_count || s.transactions || 0) + " tx</div><div class=\"text-sm\">" + (s.name || "") + " (" + (s.domain || "") + ")</div>";
      c.appendChild(card);
    });
  }
}
async function doSearch(kind) {
  var q = document.getElementById("q").value.trim();
  var top_k = document.getElementById("top_k").value.trim() || "5";
  var min_score = document.getElementById("min_score").value.trim() || "0.0";
  if (!q) { setStatus("⚠️ Veuillez entrer une recherche"); return; }
  setStatus("loading…");
  try {
    var res = await fetch("/" + kind + "?q=" + encodeURIComponent(q) + "&top_k=" + encodeURIComponent(top_k) + "&min_score=" + encodeURIComponent(min_score));
    var data = await res.json();
    if (data.error) { setStatus("error"); displayOutput(data, data.error); return; }
    if (data.results && data.results.length > 0) displayResultsCards(data.results);
    setStatus("ready");
    displayOutput({ kind: kind, data: data });
  } catch (e) { setStatus("error"); displayOutput(null, e.message); }
}
async function loadStats() {
  setStatus("loading…");
  try {
    var res = await fetch("/stats");
    var data = await res.json();
    if (data.error) { setStatus("error"); displayOutput(data, data.error); return; }
    displayStatsCards(data);
    setStatus("ready");
    displayOutput({ kind: "stats", data: data });
  } catch (e) { setStatus("error"); displayOutput(null, e.message); }
}
async function loadShards() {
  setStatus("loading…");
  try {
    var res = await fetch("/shards");
    var data = await res.json();
    if (data.error) { setStatus("error"); displayOutput(data, data.error); return; }
    setStatus("ready");
    displayOutput({ kind: "shards", data: data });
  } catch (e) { setStatus("error"); displayOutput(null, e.message); }
}
async function compressMemory() {
  setStatus("loading…");
  try {
    var res = await fetch("/compress");
    var data = await res.json();
    setStatus("ready");
    displayOutput({ kind: "compress", data: data });
  } catch (e) { setStatus("error"); displayOutput(null, e.message); }
}
async function cleanupMemory() {
  setStatus("loading…");
  try {
    var res = await fetch("/cleanup");
    var data = await res.json();
    setStatus("ready");
    displayOutput({ kind: "cleanup", data: data });
  } catch (e) { setStatus("error"); displayOutput(null, e.message); }
}
document.addEventListener("DOMContentLoaded", function() {
  var input = document.getElementById("q");
  if (input) input.focus();
});
