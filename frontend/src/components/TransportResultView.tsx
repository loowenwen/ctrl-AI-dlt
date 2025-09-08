import { Separator } from "@/components/ui/separator";

export type TransportResult = {
  result: {
    daily_commute: {
      summary: string;
      total_time_minutes: number;
      feeling: string;
    };
    key_details: {
      journey_time: string;
      starting_point: {
        station_code: string;
        station_name: string;
        walking_distance_meters: number;
        walking_time_minutes: number;
        accessibility_note?: string;
      };
      transfers: {
        count: number;
        complexity: string;
        frequency?: string;
      };
      transport_options: {
        modes: string[];
        reliability?: string;
        backup_routes?: boolean;
      };
    };
    pros_and_cons: {
      pros: string[];
      cons: string[];
    };
    decision_tip: string;
  };
};

export default function TransportResultView({
  data,
}: {
  name?: string;
  data: TransportResult;
}) {
  const r = data.result;
  return (
    <div className="space-y-4">
      <section className="space-y-1">
        <div className="text-sm text-muted-foreground">Daily commute</div>
        <div className="text-base font-semibold">{r.daily_commute.summary}</div>
        <div className="text-sm">
          Total time: <span className="font-medium">{fmtMin(r.daily_commute.total_time_minutes)}</span>
        </div>
        <div className="text-sm text-muted-foreground">{r.daily_commute.feeling}</div>
      </section>

      <Separator />

      <section className="space-y-2">
        <div className="text-sm font-semibold">Key details</div>
        <ul className="text-sm space-y-1">
          <li>
            <span className="text-muted-foreground">Journey time:</span>{" "}
            <span className="font-medium">{r.key_details.journey_time}</span>
          </li>
          <li>
            <span className="text-muted-foreground">Start:</span>{" "}
            <span className="font-medium">
              {r.key_details.starting_point.station_name} ({r.key_details.starting_point.station_code})
            </span>
          </li>
          <li>
            <span className="text-muted-foreground">Walk:</span>{" "}
            <span className="font-medium">
              {Math.round(r.key_details.starting_point.walking_distance_meters)} m •{" "}
              {fmtMin(r.key_details.starting_point.walking_time_minutes)}
            </span>
          </li>
          {r.key_details.starting_point.accessibility_note && (
            <li className="text-muted-foreground">
              {r.key_details.starting_point.accessibility_note}
            </li>
          )}
          <li>
            <span className="text-muted-foreground">Transfers:</span>{" "}
            <span className="font-medium">
              {r.key_details.transfers.count} • {r.key_details.transfers.complexity}
            </span>
          </li>
          {r.key_details.transfers.frequency && (
            <li>
              <span className="text-muted-foreground">Frequency:</span>{" "}
              <span className="font-medium">{r.key_details.transfers.frequency}</span>
            </li>
          )}
          {r.key_details.transport_options?.modes?.length > 0 && (
            <li>
              <span className="text-muted-foreground">Modes:</span>{" "}
              <span className="font-medium">{r.key_details.transport_options.modes.join(", ")}</span>
            </li>
          )}
          {r.key_details.transport_options?.reliability && (
            <li>
              <span className="text-muted-foreground">Reliability:</span>{" "}
              <span className="font-medium">{r.key_details.transport_options.reliability}</span>
            </li>
          )}
          {typeof r.key_details.transport_options?.backup_routes === "boolean" && (
            <li>
              <span className="text-muted-foreground">Backup routes:</span>{" "}
              <span className="font-medium">{r.key_details.transport_options.backup_routes ? "Yes" : "No"}</span>
            </li>
          )}
        </ul>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <div>
          <div className="text-sm font-semibold">Pros</div>
          <ul className="list-disc ml-5 text-sm">
            {r.pros_and_cons.pros.map((p, i) => <li key={`pro-${i}`}>{p}</li>)}
          </ul>
        </div>
        <div>
          <div className="text-sm font-semibold">Cons</div>
          <ul className="list-disc ml-5 text-sm">
            {r.pros_and_cons.cons.map((c, i) => <li key={`con-${i}`}>{c}</li>)}
          </ul>
        </div>
      </section>

      <section>
        <div className="text-sm font-semibold">Decision tip</div>
        <p className="text-sm">{r.decision_tip}</p>
      </section>
    </div>
  );
}

function fmtMin(n: number | undefined | null): string {
  if (n == null || !isFinite(n)) return "—";
  const minutes = Number(n);
  if (minutes < 1) return `${(minutes * 60).toFixed(0)} sec`;
  return `${minutes.toFixed(1)} min`;
}