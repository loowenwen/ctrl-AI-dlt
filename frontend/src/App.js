import React, { useState } from "react";
import axios from "axios";

function App() {
  const [age, setAge] = useState("");
  const [income, setIncome] = useState("");
  const [familySize, setFamilySize] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post("http://127.0.0.1:8000/check_eligibility", {
        age: parseInt(age),
        income: parseFloat(income),
        family_size: parseInt(familySize),
      });
      setResult(response.data);
    } catch (err) {
      console.error(err);
      setResult({ message: "Error checking eligibility" });
    }
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial" }}>
      <h1>BTO Eligibility Checker</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Age: </label>
          <input value={age} onChange={(e) => setAge(e.target.value)} required />
        </div>
        <div>
          <label>Annual Income: </label>
          <input value={income} onChange={(e) => setIncome(e.target.value)} required />
        </div>
        <div>
          <label>Family Size: </label>
          <input value={familySize} onChange={(e) => setFamilySize(e.target.value)} required />
        </div>
        <button type="submit" style={{ marginTop: "1rem" }}>Check Eligibility</button>
      </form>
      {result && (
        <div style={{ marginTop: "1rem" }}>
          <strong>{result.message}</strong>
        </div>
      )}
    </div>
  );
}

export default App;
