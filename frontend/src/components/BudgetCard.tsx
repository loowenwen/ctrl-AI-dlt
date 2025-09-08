import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface BudgetResponse {
  max_hdb_loan: number;
  total_budget: number;
  cpf_used_in_budget: number;
  retained_oa: number;
  session_id?: string;
}

interface BudgetCardProps {
  onBudgetCalculated?: (budget: BudgetResponse) => void;
}

export default function BudgetCard({ onBudgetCalculated }: BudgetCardProps) {
  const [monthlyIncome, setMonthlyIncome] = useState("");
  const [cpfSavings, setCpfSavings] = useState("");
  const [cashSavings, setCashSavings] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [budget, setBudget] = useState<BudgetResponse | null>(null);

  async function calculateBudget() {
    if (!monthlyIncome || !cpfSavings || !cashSavings) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const res = await fetch("http://127.0.0.1:8000/budget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          household_income: parseFloat(monthlyIncome),
          cpf_savings: parseFloat(cpfSavings),
          cash_savings: parseFloat(cashSavings),
        }),
      });

      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      setBudget(data);
      onBudgetCalculated?.(data);
    } catch (e: any) {
      setError(e?.message || "Failed to calculate budget");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Budgeting</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="income">Monthly Household Income</Label>
            <Input
              id="income"
              type="number"
              placeholder="e.g. 6000"
              value={monthlyIncome}
              onChange={(e) => setMonthlyIncome(e.target.value)}
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="cpf">CPF OA Savings</Label>
            <Input
              id="cpf"
              type="number"
              placeholder="e.g. 40000"
              value={cpfSavings}
              onChange={(e) => setCpfSavings(e.target.value)}
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="cash">Cash Savings</Label>
            <Input
              id="cash"
              type="number"
              placeholder="e.g. 30000"
              value={cashSavings}
              onChange={(e) => setCashSavings(e.target.value)}
            />
          </div>

          <Button 
            onClick={calculateBudget}
            disabled={!monthlyIncome || !cpfSavings || !cashSavings || isLoading}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Calculate Budget
          </Button>
        </div>

        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}

        {budget && (
          <div className="space-y-2 pt-2 border-t">
            <p className="text-sm">
              Maximum HDB Loan: <span className="font-medium">${budget.max_hdb_loan.toLocaleString()}</span>
            </p>
            <p className="text-sm">
              CPF Used: <span className="font-medium">${budget.cpf_used_in_budget.toLocaleString()}</span>
            </p>
            <p className="text-sm">
              CPF OA Retained: <span className="font-medium">${budget.retained_oa.toLocaleString()}</span>
            </p>
            <p className="text-sm font-semibold">
              Total Budget: <span className="text-base">${budget.total_budget.toLocaleString()}</span>
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}