import React from "react";
import BTOEstimators from "./wenwen_test";
import "./App.css";

function App() {
  return (
    <div className="page">
      <header className="header">
        <h1 className="page-title">BTO Tools</h1>
        <p className="page-subtitle">Estimate price, budget, and affordability</p>
      </header>
      <main>
        <BTOEstimators />
      </main>
    </div>
  );
}

export default App;
