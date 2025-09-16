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
  selectedFlatType?: string; // Filter BTOs by this flat type when doing comprehensive analysis
  defaultBTO?: {
    name: string;
    flatType?: string;
  };
}

export default function AffordabilityCard({ totalBudget, selectedFlatType, defaultBTO }: AffordabilityCardProps) {
  const [availableProjects, setAvailableProjects] = useState<BTOProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [currentFlatType, setCurrentFlatType] = useState<string>("");
  const [selectedBTOs, setSelectedBTOs] = useState<SelectedBTO[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<AffordabilityResult[] | null>(null);
  const [hasAutoRun, setHasAutoRun] = useState(false);

  // Load available BTOs
  useEffect(() => {
    async function loadBTOData() {
      try {
        const response = await fetch('http://127.0.0.1:8000/bto-data');
        const data: BTOProject[] = await response.json();
        setAvailableProjects(data);
        
        // If default BTO is provided, auto-add it to the list
        if (defaultBTO && defaultBTO.flatType) {
          // Do not prefetch prices; just prefill the selection
          setSelectedBTOs([{
            project: defaultBTO.name,
            flatType: defaultBTO.flatType,
          }]);
        } else {
          // If no default BTO, add ALL available BTOs for comprehensive comparison
          const allBTOs: SelectedBTO[] = [];
          data.forEach(project => {
            const town = project.properties.description[0].town;
            const flatTypesString = project.properties.description[0].flatType;
            // Parse flat types (e.g., "2-room, 3-room, 4-room" -> ["2-room", "3-room", "4-room"])
            const flatTypes = flatTypesString.split(", ").map(type => type.replace(" Flexi", ""));
            
            // Filter by selected flat type if provided, otherwise include all flat types
            const targetFlatTypes = selectedFlatType 
              ? flatTypes.filter(type => type === selectedFlatType)
              : flatTypes;
            
            // Add each matching flat type as a separate BTO option
            targetFlatTypes.forEach(flatType => {
              allBTOs.push({
                project: town,
                flatType: flatType,
              });
            });
          });
          
          console.log('AffordabilityCard: Auto-adding BTOs for comparison:', {
            selectedFlatType,
            totalBTOs: allBTOs.length,
            filteredBy: selectedFlatType ? `${selectedFlatType} only` : 'all flat types'
          });
          setSelectedBTOs(allBTOs);
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
    setCurrentFlatType("");
  }, [selectedProject]);

  // Clear results when total budget changes and reset auto-run flag
  useEffect(() => {
    setResults(null);
    setError(null);
    setHasAutoRun(false); // Reset auto-run flag when budget changes
  }, [totalBudget]);

  // Auto-run affordability check when budget becomes available and default BTO is provided
  useEffect(() => {
    console.log('AffordabilityCard defaultBTO effect:', {
      totalBudget,
      defaultBTO,
      selectedBTOsLength: selectedBTOs.length
    });
    
    if (totalBudget && defaultBTO && defaultBTO.flatType && selectedBTOs.length === 0) {
      console.log('AffordabilityCard - Auto-adding default BTO:', defaultBTO);
      // Auto-add the default BTO to the list
      setSelectedBTOs([{
        project: defaultBTO.name,
        flatType: defaultBTO.flatType,
      }]);
    }
  }, [totalBudget, defaultBTO]);



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
    if (!selectedProject || !currentFlatType) return;

    // Do not fetch price here; defer to affordability check
    setSelectedBTOs(current => [...current, {
      project: selectedProject,
      flatType: currentFlatType,
    }]);

    // Reset selections
    setSelectedProject("");
    setCurrentFlatType("");
    setError(null);
  }, [selectedProject, currentFlatType]);

  // Remove BTO
  const removeBTO = useCallback((index: number) => {
    setSelectedBTOs(current => current.filter((_, i) => i !== index));
    setResults(null); // Clear results when removing a BTO
  }, []);

  // Check affordability
  const checkAffordability = useCallback(async () => {
    if (!totalBudget) {
      setError("Please calculate your budget first before checking affordability.");
      return;
    }
    
    if (selectedBTOs.length === 0) {
      setError("Please add at least one BTO project to check affordability.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults(null);
    
    try {
      // First, get estimates for all selected BTOs
      const selections = selectedBTOs.reduce((acc: any, bto, idx) => {
        acc[`choice${idx}`] = {
          town: bto.project,
          flatType: bto.flatType,
          exerciseDate: 'October 2025',
        };
        return acc;
      }, {} as Record<string, any>);

      const estRes = await fetch('http://127.0.0.1:8000/cost_estimates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selections }),
      });
      if (!estRes.ok) throw new Error('Failed to estimate prices');
      const estJson = await estRes.json();
      const btosWithPrices = Object.values(estJson?.results || {})
        .filter((r: any) => typeof r?.estimatedPrice === 'number')
        .map((r: any) => ({
          name: r.projectLocation,
          flatType: r.flatType,
          price: r.estimatedPrice,
        }));

      if (!btosWithPrices.length) {
        throw new Error('No valid price estimates available');
      }

      // Then, run affordability against these estimates
      const response = await fetch("http://127.0.0.1:8000/affordability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          total_budget: totalBudget,
          btos: btosWithPrices,
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

  // Auto-run affordability check when we have budget and BTOs 
  useEffect(() => {
    console.log('🔍 AffordabilityCard auto-run check:', {
      totalBudget,
      selectedBTOsLength: selectedBTOs.length,
      hasResults: !!results,
      isLoading,
      hasError: !!error,
      hasAutoRun
    });
    
    // Simple condition: if we have budget and BTOs, and haven't run yet, run it
    if (totalBudget && totalBudget > 0 && selectedBTOs.length > 0 && !hasAutoRun && !isLoading) {
      console.log('🚀 AffordabilityCard: AUTO-TRIGGERING affordability check...');
      setHasAutoRun(true);
      
      // Run immediately 
      setTimeout(() => {
        checkAffordability();
      }, 100);
    }
  }, [totalBudget, selectedBTOs, hasAutoRun, isLoading, checkAffordability]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Affordability Check
          {!defaultBTO && (
            <span className="text-sm bg-blue-100 text-blue-700 px-2 py-1 rounded">
              All BTOs
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Info banner for comprehensive analysis */}
        {!defaultBTO && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-700">
              <strong>Comprehensive Analysis:</strong> Analyzing affordability for all available BTO projects and selected flat type to give you the complete picture.
            </p>
          </div>
        )}
        
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
              <Select value={currentFlatType} onValueChange={setCurrentFlatType}>
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
            disabled={!selectedProject || !currentFlatType}
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
                    <div className="text-sm text-gray-500">{bto.flatType}</div>
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
                  Running Affordability Agent
                </>
              ) : !totalBudget ? (
                'Calculate Budget First'
              ) : (
                'Check Affordability'
              )}
            </Button>
            
            {!totalBudget && (
              <p className="text-sm text-gray-500 text-center">
                Complete the budget calculation before checking affordability
              </p>
            )}
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
