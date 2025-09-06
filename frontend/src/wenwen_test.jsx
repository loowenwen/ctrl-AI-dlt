import React, { useState, useEffect, useMemo } from "react";
import axios from "axios";
// leaflet map rendering
import { MapContainer, TileLayer, Popup, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function BTOEstimators() {
  const [budgetOutput, setBudgetOutput] = useState("");
  const [isBudgetLoading, setIsBudgetLoading] = useState(false);
  const [affordabilityOutput, setAffordabilityOutput] = useState("Affordability check will use the agent soon.");
  const [btoListings, setBtoListings] = useState([]);
  const [isLoadingListings, setIsLoadingListings] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [savedByTown, setSavedByTown] = useState({});
  const [selectedFlatType, setSelectedFlatType] = useState("");
  const [selectedExerciseDate, setSelectedExerciseDate] = useState("October 2025");

  // Unique flat types from concatenated strings like "2-Room Flexi, 3-Room, 4-Room"
  const flatTypeOptions = useMemo(() => {
    const set = new Set();
    for (const item of btoListings || []) {
      const s = item.flatType || "";
      for (const t of s.split(",")) {
        const trimmed = t.trim();
        if (trimmed) set.add(trimmed);
      }
    }
    // Optional sort for nicer UX
    const order = ["Community Care Apartment", "2-Room Flexi", "3-Room", "4-Room", "5-Room", "3Gen"];
    return Array.from(set).sort((a, b) => {
      const ia = order.indexOf(a);
      const ib = order.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
  }, [btoListings]);

  const filteredListings = useMemo(() => {
    if (!selectedFlatType) return [];
    return (btoListings || []).filter((item) => {
      const s = item.flatType || "";
      return s.split(",").map((x) => x.trim()).includes(selectedFlatType);
    });
  }, [btoListings, selectedFlatType]);

  // Top half: only compute budget (loan + total)
  const handleBudgetEstimator = (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const income = parseFloat(form.get("income"));
    const cash = parseFloat(form.get("cash"));
    const cpf = parseFloat(form.get("cpf"));

    const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

    (async () => {
      try {
        setIsBudgetLoading(true);
        setBudgetOutput("Calculating your maximum HDB loan and total budget...");

        // Compute total budget from backend
        const budgetResp = await axios.post(`${API_BASE}/budget`, {
          household_income: income,
          cash_savings: cash,
          cpf_savings: cpf,
          retain_oa_amount: 20000,
          // Use backend defaults for rate/tenure; include here if you want to expose UI controls
        });

        const { max_hdb_loan, total_budget, cpf_used_in_budget, retained_oa } = budgetResp.data || {};

        setBudgetOutput(
          [
            "Here is your computed BTO budget based on income and savings:",
            "",
            `1. Maximum HDB Loan: $${max_hdb_loan?.toLocaleString?.() ?? max_hdb_loan}`,
            `2. CPF used (after retaining $${(retained_oa ?? 20000).toLocaleString?.() ?? retained_oa ?? 20000}): $${cpf_used_in_budget?.toLocaleString?.() ?? Math.max(cpf - 20000, 0).toLocaleString()}`,
            `3. Total Budget Available: $${total_budget?.toLocaleString?.() ?? total_budget} (Cash $${cash.toLocaleString()} + CPF used + Max Loan)`,
            "",
            "Next step: Use the Affordability section below to check a specific BTO price (coming soon).",
          ].join("\n")
        );
      } catch (err) {
        const message = err?.response?.data?.detail || err?.message || String(err);
        setBudgetOutput(`Error: ${message}`);
      } finally {
        setIsBudgetLoading(false);
      }
    })();
  };

  // Second half: affordability placeholder (not integrated yet)
  const handleAffordability = (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const price = parseFloat(form.get("price"));
    setAffordabilityOutput(
      [
        `You entered target BTO price: $${price?.toLocaleString?.() ?? price}.`,
        "",
        "Affordability check will use the dedicated agent soon.",
        "We will compare your computed total budget against the entered price and show shortfall or 'Affordable'.",
      ].join("\n")
    );
  };

  const loadBtoListings = async () => {
    const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
    try {
      setIsLoadingListings(true);
      const resp = await axios.get(`${API_BASE}/bto_listings`);
      setBtoListings(resp.data || []);
    } catch (err) {
      console.error("Failed to load BTO listings", err);
      setBtoListings([]);
      alert(`Failed to load BTO listings: ${err?.response?.data?.detail || err?.message || err}`);
    } finally {
      setIsLoadingListings(false);
    }
  };

  useEffect(() => {
    // Auto-load listings on mount so map/checklist can render
    loadBtoListings();
  }, []);

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedByTown = useMemo(() => {
    const map = {};
    for (const item of btoListings) {
      const id = item.projectId || `${item.town}-${item.lat}-${item.lng}`;
      if (!selectedIds.has(id)) continue;
      const key = item.town || "Unknown";
      const minimal = {
        projectId: item.projectId,
        flatType: item.flatType,
        lat: item.lat,
        lng: item.lng,
        region: item.region,
        stage: item.stage,
        ballotQtr: item.ballotQtr,
      };
      if (!map[key]) map[key] = [];
      map[key].push(minimal);
    }
    return map;
  }, [btoListings, selectedIds]);

  const saveSelection = () => {
    setSavedByTown(selectedByTown);
    try {
      localStorage.setItem("selected_btos_by_town", JSON.stringify(selectedByTown));
    } catch (_) {}
  };

  const mapCenter = useMemo(() => {
    if (btoListings && btoListings.length > 0) {
      return [btoListings[0].lat || 1.3521, btoListings[0].lng || 103.8198];
    }
    return [1.3521, 103.8198]; // Singapore
  }, [btoListings]);

  return (
    <>
      {/* Full-width map hero at the top */}
      <div className="map-hero">
        <MapContainer center={mapCenter} zoom={11} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {btoListings.map((bto) => {
            const id = bto.projectId || `${bto.town}-${bto.lat}-${bto.lng}`;
            const isSelected = selectedIds.has(id);
            const color = isSelected ? "#d9534f" : "#1e90ff";
            return (
              <CircleMarker key={id} center={[bto.lat, bto.lng]} pathOptions={{ color }} radius={8}>
                <Popup>
                  <div style={{ minWidth: 180 }}>
                    <div style={{ fontWeight: 600 }}>{bto.town}</div>
                    <div>{bto.flatType}</div>
                    <div style={{ color: "#666", fontSize: "0.9em" }}>
                      {bto.region || "Region"} • {bto.stage || "Stage"}
                    </div>
                    <div style={{ marginTop: 6 }}>
                      <button className="button" onClick={() => toggleSelect(id)}>
                        {isSelected ? "Unselect" : "Select"}
                      </button>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      {/* Rest of the UI in a centered container */}
      <div className="container">
        <section className="grid">
        {/* BTO Cost Estimator */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" aria-hidden>💰</div>
            <div>
              <h2 className="card-title">BTO Cost Estimator</h2>
              <p className="card-subtitle">Pick a flat type, date, then select BTOs</p>
            </div>
          </div>
          <div className="form">
            <div className="input-row">
              <div className="input-group">
                <label className="label" htmlFor="flatType">Flat Type</label>
                <select
                  id="flatType"
                  className="input"
                  value={selectedFlatType}
                  onChange={(e) => setSelectedFlatType(e.target.value)}
                >
                  <option value="">Select a flat type</option>
                  {flatTypeOptions.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="label" htmlFor="exerciseDate">Exercise Date</label>
                <select
                  id="exerciseDate"
                  className="input"
                  value={selectedExerciseDate}
                  onChange={(e) => setSelectedExerciseDate(e.target.value)}
                >
                  <option value="October 2025">October 2025</option>
                </select>
              </div>
            </div>
          </div>

          {/* Checklist to select BTOs and save by town */}
          <div className="divider" />
          <h3 className="section-title">Select BTOs (filtered by flat type)</h3>
          <div className="actions">
            <button className="button" onClick={loadBtoListings} disabled={isLoadingListings}>
              {isLoadingListings ? "Loading..." : "Refresh BTO Listings"}
            </button>
          </div>
          <div className="output" style={{ maxHeight: 220, overflow: "auto" }}>
            {!selectedFlatType ? (
              <div>Please select a flat type to see matching BTOs.</div>
            ) : filteredListings.length === 0 ? (
              <div>No BTOs available for "{selectedFlatType}".</div>
            ) : (
              <ul style={{ listStyle: "none", paddingLeft: 0 }}>
                {filteredListings.map((bto) => {
                  const id = bto.projectId || `${bto.town}-${bto.lat}-${bto.lng}`;
                  return (
                    <li key={id} style={{ marginBottom: 6 }}>
                      <label>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(id)}
                          onChange={() => toggleSelect(id)}
                          style={{ marginRight: 8 }}
                        />
                        <strong>{bto.town}</strong> — {bto.flatType}
                        <span style={{ color: "#666", marginLeft: 8 }}>
                          ({bto.region || "Region"}, {bto.stage || "Stage"})
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
          <div className="actions">
            <button className="button success" onClick={saveSelection}>Save Selection</button>
          </div>
          <pre className="output" aria-live="polite">{Object.keys(savedByTown).length ? JSON.stringify(savedByTown, null, 2) : "Saved selection (dictionary) will appear here."}</pre>
        </div>

        {/* BTO Budget Estimator - split into two */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" aria-hidden>📊</div>
            <div>
              <h2 className="card-title">BTO Budget Estimator</h2>
              <p className="card-subtitle">Top: Budget. Bottom: Affordability (coming soon)</p>
            </div>
          </div>

          {/* Top half: Budget */}
          <h3 className="section-title">1) Budget (Income + Savings)</h3>
          <form onSubmit={handleBudgetEstimator} className="form">
            <div className="input-row">
              <div className="input-group">
                <label className="label" htmlFor="income">Monthly Household Income</label>
                <input id="income" name="income" type="number" inputMode="decimal" placeholder="e.g., 8500" className="input" required />
              </div>
              <div className="input-group">
                <label className="label" htmlFor="cash">Cash Savings</label>
                <input id="cash" name="cash" type="number" inputMode="decimal" placeholder="e.g., 40000" className="input" required />
              </div>
            </div>
            <div className="input-row">
              <div className="input-group">
                <label className="label" htmlFor="cpf">CPF OA Savings</label>
                <input id="cpf" name="cpf" type="number" inputMode="decimal" placeholder="e.g., 70000" className="input" required />
                <p className="help">Recommendation: retain at least $20,000 in your CPF OA. We will exclude $20,000 by default.</p>
              </div>
            </div>
            <div className="actions">
              <button type="submit" className="button success" disabled={isBudgetLoading}>
                {isBudgetLoading ? <span className="spinner" aria-hidden /> : null}
                {isBudgetLoading ? "Calculating..." : "Compute Budget"}
              </button>
            </div>
          </form>
          <pre className={`output ${isBudgetLoading ? "loading" : ""}`} aria-live="polite">{budgetOutput || "Your maximum loan and total budget will show here."}</pre>

          <div className="divider" />

          {/* Bottom half: Affordability (placeholder) */}
          <h3 className="section-title">2) Affordability (coming soon)</h3>
          <form onSubmit={handleAffordability} className="form">
            <div className="input-row">
              <div className="input-group">
                <label className="label" htmlFor="price">Target BTO Price</label>
                <input id="price" name="price" type="number" inputMode="decimal" placeholder="e.g., 520000" className="input" required />
              </div>
            </div>
            <div className="actions">
              <button type="submit" className="button primary">Preview Affordability</button>
            </div>
          </form>
          <pre className="output" aria-live="polite">{affordabilityOutput}</pre>
        </div>

        {/* Map card removed — now a full-width hero above */}
        </section>
      </div>
    </>
  );
}
