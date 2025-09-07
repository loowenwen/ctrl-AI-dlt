import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function BudgetCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Budgeting</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>Monthly income: —</p>
        <p>CPF savings: —</p>
        <p>Cash savings: —</p>
        <p className="font-semibold">Estimated budget: —</p>
        <p className="text-xs text-muted-foreground">
          Placeholder content for your budgeting helper.
        </p>
      </CardContent>
    </Card>
  )
}