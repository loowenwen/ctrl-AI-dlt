// src/components/LoadingView.tsx
import { useEffect, useState } from "react";
import { Loader2, Dot } from "lucide-react";

export type LoadingStep = {
  title: string;
  desc: string;
};

interface LoadingViewProps {
  sentence: string;
}

const DEFAULT_STEPS: LoadingStep[] = [
  { title: "Gathering signals", desc: "Scraping official sites & forums for launch info, prices, amenities." },
  { title: "Social media scan", desc: "Crawling TikTok & videos; extracting audio, captions, thumbnails." },
  { title: "Multimodal understanding", desc: "Analyzing text + video frames to summarize quality and locality." },
  { title: "Sentiment & risk scoring", desc: "Measuring public sentiment and flagging concerns." },
  { title: "Synthesis", desc: "Merging findings into a personalized report based on your inputs." },
];

export default function LoadingView({ sentence }: LoadingViewProps) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setActive((i) => (i + 1) % DEFAULT_STEPS.length), 2200);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-4 rounded-md border bg-muted/30 p-4">
      <div className="flex items-center gap-2 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Running multi-agent analysis…</span>
      </div>

      <div className="rounded-md border p-3 bg-white text-sm">
        <div className="font-medium mb-1">Your request</div>
        <div className="text-muted-foreground">{sentence}</div>
      </div>

      <ol className="mt-2 space-y-2">
        {DEFAULT_STEPS.map((s, i) => (
          <li
            key={s.title}
            className={`rounded-md border p-3 ${i === active ? "bg-muted/40" : "bg-white"}`}
          >
            <div className="flex items-center gap-2">
              <Dot className={`h-5 w-5 ${i === active ? "animate-pulse" : ""}`} />
              <span className="font-medium">{s.title}</span>
            </div>
            <p className="pl-7 text-sm text-muted-foreground">{s.desc}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}