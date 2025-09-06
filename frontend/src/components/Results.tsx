// src/pages/Results.tsx
import { useLocation, Link as RouterLink } from "react-router-dom"
import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

type ApiEnvelope = { body?: string } & Record<string, any>

function safeJsonParse<T = any>(v: unknown): T | null {
  try { return typeof v === "string" ? JSON.parse(v) : (v as T) }
  catch { return null }
}

export default function Results() {
  const location = useLocation()
  const raw = (location.state?.data ?? {}) as ApiEnvelope

  // 1) Try to parse `body` if present, else use raw
  const parsed = useMemo(() => {
    // Some backends return { body: "<json-string>" }
    const inner = raw?.body ? safeJsonParse(raw.body) : raw
    // Sometimes upstream libs wrap strings again; try one more time
    return typeof inner === "string" ? safeJsonParse(inner) : inner
  }, [raw])

  const input: string | undefined = parsed?.input ?? parsed?.request ?? undefined
  const output: string | undefined = parsed?.output ?? parsed?.result ?? parsed?.text ?? undefined
  const statusVal: string | undefined =
    parsed?.status?._value_ ?? parsed?.status ?? raw?.status ?? "completed"

  // Extract a numeric score if present, e.g., "Score: 0.6 ..."
  const scoreMatch = output?.match(/Score:\s*([+-]?[0-9]*\.?[0-9]+)/i);
  const score = scoreMatch ? Number(scoreMatch[1]) : undefined
  let sentimentBadge: string | undefined;

  if (score !== undefined) {
    if (score > 0.33) {
      sentimentBadge = "Positive";
    } else if (score < -0.33) {
      sentimentBadge = "Negative";
    } else {
      sentimentBadge = "Neutral";
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl md:text-3xl font-bold">Analysis Results</h1>
          <div className="flex items-center gap-2">
            {sentimentBadge && <Badge variant="secondary" className={sentimentBadge === "Positive" ? "bg-green-500" : "bg-red-500 text-white"}>{sentimentBadge}{score !== undefined ? ` (${score})` : ""}</Badge>}
            <Badge>{String(statusVal).toUpperCase()}</Badge>
          </div>
        </div>

        {/* Input summary */}
        <Card>
          <CardHeader>
            <CardTitle>Your Request</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {input ? <p>{input}</p> : <p>No input text provided.</p>}
          </CardContent>
        </Card>

        {/* Output (pretty) */}
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Report</CardTitle>
          </CardHeader>
          <CardContent>
            {output ? (
              <div className="prose prose-sm max-w-none whitespace-pre-wrap">
                {output}
              </div>
            ) : (
              <Alert>
                <AlertTitle>No summary text</AlertTitle>
                <AlertDescription>
                  The API didn't return a top-level <code>output</code> string.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <div className="flex gap-2">
          <RouterLink to="/" className="inline-block">
            <Button variant="outline">Back to Home</Button>
          </RouterLink>
          <Button
            onClick={() => {
              // quick export: download JSON of parsed payload
              const blob = new Blob([JSON.stringify(parsed ?? raw, null, 2)], { type: "application/json" })
              const url = URL.createObjectURL(blob)
              const a = document.createElement("a")
              a.href = url
              a.download = "report.json"
              a.click()
              URL.revokeObjectURL(url)
            }}
          >
            Download JSON
          </Button>
        </div>
      </div>
    </div>
  )
}
