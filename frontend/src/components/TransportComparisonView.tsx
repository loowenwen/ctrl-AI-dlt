import { Separator } from "@/components/ui/separator";

export type TransportComparisonResult = {
  result?: {
    ranking?: Array<{ rank: number; bto_name: string }>;
    winner_analysis?: {
      bto_name: string;
      advantages?: {
        journey_time?: { minutes?: number; vs_others?: number[]; advantage?: string };
        starting_point?: {
          station_code?: string;
          station_name?: string;
          walking_distance_meters?: number;
          walking_time_minutes?: number;
          advantage?: string;
        };
        transfers?: { count?: number; vs_others?: number[]; advantage?: string };
        transport_options?: {
          modes?: string[];
          reliability?: string;
          backup_routes?: boolean;
          advantage?: string;
        };
        peak_performance?: string;
      };
      key_differentiator?: string;
    };
    comparison_table?: Array<{
      bto_name: string;
      total_time_minutes?: number;
      walking_time_minutes?: number;
      transfers?: number;
      best_route?: string;
    }>;
    summary?: { overall_assessment?: string };
  };
  raw_text?: string;
};

export default function TransportComparisonView({ data }: { data: TransportComparisonResult }) {
  const r = data?.result;

  if (!data) {
    return null;
  }

  if (!r && data.raw_text) {
    return (
      <div className="space-y-3 text-sm">
        <div className="font-semibold">Comparison (unstructured)</div>
        <p className="whitespace-pre-wrap text-muted-foreground">{data.raw_text}</p>
      </div>
    );
  }

  if (!r) {
    return <div className="text-sm text-muted-foreground">No comparison result available.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Ranking */}
      {Array.isArray(r.ranking) && r.ranking.length > 0 && (
        <section className="space-y-2">
          <div className="text-sm font-semibold">Ranking</div>
          <ol className="list-decimal ml-5 text-sm space-y-1">
            {r.ranking.map((x) => (
              <li key={x.rank}>
                <span className="font-medium">#{x.rank}</span> {x.bto_name}
              </li>
            ))}
          </ol>
        </section>
      )}

      <Separator />

      {/* Winner analysis */}
      {r.winner_analysis && (
        <section className="space-y-3">
          <div className="text-sm font-semibold">Top pick: {r.winner_analysis.bto_name}</div>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            {r.winner_analysis.advantages?.journey_time && (
              <div>
                <div className="font-medium">Journey time</div>
                <div className="text-muted-foreground">
                  {r.winner_analysis.advantages.journey_time.minutes != null ? `${r.winner_analysis.advantages.journey_time.minutes} min` : "—"}
                </div>
                {r.winner_analysis.advantages.journey_time.advantage && (
                  <div className="text-xs text-emerald-700">{r.winner_analysis.advantages.journey_time.advantage}</div>
                )}
              </div>
            )}
            {r.winner_analysis.advantages?.starting_point && (
              <div>
                <div className="font-medium">Starting point</div>
                <div className="text-muted-foreground">
                  {r.winner_analysis.advantages.starting_point.station_name}
                  {r.winner_analysis.advantages.starting_point.station_code ? ` (${r.winner_analysis.advantages.starting_point.station_code})` : ""}
                </div>
                <div className="text-muted-foreground">
                  {r.winner_analysis.advantages.starting_point.walking_distance_meters != null ? `${Math.round(r.winner_analysis.advantages.starting_point.walking_distance_meters)} m` : "—"}
                  {" • "}
                  {r.winner_analysis.advantages.starting_point.walking_time_minutes != null ? `${r.winner_analysis.advantages.starting_point.walking_time_minutes} min walk` : "—"}
                </div>
                {r.winner_analysis.advantages.starting_point.advantage && (
                  <div className="text-xs text-emerald-700">{r.winner_analysis.advantages.starting_point.advantage}</div>
                )}
              </div>
            )}
            {r.winner_analysis.advantages?.transfers && (
              <div>
                <div className="font-medium">Transfers</div>
                <div className="text-muted-foreground">{r.winner_analysis.advantages.transfers.count ?? "—"}</div>
                {r.winner_analysis.advantages.transfers.advantage && (
                  <div className="text-xs text-emerald-700">{r.winner_analysis.advantages.transfers.advantage}</div>
                )}
              </div>
            )}
            {r.winner_analysis.advantages?.transport_options && (
              <div>
                <div className="font-medium">Transport options</div>
                <div className="text-muted-foreground">
                  {Array.isArray(r.winner_analysis.advantages.transport_options.modes)
                    ? r.winner_analysis.advantages.transport_options.modes.join(", ")
                    : "—"}
                </div>
                {r.winner_analysis.advantages.transport_options.reliability && (
                  <div className="text-muted-foreground">Reliability: {r.winner_analysis.advantages.transport_options.reliability}</div>
                )}
                <div className="text-muted-foreground">
                  Backup routes: {typeof r.winner_analysis.advantages.transport_options.backup_routes === "boolean" ? (r.winner_analysis.advantages.transport_options.backup_routes ? "Yes" : "No") : "—"}
                </div>
                {r.winner_analysis.advantages.transport_options.advantage && (
                  <div className="text-xs text-emerald-700">{r.winner_analysis.advantages.transport_options.advantage}</div>
                )}
              </div>
            )}
          </div>
          {r.winner_analysis.key_differentiator && (
            <div className="text-sm">
              <span className="font-medium">Key differentiator:</span> {r.winner_analysis.key_differentiator}
            </div>
          )}
        </section>
      )}

      {/* Comparison table */}
      {Array.isArray(r.comparison_table) && r.comparison_table.length > 0 && (
        <section className="space-y-2">
          <div className="text-sm font-semibold">Comparison table</div>
          <div className="text-xs text-muted-foreground">(Based on best route per location)</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left">
                <tr className="border-b">
                  <th className="py-2 pr-4">BTO</th>
                  <th className="py-2 pr-4">Total time (min)</th>
                  <th className="py-2 pr-4">Walk (min)</th>
                  <th className="py-2 pr-4">Transfers</th>
                  <th className="py-2 pr-4">Best route</th>
                </tr>
              </thead>
              <tbody>
                {r.comparison_table.map((row) => (
                  <tr key={row.bto_name} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{row.bto_name}</td>
                    <td className="py-2 pr-4">{row.total_time_minutes ?? "—"}</td>
                    <td className="py-2 pr-4">{row.walking_time_minutes ?? "—"}</td>
                    <td className="py-2 pr-4">{row.transfers ?? "—"}</td>
                    <td className="py-2 pr-4">{row.best_route ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Summary */}
      {r.summary?.overall_assessment && (
        <section className="space-y-1">
          <div className="text-sm font-semibold">Overall assessment</div>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{r.summary.overall_assessment}</p>
        </section>
      )}
    </div>
  );
}
