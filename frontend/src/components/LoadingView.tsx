import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Loader2, Dot, CheckCircle2 } from "lucide-react"
import { TealButton } from "./TealButton";

export type LoadingPhase = "form" | "loading" | "done" | "error";

export interface LoadingStep {
  title: string;
  desc: string;
}

interface LoadingViewProps {
  phase: LoadingPhase;
  sentence: string;
  steps?: LoadingStep[];
  onCancel?: () => void;
  onViewReport?: () => void;   // shown when phase === "done"
  errorMessage?: string;       // shown when phase === "error"
}

const DEFAULT_STEPS: LoadingStep[] = [
  { title: "Gathering signals", desc: "Scraping official sites & forums for launch info, prices, amenities." },
  { title: "Social media scan", desc: "Crawling TikTok & videos; extracting audio, captions, thumbnails." },
  { title: "Multimodal understanding", desc: "Analyzing text + video frames to summarize quality and locality." },
  { title: "Sentiment & risk scoring", desc: "Measuring public sentiment and flagging concerns." },
  { title: "Synthesis", desc: "Merging findings into a personalized report based on your inputs." },
];

export default function LoadingView({
  phase,
  sentence,
  steps = DEFAULT_STEPS,
  onCancel,
  onViewReport,
  errorMessage,
}: LoadingViewProps) {
  const [active, setActive] = useState(0)

  useEffect(() => {
    if (phase !== "loading") return
    const t = setInterval(() => setActive((i) => (i + 1) % steps.length), 2200)
    return () => clearInterval(t)
  }, [phase, steps.length])

  if (phase === "done") {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Report ready</DialogTitle>
          <DialogDescription>Your multi-agent analysis is complete.</DialogDescription>
        </DialogHeader>
        <div className="rounded-md border bg-muted/30 p-3 text-sm">
          <div className="flex items-center gap-2 text-emerald-700">
            <CheckCircle2 className="h-5 w-5" />
            Analysis complete. Click below to view your report.
          </div>
        </div>
        <DialogFooter>
          <TealButton onClick={onViewReport}>
            View report
          </TealButton>
        </DialogFooter>
      </>
    )
  }

  if (phase === "error") {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Something went wrong</DialogTitle>
          <DialogDescription className="text-red-600">
            {errorMessage ?? "Please try again."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>Close</Button>
        </DialogFooter>
      </>
    )
  }

  // phase === "loading"
  return (
    <>
      <DialogHeader>
        <DialogTitle>Running multi-agent analysis</DialogTitle>
        <DialogDescription>This can take a few minutes.</DialogDescription>
      </DialogHeader>

      <div className="rounded-md border p-3 bg-muted/30 text-sm">
        <div className="font-medium mb-1">Your information</div>
        <div className="text-muted-foreground">{sentence}</div>
      </div>

      <div className="mt-2 flex items-center gap-2 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Working… please keep this tab open.</span>
      </div>

      <ol className="mt-4 space-y-3">
        {steps.map((s, i) => (
          <li key={s.title} className={`rounded-md border p-3 ${i === active ? "bg-muted/40" : "bg-white"}`}>
            <div className="flex items-center gap-2">
              <Dot className={`h-5 w-5 ${i === active ? "animate-pulse" : ""}`} />
              <span className="font-medium">{s.title}</span>
            </div>
            <p className="pl-7 text-sm text-muted-foreground">{s.desc}</p>
          </li>
        ))}
      </ol>

      <DialogFooter>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </DialogFooter>
    </>
  )
}