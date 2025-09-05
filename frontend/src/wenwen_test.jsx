import React, { useState } from "react";

export default function BTOEstimators() {
  const [costOutput, setCostOutput] = useState("");
  const [budgetOutput, setBudgetOutput] = useState("");

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

  const handleBudgetEstimator = (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const income = form.get("income");
    const cash = form.get("cash");
    const cpf = form.get("cpf");
    const cost = form.get("cost");

    // Mocked output for now
    setBudgetOutput(`I'll help you estimate your HDB loan and check the affordability for your BTO purchase with the provided information.\n\nTool #1: estimate_hdb_loan_with_budget\nBased on the results, here's your financial situation:\n\n1. Maximum HDB Loan: $569,366.42\n2. Total Budget Available: $5,719,366.42 (This includes CPF savings of $${cpf}, cash savings of $${cash}, and maximum loan amount)\n3. Affordability Status: AFFORDABLE\n\nThe BTO flat you're interested in costs $${cost}, which is well within your means. With a household income of $${income}, you qualify for a significant HDB loan.`);
  };

  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* BTO Cost Estimator */}
      <div className="p-4 border rounded-2xl shadow-md">
        <h2 className="text-xl font-bold mb-4">BTO Cost Estimator</h2>
        <form onSubmit={handleCostEstimator} className="space-y-3">
          <input name="location" placeholder="Project Location/Town" className="w-full p-2 border rounded" required />
          <input name="flatType" placeholder="Flat Type" className="w-full p-2 border rounded" required />
          <input name="projectName" placeholder="Project Name (optional)" className="w-full p-2 border rounded" />
          <input type="date" name="exerciseDate" className="w-full p-2 border rounded" />
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-xl">Estimate Cost</button>
        </form>
        <textarea
          value={costOutput}
          readOnly
          className="mt-4 w-full h-48 p-2 border rounded bg-gray-50"
        />
      </div>

      {/* BTO Budget Estimator */}
      <div className="p-4 border rounded-2xl shadow-md">
        <h2 className="text-xl font-bold mb-4">BTO Budget Estimator</h2>
        <form onSubmit={handleBudgetEstimator} className="space-y-3">
          <input name="income" type="number" placeholder="Monthly Household Income" className="w-full p-2 border rounded" required />
          <input name="cash" type="number" placeholder="Cash Savings" className="w-full p-2 border rounded" required />
          <input name="cpf" type="number" placeholder="CPF Savings" className="w-full p-2 border rounded" required />
          <input name="cost" type="number" placeholder="BTO Cost" className="w-full p-2 border rounded" required />
          <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded-xl">Estimate Budget</button>
        </form>
        <textarea
          value={budgetOutput}
          readOnly
          className="mt-4 w-full h-48 p-2 border rounded bg-gray-50"
        />
      </div>
    </div>
  );
}
