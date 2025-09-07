import { useLocation } from "react-router-dom";
import BudgetCard from "./BudgetCard";
import TransportCard from "./TransportCard";
import SentimentReport from "@/components/SentimentReport";

export default function Results() {
  const location = useLocation();
  const incomingPayload = (location.state as any)?.payload;
  const text: string | undefined = incomingPayload?.text;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-6xl">
        <h1 className="mb-4 text-2xl md:text-3xl font-bold">Analysis Results</h1>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT: Sentiment report */}
          <div className="lg:col-span-8 space-y-6">
            <SentimentReport initialText={text} />
          </div>

          {/* RIGHT: Budget + Transport */}
          <aside className="lg:col-span-4 space-y-6 mt-9">
            <BudgetCard />
            <TransportCard />
          </aside>
        </div>
      </div>
    </div>
  );
}