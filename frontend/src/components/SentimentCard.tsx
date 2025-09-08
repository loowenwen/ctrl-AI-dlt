import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Link as RouterLink } from "react-router-dom"
import { type ApiEnvelope } from "./SentimentReport";

interface SentimentCardProps {
  input: string | undefined;
  output: string | undefined;
  parsed: string | undefined;
  raw: ApiEnvelope | undefined;
}

export default function SentimentCard({ input, output, parsed, raw }: SentimentCardProps) {
  return (
    <>
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

      {/* Actions */}
      <div className="flex gap-2">
        <RouterLink to="/" className="inline-block">
          <Button variant="outline">Back to Home</Button>
        </RouterLink>
        <Button
          onClick={() => {
            const blob = new Blob(
              [JSON.stringify(parsed ?? raw, null, 2)],
              { type: "application/json" }
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "report.json";
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          Download JSON
        </Button>
      </div>
    </>
  )
}