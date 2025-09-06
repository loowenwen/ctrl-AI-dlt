import React, { useState } from "react";
import axios from "axios";

export default function BTOEstimators() {
  const [costOutput, setCostOutput] = useState("");
  const [budgetOutput, setBudgetOutput] = useState("");
  const [isBudgetLoading, setIsBudgetLoading] = useState(false);
  const [affordabilityOutput, setAffordabilityOutput] = useState("Affordability check will use the agent soon.");

  const handleCostEstimator = (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const location = form.get("location");
    const flatType = form.get("flatType");
    const projectName = form.get("projectName") || "N/A";
    const exerciseDate = form.get("exerciseDate") || "2025-10-01";

    // Mocked output for now
    setCostOutput(`Location: ${location}\nFlat Type: ${flatType}\nProject Tier: Prime\nExercise Date: ${exerciseDate}\nSample Size: 15\nEstimated Price: $674,283\n95% Confidence Interval: $632,786 - $715,780\nHistorical Trend: stable\nMethodology: linear_regression`);
  };

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

  return (
    <div className="container">
      <section className="grid">
        {/* BTO Cost Estimator */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" aria-hidden>💰</div>
            <div>
              <h2 className="card-title">BTO Cost Estimator</h2>
              <p className="card-subtitle">Quick price estimate by project and type</p>
            </div>
          </div>
          <form onSubmit={handleCostEstimator} className="form">
            <div className="input-group">
              <label className="label" htmlFor="location">Project Location/Town</label>
              <input id="location" name="location" placeholder="e.g., Tampines" className="input" required />
            </div>
            <div className="input-group">
              <label className="label" htmlFor="flatType">Flat Type</label>
              <input id="flatType" name="flatType" placeholder="e.g., 4-room" className="input" required />
            </div>
            <div className="input-group">
              <label className="label" htmlFor="projectName">Project Name (optional)</label>
              <input id="projectName" name="projectName" placeholder="e.g., GreenSpring Residences" className="input" />
            </div>
            <div className="input-group">
              <label className="label" htmlFor="exerciseDate">Exercise Date</label>
              <input id="exerciseDate" type="date" name="exerciseDate" className="input" />
            </div>
            <div className="actions">
              <button type="submit" className="button primary">Estimate Cost</button>
            </div>
          </form>
          <pre className="output" aria-live="polite">{costOutput || "Results will appear here."}</pre>
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
      </section>
    </div>
  );
}
