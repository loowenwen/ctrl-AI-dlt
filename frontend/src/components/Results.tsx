import { useLocation } from "react-router-dom";
import { useState } from "react";
import BudgetCard from "./BudgetCard";
import TransportCard from "./TransportCard";
import SentimentReport from "@/components/SentimentReport";
import AffordabilityCard from "./AffordabilityCard";

interface BudgetData {
  max_hdb_loan: number;
  total_budget: number;
  cpf_used_in_budget: number;
  retained_oa: number;
  session_id?: string;
}

export default function Results() {
  const location = useLocation();
  const incomingPayload = (location.state as any)?.payload;
  const btoProject = (location.state as any)?.btoProject;
  const selectedFlatType = (location.state as any)?.selectedFlatType;
  const text: string | undefined = incomingPayload?.text;
  const [budgetData, setBudgetData] = useState<BudgetData | null>(null);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-7xl">
        <h1 className="mb-4 text-2xl md:text-3xl font-bold">Analysis Results</h1>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT: Sentiment report */}
          <div className="lg:col-span-8 space-y-6">
            <SentimentReport initialText={text} />
          </div>

          {/* RIGHT: Budget + Transport + Affordability */}
          <aside className="lg:col-span-4 space-y-6 mt-9.5">
            <BudgetCard onBudgetCalculated={setBudgetData} />
            <AffordabilityCard 
              totalBudget={budgetData?.total_budget}
              defaultBTO={btoProject ? {
                name: btoProject,
                flatType: selectedFlatType
              } : undefined}
            />
            <TransportCard btoProject={btoProject}/>
          </aside>
        </div>
      </div>
    </div>
  );
}