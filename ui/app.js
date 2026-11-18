"use strict";

const byId = (id) => document.getElementById(id);
let base = "";
const trip = byId("trip");
const predict = byId("predict");
const connect = byId("connect");
const map = byId("map");
const address = byId("server");

function status(message, error = false) {
  byId("status").textContent = message;
  byId("status").classList.toggle("error", error);
}

function clearResult() {
  byId("metrics").hidden = true;
  map.hidden = true;
  map.removeAttribute("srcdoc");
  byId("empty").hidden = false;
}

async function request(path, method = "GET") {
  const response = await fetch(base + path, { method, signal: AbortSignal.timeout(120000) });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "API returned HTTP " + response.status);
  }
  return response.json();
}

connect.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = connect.querySelector("button");
  button.disabled = true;
  trip.disabled = predict.disabled = true;
  clearResult();
  status("Loading evaluator trips...");
  try {
    const url = new URL(address.value);
    if (!["http:", "https:"].includes(url.protocol)) throw new Error("Use an HTTP or HTTPS address.");
    base = url.origin;
    const payload = await request("/trips");
    trip.replaceChildren(...payload.trips.map((id) => new Option(id, id)));
    if (!payload.trips.length) throw new Error("The API returned no trips.");
    trip.disabled = predict.disabled = false;
    status(payload.trips.length + " trips available.");
  } catch (error) {
    trip.replaceChildren(new Option("Connect to load trips", ""));
    status(error.message, true);
  } finally {
    button.disabled = false;
  }
});

byId("run").addEventListener("submit", async (event) => {
  event.preventDefault();
  const selected = trip.value;
  const button = connect.querySelector("button");
  trip.disabled = predict.disabled = button.disabled = true;
  clearResult();
  status("Reconstructing trip " + selected + "...");
  try {
    const result = await request("/trips/" + encodeURIComponent(selected) + "/prediction", "POST");
    map.srcdoc = result.map_html;
    map.hidden = false;
    byId("empty").hidden = true;
    const metrics = result.metrics;
    if (metrics) {
      for (const key of ["top1", "continuity", "sequence_f1", "candidate_miss"]) {
        byId(key).textContent = metrics[key] == null ? "Unavailable" : (metrics[key] * 100).toFixed(1) + "%";
      }
      byId("alignment").textContent = metrics.aligned_observations + " / " + metrics.observations;
      byId("metrics").hidden = false;
    }
    const matched = result.observation_arcs.filter((arc) => arc !== null).length;
    status(matched + " observations matched across " + result.route_legs.length + " route legs." +
           (metrics ? "" : " Evaluation results unavailable."));
  } catch (error) {
    status(error.message, true);
  } finally {
    trip.disabled = predict.disabled = button.disabled = false;
  }
});
