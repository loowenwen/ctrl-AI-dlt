// src/components/SentimentReport.tsx
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import SentimentCard from "./SentimentCard";
import LoadingView from "./LoadingView";

export type ApiEnvelope = { body?: string } & Record<string, any>;

function safeJsonParse<T = any>(v: unknown): T | null {
  try { return typeof v === "string" ? JSON.parse(v) : (v as T); }
  catch { return null; }
}

type Props = {
  initialText?: string | null;
  isAllBTOAnalysis?: boolean; // Whether user is analyzing all BTOs vs specific BTO
  selectedFlatType?: string; // Flat type for context
};

export default function SentimentReport({ initialText, isAllBTOAnalysis, selectedFlatType }: Props) {
  const [apiRaw, setApiRaw] = useState<ApiEnvelope | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const showLoading = isLoading || (!apiRaw && !apiError && !!initialText);

  useEffect(() => {
    if (!initialText || !initialText.trim()) return;
    const abort = new AbortController();

    (async () => {
      try {
        setIsLoading(true);
        setApiError(null);
        setApiRaw(null);

        // Enhance the prompt for comprehensive BTO analysis
        const enhancedText = isAllBTOAnalysis 
          ? `${initialText}

CONTEXT: Looking at all BTO launches in October 2025 Singapore${selectedFlatType ? ` for ${selectedFlatType} flats` : ''}.`
          : initialText;

        const res = await fetch(
          "https://ituhr6ycktc3r2yvoiiq3igs3q0ebbts.lambda-url.us-east-1.on.aws/",
          {
            method: "POST",
            body: JSON.stringify({ text: enhancedText }),
            signal: abort.signal,
          }
        );
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        const data = await res.json();
        setApiRaw(data);
      } catch (e: any) {
        if (e?.name !== "AbortError") setApiError(e?.message || "Unknown error");
      } finally {
        setIsLoading(false);
      }
    })();

    return () => abort.abort();
  }, [initialText, isAllBTOAnalysis, selectedFlatType]);

  const parsed = useMemo(() => {
    if (!apiRaw) return null;
    const inner = apiRaw?.body ? safeJsonParse(apiRaw.body) : apiRaw;
    return typeof inner === "string" ? safeJsonParse(inner) : inner;
  }, [apiRaw]);

  const input: string | undefined =
    parsed?.input ?? parsed?.request ?? initialText ?? undefined;

  const output: string | undefined =
    parsed?.output ?? parsed?.result ?? parsed?.text ?? undefined;

  const statusVal: string | undefined = (() => {
    if (showLoading) return "executing";
    return parsed?.status?._value_ ?? parsed?.status ?? apiRaw?.status ?? "completed";
  })();

  const scoreMatch = output?.match(/Score:\s*([+-]?[0-9]*\.?[0-9]+)/i);
  const score = scoreMatch ? Number(scoreMatch[1]) : undefined;
  let sentimentBadge: "Positive" | "Negative" | undefined;
  if (score !== undefined) {
    if (score > 0) sentimentBadge = "Positive";
    else sentimentBadge = "Negative";
  }

  return (
    <div className="space-y-4">
      {/* badges */}
      <div className="flex items-center gap-2">
        <Badge>{String(statusVal).toUpperCase()}</Badge>
        {apiError && <Badge className="bg-rose-600 text-white">ERROR</Badge>}
        {sentimentBadge && !isLoading && (
          <Badge
            variant="secondary"
            className={
              sentimentBadge === "Positive"
                ? "bg-emerald-500"
                : "bg-rose-500 text-white"
            }
          >
            {sentimentBadge}{score !== undefined ? ` (${score})` : ""}
          </Badge>
        )}
      </div>

      {/* Conditional view */}
      {showLoading ? (
        <LoadingView sentence={initialText ?? ""} />
      ) : (
        <SentimentCard
          input={input}
          output={output}
          parsed={parsed}
          raw={apiRaw ?? {}}
        />
      )}
    </div>
  );
}