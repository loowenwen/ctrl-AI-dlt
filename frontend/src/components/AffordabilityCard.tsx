import { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Loader2, X } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// Types for BTO data structure
interface BTOProject {
  coordinates: string;
  properties: {
    description: Array<{
      town: string;
      flatType: string;
      stage: string;
      maxRemainingLease: string;
    }>;
  };
}

// Types for the selected BTO
interface SelectedBTO {
  project: string;
  flatType: string;
  price?: number;
}

interface AffordabilityResult {
  name: string;
  flatType: string;
  price: number;
  affordability_status: string;
  shortfall: number;
  monthly_payment?: number;
  project_tier?: string;
  downpayment_needed?: number;
  potential_grants?: string[];
  additional_requirements?: string;
}

interface AffordabilityCardProps {
  totalBudget?: number;
  defaultBTO?: {
    name: string;
    flatType?: string;
  };
}

export default function AffordabilityCard({ totalBudget, defaultBTO }: AffordabilityCardProps) {
  const [availableProjects, setAvailableProjects] = useState<BTOProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [selectedFlatType, setSelectedFlatType] = useState<string>("");
  const [selectedBTOs, setSelectedBTOs] = useState<SelectedBTO[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<AffordabilityResult[] | null>(null);

  // Load available BTOs
  useEffect(() => {
    async function loadBTOData() {
      try {
        const response = await fetch('/api/bto-data');
        const data: BTOProject[] = await response.json();
        setAvailableProjects(data);
        
        // If default BTO is provided, auto-add it to the list
        if (defaultBTO && defaultBTO.flatType) {
          try {
            const priceResponse = await fetch(`/api/estimate-price/${encodeURIComponent(defaultBTO.name)}/${encodeURIComponent(defaultBTO.flatType)}`);
            if (priceResponse.ok) {
              const priceData = await priceResponse.json();
              setSelectedBTOs([{
                project: defaultBTO.name,
                flatType: defaultBTO.flatType,
                price: priceData.estimated_price
              }]);
            }
          } catch (error) {
            console.error('Failed to load default BTO price:', error);
            // Still set the project and flat type for manual selection
            setSelectedProject(defaultBTO.name);
            setSelectedFlatType(defaultBTO.flatType);
          }
        }
      } catch (error) {
        console.error('Failed to load BTO data:', error);
        setError('Failed to load available BTO projects');
      }
    }
    loadBTOData();
  }, [defaultBTO]);

  // Reset flat type when project changes
  useEffect(() => {
    setSelectedFlatType("");
  }, [selectedProject]);

  // Get available flat types for selected project
  const getAvailableFlatTypes = useCallback((projectName: string) => {
    const project = availableProjects.find(
      p => p.properties.description[0].town === projectName
    );
    if (!project) return [];
    return project.properties.description[0].flatType
      .split(", ")
      .map(type => type.replace(" Flexi", ""));
  }, [availableProjects]);

  // Add BTO
  const addBTO = useCallback(async () => {
    if (!selectedProject || !selectedFlatType) return;

    try {
      // Get price estimate
      const response = await fetch(`/api/estimate-price/${encodeURIComponent(selectedProject)}/${encodeURIComponent(selectedFlatType)}`);
      if (!response.ok) {
        throw new Error("Failed to get price estimate");
      }
      const data = await response.json();
      
      setSelectedBTOs(current => [...current, {
        project: selectedProject,
        flatType: selectedFlatType,
        price: data.estimated_price
      }]);

      // Reset selections
      setSelectedProject("");
      setSelectedFlatType("");
      setError(null);
    } catch (error) {
      setError("Failed to get price estimate for selected BTO");
    }
  }, [selectedProject, selectedFlatType]);

  // Remove BTO
  const removeBTO = useCallback((index: number) => {
    setSelectedBTOs(current => current.filter((_, i) => i !== index));
    setResults(null); // Clear results when removing a BTO
  }, []);

  // Check affordability
  const checkAffordability = useCallback(async () => {
    if (!totalBudget || selectedBTOs.length === 0) return;

    setIsLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const response = await fetch("/api/affordability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          total_budget: totalBudget,
          btos: selectedBTOs.map(bto => ({
            name: bto.project,
            flatType: bto.flatType,
            price: bto.price
          }))
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to check affordability");
      }

      const data = await response.json();
      setResults(data.results);
    } catch (error) {
      setError("Failed to check affordability. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [totalBudget, selectedBTOs]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Affordability Check</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Project Selection */}
        <div className="grid gap-4">
          {/* BTO Project Selection */}
          <div className="grid gap-2">
            <Label htmlFor="bto-project">BTO Project</Label>
            <Select value={selectedProject} onValueChange={setSelectedProject}>
              <SelectTrigger id="bto-project" className="bg-white">
                <SelectValue placeholder="Choose BTO project" />
              </SelectTrigger>
              <SelectContent className="z-[3001]">
                {availableProjects.map((project) => (
                  <SelectItem 
                    key={project.properties.description[0].town} 
                    value={project.properties.description[0].town}
                  >
                    {project.properties.description[0].town}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Flat Type Selection */}
          {selectedProject && (
            <div className="grid gap-2">
              <Label htmlFor="flat-type">Flat Type</Label>
              <Select value={selectedFlatType} onValueChange={setSelectedFlatType}>
                <SelectTrigger id="flat-type" className="bg-white">
                  <SelectValue placeholder="Choose flat type" />
                </SelectTrigger>
                <SelectContent className="z-[3001]">
                  {getAvailableFlatTypes(selectedProject).map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Add BTO Button */}
          <Button 
            onClick={addBTO}
            disabled={!selectedProject || !selectedFlatType}
            variant="outline"
          >
            Add BTO to Compare
          </Button>
        </div>

        {/* Selected BTOs List */}
        {selectedBTOs.length > 0 && (
          <div className="space-y-3 border-t pt-4">
            <Label>Selected BTOs</Label>
            <div className="space-y-2">
              {selectedBTOs.map((bto, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                  <div className="space-y-1">
                    <div className="font-medium">{bto.project}</div>
                    <div className="text-sm text-gray-500">
                      {bto.flatType} - ${bto.price?.toLocaleString() || 'Calculating...'}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeBTO(index)}
                    className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>

            {/* Check Affordability Button */}
            <Button
              onClick={checkAffordability}
              disabled={isLoading || !totalBudget}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Checking...
                </>
              ) : (
                'Check Affordability'
              )}
            </Button>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {/* Results */}
        {results && results.length > 0 && (
          <div className="space-y-4 border-t pt-4">
            <Label>Affordability Analysis</Label>
            <div className="space-y-4">
              {results.map((result, index) => (
                <div key={index} className={`rounded-lg border p-4 ${
                  result.affordability_status === "Affordable"
                    ? "bg-green-50 border-green-200"
                    : "bg-red-50 border-red-200"
                }`}>
                  <div className="space-y-3">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-lg">{result.name}</h4>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        result.affordability_status === "Affordable"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}>
                        {result.affordability_status}
                      </span>
                    </div>

                    {/* Basic Info */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium">Flat Type:</span> {result.flatType}
                      </div>
                      <div>
                        <span className="font-medium">Price:</span> ${result.price.toLocaleString()}
                      </div>
                      {result.project_tier && (
                        <div>
                          <span className="font-medium">Project Tier:</span> {result.project_tier}
                        </div>
                      )}
                      {result.monthly_payment && (
                        <div>
                          <span className="font-medium">Monthly Payment:</span> ${result.monthly_payment.toLocaleString()}
                        </div>
                      )}
                    </div>

                    {/* Financial Details */}
                    {result.downpayment_needed && (
                      <div className="text-sm">
                        <span className="font-medium">Required Downpayment (15%):</span> ${result.downpayment_needed.toLocaleString()}
                      </div>
                    )}

                    {/* Shortfall Warning */}
                    {result.shortfall > 0 && (
                      <div className="bg-red-100 border border-red-200 rounded-lg p-3">
                        <p className="text-red-700 font-medium text-sm">
                          ⚠️ Budget Shortfall: ${result.shortfall.toLocaleString()}
                        </p>
                        <p className="text-red-600 text-xs mt-1">
                          You need an additional ${result.shortfall.toLocaleString()} to afford this BTO.
                        </p>
                      </div>
                    )}

                    {/* Grants */}
                    {result.potential_grants && result.potential_grants.length > 0 && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <p className="font-medium text-blue-800 text-sm mb-2">💰 Potential Grants Available:</p>
                        <ul className="text-blue-700 text-xs space-y-1">
                          {result.potential_grants.map((grant, grantIndex) => (
                            <li key={grantIndex}>• {grant}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Additional Requirements */}
                    {result.additional_requirements && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <p className="font-medium text-yellow-800 text-sm">📋 Additional Requirements:</p>
                        <p className="text-yellow-700 text-xs mt-1">{result.additional_requirements}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Summary */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h5 className="font-medium text-gray-800 mb-2">Summary</h5>
              <div className="text-sm text-gray-600 space-y-1">
                <p>Your Total Budget: ${totalBudget?.toLocaleString()}</p>
                <p>Recommended Max Monthly Payment: ${(totalBudget ? totalBudget * 0.03 : 0).toLocaleString()}</p>
                <p className="text-xs text-gray-500 mt-2">
                  * Monthly payments calculated based on 25-year loan tenure at 2.6% interest rate
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
