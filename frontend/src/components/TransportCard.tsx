import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function TransportCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Transportation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>Nearest MRT: —</p>
        <p>Walk time: —</p>
        <p>Bus options: —</p>
        <p className="text-xs text-muted-foreground">
          Placeholder content for transport insights.
        </p>
      </CardContent>
    </Card>
  )
}