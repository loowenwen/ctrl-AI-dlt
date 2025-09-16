import { useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import SentimentReport from "@/components/SentimentReport";
import AffordabilityCard from "./AffordabilityCard";
import TransportCard from "./TransportCard";
import { Loader2 } from "lucide-react";

export default function Results() {
  const location = useLocation();
  const incomingPayload = (location.state as any)?.payload;
  const formData = (location.state as any)?.formData;
  const text: string | undefined = incomingPayload?.text;
  
  // State for API results and loading
  const [budgetResult, setBudgetResult] = useState<any>(null);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetError, setBudgetError] = useState<string | null>(null);

  // Call agents when component mounts
  useEffect(() => {
    if (formData?.budget) {
      setBudgetLoading(true);
      fetch("http://127.0.0.1:8000/budget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          household_income: formData.budget.monthlyIncome,
          cpf_savings: formData.budget.cpfSavings,
          cash_savings: formData.budget.cashSavings,
        }),
      })
      .then(res => res.json())
      .then(data => {
        console.log("Budget API response:", data);
        setBudgetResult(data);
        setBudgetLoading(false);
      })
      .catch(error => {
        console.error("Budget API error:", error);
        setBudgetError("Failed to calculate budget");
        setBudgetLoading(false);
      });
    }


  }, [formData]);

    // Debug logging
  console.log("🔍 Results - formData:", formData);
  console.log("🔍 Results - budgetResult:", budgetResult);
  console.log("🔍 Results - budgetLoading:", budgetLoading);
  
  // Detailed transport data logging
  const transportAutoRun = formData?.transport ? {
    destinationPostal: formData.transport.destinationPostal,
    timePeriod: formData.transport.timePeriod
  } : undefined;
  console.log("🚚 Transport props:", {
    btoProject: formData?.transport?.btoProject,
    autoRun: transportAutoRun
  });
  
  // Detailed affordability data logging
  const affordabilityProps = {
    totalBudget: budgetResult?.total_budget,
    defaultBTO: formData?.transport?.btoProject && formData?.transport?.flatType ? {
      name: formData.transport.btoProject,
      flatType: formData.transport.flatType
    } : undefined
  };
  console.log("💰 Affordability props:", affordabilityProps);
  
  // Debug transport data
  console.log("Results - transport data for TransportCard:", {
    btoProject: (location.state as any)?.btoProject || "ALL BTOs (no specific project selected)",
    destinationPostal: formData?.transport?.destinationPostal,
    timePeriod: formData?.transport?.timePeriod,
    willAnalyzeAllBTOs: !(location.state as any)?.btoProject
  });
  
  // Debug affordability data
  console.log("Results - affordability data for AffordabilityCard:", {
    totalBudget: budgetResult?.total_budget,
    defaultBTO: (location.state as any)?.btoProject && (location.state as any)?.selectedFlatType ? {
      name: (location.state as any)?.btoProject,
      flatType: (location.state as any)?.selectedFlatType
    } : undefined
  });

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-7xl">
        <h1 className="mb-4 text-2xl md:text-3xl font-bold">Analysis Results</h1>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT: Sentiment report */}
          <div className="lg:col-span-8 space-y-6">
            <SentimentReport 
              initialText={text} 
              isAllBTOAnalysis={!(location.state as any)?.btoProject} // True when no specific BTO selected
              selectedFlatType={(location.state as any)?.selectedFlatType}
            />
          </div>

          {/* RIGHT: Pre-calculated Results */}
          <aside className="lg:col-span-4 space-y-6 mt-9.5">
            {/* Budget Results Display */}
            <div className="bg-white rounded-lg border p-4">
              <h3 className="font-semibold mb-4">Budget Analysis</h3>
              {budgetLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-gray-600">Calculating budget...</span>
                </div>
              ) : budgetError ? (
                <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">
                  {budgetError}
                </div>
              ) : budgetResult ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm font-medium text-green-700">Budget calculated successfully</span>
                  </div>
                  <p className="text-sm">
                    Maximum HDB Loan: <span className="font-medium">${budgetResult.max_hdb_loan?.toLocaleString()}</span>
                  </p>
                  <p className="text-sm">
                    CPF Used: <span className="font-medium">${budgetResult.cpf_used_in_budget?.toLocaleString()}</span>
                  </p>
                  <p className="text-sm">
                    CPF OA Retained: <span className="font-medium">${budgetResult.retained_oa?.toLocaleString()}</span>
                  </p>
                  <p className="text-sm font-semibold">
                    Total Budget: <span className="text-base">${budgetResult.total_budget?.toLocaleString()}</span>
                  </p>
                </div>
              ) : (
                <div className="text-sm text-gray-500">No budget data provided</div>
              )}
            </div>

            {/* Affordability Analysis - Runs after budget is available */}
            <AffordabilityCard 
              totalBudget={budgetResult?.total_budget}
              selectedFlatType={(location.state as any)?.selectedFlatType}
              defaultBTO={(location.state as any)?.btoProject && (location.state as any)?.selectedFlatType ? {
                name: (location.state as any)?.btoProject,
                flatType: (location.state as any)?.selectedFlatType
              } : undefined}
            />

            {/* Transport Card with Button */}
            <TransportCard 
              btoProject={(location.state as any)?.btoProject}
              autoRun={formData?.transport ? {
                destinationPostal: formData.transport.destinationPostal,
                timePeriod: formData.transport.timePeriod
              } : undefined}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}