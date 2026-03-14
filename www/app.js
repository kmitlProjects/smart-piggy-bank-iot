const API_URL = "http://YOUR_ESP32_IP/status";

async function loadStatus() {
  const statusEl = document.getElementById("status");
  try {
    const res = await fetch(API_URL);
    if (!res.ok) throw new Error("HTTP " + res.status);

    const data = await res.json();
    statusEl.textContent = "Connected";

    document.getElementById("c1").textContent = data.coins?.["1"] ?? 0;
    document.getElementById("c2").textContent = data.coins?.["2"] ?? 0;
    document.getElementById("c5").textContent = data.coins?.["5"] ?? 0;
    document.getElementById("c10").textContent = data.coins?.["10"] ?? 0;
    document.getElementById("total").textContent = data.total ?? 0;
    document.getElementById("estTotal").textContent = data.estimated_total ?? "-";
    document.getElementById("estCoins").textContent = data.estimated_coin_count ?? "-";
    document.getElementById("fillPercent").textContent = data.fill_percent ?? "-";
    document.getElementById("distance").textContent = data.distance_cm ?? "-";
    document.getElementById("full").textContent = String(data.is_full ?? false);
    document.getElementById("locked").textContent = String(data.is_locked ?? true);
    document.getElementById("wifi").textContent = String(data.wifi_connected ?? false);
  } catch (err) {
    statusEl.textContent = "Disconnected: " + err.message;
  }
}

setInterval(loadStatus, 2000);
loadStatus();
