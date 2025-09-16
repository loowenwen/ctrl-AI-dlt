import { useEffect, useMemo, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, X } from "lucide-react";
import TransportResultView, { type TransportResult } from "@/components/TransportResultView";
import TransportComparisonView, { type TransportComparisonResult } from "@/components/TransportComparisonView";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

type BTOListingAPI = {
  lat: number;
  lng: number;
  town: string;
  flatType: string;
  projectId?: string;
  region?: string;
  listingType?: string;
  stage?: string;
  ballotQtr?: string;
};

type Props = {
  btoProject?: string;
  autoRun?: {
    destinationPostal: string;
    timePeriod: string;
  };
};

const ALL_VALUE = "__ALL__";

type AllResponse = Record<string, TransportResult>;

export default function TransportCard({ btoProject, autoRun }: Props) {
  const [projects, setProjects] = useState<string[]>([]);
  const [projectsLoading, setProjectsLoading] = useState<boolean>(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const [name, setName] = useState<string>(btoProject ?? "");
  const [postal, setPostal] = useState<string>("");
  const [period, setPeriod] = useState<string>("");

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [singleData, setSingleData] = useState<TransportResult | null>(null);
  const [allData, setAllData] = useState<AllResponse | null>(null);
  const [compareTargets, setCompareTargets] = useState<string[]>([]);
  const [compareResult, setCompareResult] = useState<TransportComparisonResult | null>(null);
  const [analyzedProjects, setAnalyzedProjects] = useState<string[]>([]);
  const [hasAutoRun, setHasAutoRun] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setProjectsLoading(true);
        setProjectsError(null);
        const res = await fetch(`http://127.0.0.1:8000/bto_listings`);
        if (!res.ok) throw new Error(`Failed to load listings (${res.status})`);
        const json = (await res.json()) as BTOListingAPI[];
        if (!alive) return;

        const names = Array.from(
          new Set(json.map((x) => (x.town || "").trim()).filter(Boolean))
        ).sort();

        setProjects(names);

        // Preselect prop if present
        if (btoProject && names.includes(btoProject)) {
          setName((prev) => (prev ? prev : btoProject));
        }
      } catch (e: any) {
        if (!alive) return;
        setProjectsError(e?.message || "Failed to load projects");
      } finally {
        if (alive) setProjectsLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [btoProject]);

  // Reset hasAutoRun when autoRun props change
  useEffect(() => {
    setHasAutoRun(false);
  }, [autoRun]);

  // Auto-run transport analysis if autoRun parameters are provided
  useEffect(() => {
    console.log('🔍 TransportCard auto-run check:', {
      autoRun: !!autoRun,
      btoProject,
      destinationPostal: autoRun?.destinationPostal,
      timePeriod: autoRun?.timePeriod,
      hasAutoRun,
      isLoading,
      hasResults: !!singleData
    });
    
    // Auto-run when we have autoRun params (regardless of specific BTO or all BTOs)
    if (autoRun && autoRun.destinationPostal && autoRun.timePeriod && !hasAutoRun && !isLoading) {
      console.log('🚀 TransportCard: AUTO-TRIGGERING transport analysis...');
      setHasAutoRun(true);
      setPostal(autoRun.destinationPostal);
      setPeriod(autoRun.timePeriod);
      
      // If specific BTO provided, use it; otherwise analyze ALL BTOs
      if (btoProject) {
        console.log('🏠 TransportCard: Analyzing specific BTO:', btoProject);
        setName(btoProject);
      } else {
        console.log('🏢 TransportCard: Auto-selecting ALL BTOs for comprehensive analysis');
        setName(ALL_VALUE); // Auto-select "All BTOs"
      }
      
      // Run analysis after form is populated
      setTimeout(() => {
        console.log('🎯 TransportCard: Auto-executing onQuery...');
        onQuery();
      }, 500); // Longer delay to ensure state updates
    }
  }, [autoRun, btoProject, hasAutoRun, isLoading]);

  const isAll = name === ALL_VALUE;

  const canQuery = useMemo(() => {
    // For "All", we don't need a specific name
    return (isAll || name.trim().length > 0) && postal.trim().length > 0 && period.trim().length > 0;
  }, [isAll, name, postal, period]);

  async function onQuery() {
    if (!canQuery) return;
    setIsLoading(true);
    setError(null);
    setSingleData(null);
    setAllData(null);
    setCompareResult(null);

    try {
      if (isAll) {
        const params = new URLSearchParams({
          postal_code: postal.trim(),
          time_period: period.trim(),
        });
        const res = await fetch(`http://127.0.0.1:8000/analyze_all_btos?${params.toString()}`, {
          method: "POST",
        });
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        const json = (await res.json()) as AllResponse;
        setAllData(json);
      } else {
        // Single project
        const params = new URLSearchParams({
          name: name.trim(),
          postal_code: postal.trim(),
          time_period: period.trim(),
        });
        const res = await fetch(`http://127.0.0.1:8000/analyze_bto?${params.toString()}`, {
          method: "POST",
        });
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        const json = (await res.json()) as TransportResult;
        setSingleData(json);
        // Record that this project has been analyzed successfully for this session
        setAnalyzedProjects((prev) => (prev.includes(name) ? prev : [...prev, name]));
      }
    } catch (e: any) {
      setError(e?.message || "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }

  function addCompareTarget() {
    if (!name || name === ALL_VALUE) return;
    if (!analyzedProjects.includes(name)) {
      setError("Analyze this BTO first using Query before adding to comparison.");
      return;
    }
    setCompareTargets((prev) => (prev.includes(name) ? prev : [...prev, name]));
  }

  function removeCompareTarget(target: string) {
    setCompareTargets((prev) => prev.filter((t) => t !== target));
  }

  async function clearComparison() {
    try {
      setIsLoading(true);
      setError(null);
      await fetch(`http://127.0.0.1:8000/compare_btos/clear`, { method: "DELETE" });
      setCompareResult(null);
    } catch (e: any) {
      setError(e?.message || "Failed to clear comparison data");
    } finally {
      setIsLoading(false);
    }
  }

  async function runComparison() {
    if (postal.trim().length === 0 || period.trim().length === 0) return;
    // Must have analyzed at least 2 different BTOs in single mode
    const uniqueTargets = Array.from(new Set(compareTargets));
    if (uniqueTargets.length < 2) {
      setError("Add at least 2 analyzed BTOs to compare.");
      return;
    }
    // Ensure all selected compare targets were previously analyzed
    const missing = uniqueTargets.filter((t) => !analyzedProjects.includes(t));
    if (missing.length > 0) {
      setError(`Analyze first: ${missing.join(", ")}`);
      return;
    }
    setIsLoading(true);
    setError(null);
    setSingleData(null);
    setAllData(null);
    setCompareResult(null);

    try {
      // Then call compare endpoint; backend reads saved comparison set
      const cmpParams = new URLSearchParams({
        destination_address: postal.trim(),
        time_period: period.trim(),
      });
      const cmpRes = await fetch(`http://127.0.0.1:8000/compare_btos?${cmpParams.toString()}`, { method: "POST" });
      if (!cmpRes.ok) throw new Error(`Compare failed (${cmpRes.status})`);
      const cmpJson = (await cmpRes.json()) as TransportComparisonResult;
      setCompareResult(cmpJson);
    } catch (e: any) {
      setError(e?.message || "Comparison failed");
    } finally {
      setIsLoading(false);
    }
  }

  // Sort keys when rendering "All" for consistent order
  const allEntries = useMemo(() => {
    if (!allData) return [];
    return Object.entries(allData).sort(([a], [b]) => a.localeCompare(b));
  }, [allData]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transportation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Form */}
        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="bto-name">BTO Project</Label>
            <Select
              value={name || undefined}
              onValueChange={setName}
              disabled={projectsLoading || !!projectsError}
            >
              <SelectTrigger id="bto-name" className="w-full">
                <SelectValue placeholder={projectsLoading ? "Loading…" : "Select a BTO project"} />
              </SelectTrigger>
              <SelectContent className="max-h-72">
                <SelectItem value={ALL_VALUE}>All BTOs</SelectItem>
                {projects.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {projectsError && (
              <p className="text-xs text-rose-600">Failed to load projects: {projectsError}</p>
            )}
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="postal">Destination Postal Code</Label>
            <Input
              id="postal"
              type="text"
              inputMode="numeric"
              placeholder="e.g. 079903"
              value={postal}
              onChange={(e) => setPostal(e.target.value)}
            />
          </div>

          <div className="grid gap-1.5">
            <Label>Time Period</Label>
            <Select value={period} onValueChange={setPeriod}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Choose time period" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Morning Peak">Morning Peak</SelectItem>
                <SelectItem value="Evening Peak">Evening Peak</SelectItem>
                <SelectItem value="Daytime Off-Peak">Daytime Off-Peak</SelectItem>
                <SelectItem value="Nighttime Off-Peak">Nighttime Off-Peak</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-wrap gap-2 justify-end">
            <Button onClick={addCompareTarget} variant="outline" disabled={!name || name === ALL_VALUE || isLoading || !analyzedProjects.includes(name)}>
              Add to Compare
            </Button>
            <Button onClick={onQuery} disabled={!canQuery || isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLoading ? "Running Transportation Agent" : "Query"}
            </Button>
          </div>
        </div>

        {/* States */}
        {error && (
          <Alert>
            <AlertTitle>Transport analysis failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading && !error && (
          <div className="text-sm text-muted-foreground">
            {isAll
              ? "Analyzing all BTO locations… computing routes, walking times, and transfers."
              : "Computing route, walking time, transfers and reliability…"}
          </div>
        )}

        {/* Results */}
        {/* Compare selection chips */}
        {compareTargets.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-semibold">Selected for comparison</div>
            <div className="flex flex-wrap gap-2">
              {compareTargets.map((t) => (
                <div key={t} className="flex items-center gap-2 bg-gray-100 rounded-full px-3 py-1 text-sm">
                  <span className="font-medium">{t}</span>
                  <button className="text-gray-500 hover:text-gray-700" onClick={() => removeCompareTarget(t)} aria-label={`Remove ${t}`}>
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button onClick={runComparison} disabled={isLoading || compareTargets.length === 0 || !postal || !period}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Compare Selected
              </Button>
              <Button onClick={clearComparison} variant="ghost" disabled={isLoading}>Clear Comparison</Button>
            </div>
          </div>
        )}

        {!isLoading && !error && singleData && (
          <>
            <div className="text-base font-semibold">{name}</div>
            <TransportResultView data={singleData} />
          </>
        )}

        {!isLoading && !error && allEntries.length > 0 && (
          <Accordion type="multiple" className="w-full">
            {allEntries.map(([projectName, resultObj]) => (
              <AccordionItem key={projectName} value={projectName}>
                <AccordionTrigger className="text-base font-semibold">
                  {projectName}
                </AccordionTrigger>
                <AccordionContent>
                  <div className="pt-2">
                    <TransportResultView name={projectName} data={resultObj} />
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}

        {!isLoading && !error && compareResult && (
          <div className="border-t pt-4">
            <div className="text-base font-semibold mb-2">Transport Comparison</div>
            <TransportComparisonView data={compareResult} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
