import { useMemo, useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TealButton } from "./TealButton"
import { useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"

interface BTOIntentDialogProps {
  btoProject: string | undefined;
  flatType?: string;
}

interface BTOProjectInfo {
  coordinates: string;
  properties: {
    listingType: string;
    description: Array<{
      flatType: string;
      town: string;
      stage: string;
      ballotQtr: string;
    }>;
  };
}

export default function BTOIntentDialog({ btoProject, flatType }: BTOIntentDialogProps) {
  const [open, setOpen] = useState(false);  
  const [query, setQuery] = useState<string>("");
  const [selectedFlatType, setSelectedFlatType] = useState<string>("");
  const [occupant1Age, setOccupant1Age] = useState<string>("");
  const [occupant1Status, setOccupant1Status] = useState<string>("");
  const [occupant2Age, setOccupant2Age] = useState<string>("");
  const [occupant2Status, setOccupant2Status] = useState<string>("");
  const [availableFlatTypes, setAvailableFlatTypes] = useState<string[]>([]);
  
  // Budget inputs
  const [monthlyIncome, setMonthlyIncome] = useState<string>("");
  const [cpfSavings, setCpfSavings] = useState<string>("");
  const [cashSavings, setCashSavings] = useState<string>("");
  
  // Transport inputs
  const [destinationPostal, setDestinationPostal] = useState<string>("");
  const [timePeriod, setTimePeriod] = useState<string>("");
  
  // Loading and error states
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const navigate = useNavigate();

  // Load available flat types for the selected BTO project,
  // or provide sensible defaults when no project is selected.
  useEffect(() => {
    async function loadProjectData() {
      try {
        const response = await fetch('/api/bto-data');
        const projects: BTOProjectInfo[] = await response.json();

        // Find the project that matches our btoProject name
        const project = projects.find(p =>
          p.properties.description[0].town === btoProject
        );

        if (project) {
          // Parse flat types string "2-Room Flexi, 3-Room, 4-Room" into array
          const types = project.properties.description[0].flatType
            .split(", ")
            .map(type => type.replace(" Flexi", "")); // Normalize "2-Room Flexi" to "2-Room"

          setAvailableFlatTypes(types);

          // If we have a default flatType and it's available, select it
          if (flatType && types.includes(flatType)) {
            setSelectedFlatType(flatType);
          }
        } else {
          // No specific project selected/found: show common flat types
          setAvailableFlatTypes(["2-Room", "3-Room", "4-Room", "5-Room", "3Gen"]);
        }
      } catch (error) {
        console.error("Error loading BTO project data:", error);
        // Fallback to basic flat types if data loading fails
        setAvailableFlatTypes(["2-Room", "3-Room", "4-Room", "5-Room", "3Gen"]);
      }
    }

    if (btoProject) {
      loadProjectData();
    } else {
      // If user has no BTO in mind, populate default options
      setAvailableFlatTypes(["2-Room", "3-Room", "4-Room", "5-Room", "3Gen"]);
    }
  }, [btoProject, flatType]);
  const occupantStatuses = [
    "Single",
    "Married",
    "Divorced",
    "Widowed",
    "Student",
    "Working Professional",
    "Self-Employed",
    "Retired"
  ];
;
   function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) reset()
  }

  function reset() {
    setQuery("");
    setSelectedFlatType("");
    setOccupant1Age("");
    setOccupant1Status("");
    setOccupant2Age("");
    setOccupant2Status("");
    setMonthlyIncome("");
    setCpfSavings("");
    setCashSavings("");
    setDestinationPostal("");
    setTimePeriod("");
    setIsLoading(false);
    setError(null);
  }

  const generatedText = useMemo(() => {
    let parts: string[] = [];

    if (occupant1Age || occupant1Status) {
      const age = occupant1Age ? `${occupant1Age} years old` : undefined;
      const status = occupant1Status ? occupant1Status.toLowerCase() : undefined;
      const who = [age, status].filter(Boolean).join(" and ");
      if (who) parts.push(`I'm ${who}.`);
    }

    if (occupant2Age && occupant2Status) {
      parts.push(`My partner is ${occupant2Age} years old and ${occupant2Status.toLowerCase()}.`);
    }

    if (selectedFlatType) {
      const where = btoProject ? ` at ${btoProject}` : "";
      parts.push(`We're interested in a ${selectedFlatType} flat${where}.`);
    }

    if (query) parts.push(query);

    return parts.join(" ");
  }, [btoProject, selectedFlatType, occupant1Age, occupant1Status, occupant2Age, occupant2Status, query]);

  const payload = useMemo(() => {
    return {
      text: generatedText,
      btoProject,
      flatType: selectedFlatType,
      occupants: [
        occupant1Age && occupant1Status ? {
          age: parseInt(occupant1Age),
          status: occupant1Status
        } : null,
        occupant2Age && occupant2Status ? {
          age: parseInt(occupant2Age),
          status: occupant2Status
        } : null
      ].filter(Boolean),
      budget: {
        monthlyIncome: monthlyIncome ? parseFloat(monthlyIncome) : null,
        cpfSavings: cpfSavings ? parseFloat(cpfSavings) : null,
        cashSavings: cashSavings ? parseFloat(cashSavings) : null
      },
      transport: {
        destinationPostal,
        timePeriod
      }
    };
  }, [generatedText, btoProject, selectedFlatType, occupant1Age, occupant1Status, occupant2Age, occupant2Status, monthlyIncome, cpfSavings, cashSavings, destinationPostal, timePeriod]);
  
  const isFormValid = useMemo(() => {
    // Required: at least one occupant with age and status
    const hasValidOccupant1 = occupant1Age && occupant1Status;
    
    // Required: flat type selection
    const hasValidFlatType = selectedFlatType;
    
    // Required: budget information
    const hasValidBudget = monthlyIncome && cpfSavings && cashSavings;
    
    // Required: transport information
    const hasValidTransport = destinationPostal && timePeriod;
    
    return hasValidOccupant1 && hasValidFlatType && hasValidBudget && hasValidTransport;
  }, [occupant1Age, occupant1Status, selectedFlatType, monthlyIncome, cpfSavings, cashSavings, destinationPostal, timePeriod]);
  
  async function onSubmit() {
    if (!isFormValid) return;
    
    // Navigate immediately with form data - agents will run on results page
    navigate("/results", {
      state: {
        payload,
        btoProject,
        selectedFlatType,
        formData: {
          budget: {
            monthlyIncome: parseFloat(monthlyIncome),
            cpfSavings: parseFloat(cpfSavings),
            cashSavings: parseFloat(cashSavings),
          },
          transport: btoProject && destinationPostal && timePeriod ? {
            btoProject,
            destinationPostal,
            timePeriod
          } : null
        }
      },
    });
    
    setOpen(false);
    reset();
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        { btoProject ? (
          <TealButton size="sm" className="px-2 py-2 font-xs">
            Select
          </TealButton>
        ) : (
          <TealButton className="px-4 py-6 text-lg">
            I have no BTO projects in mind
          </TealButton>
        )}
        
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg z-[3000] max-h-[90vh] flex flex-col">
        {/* Form */}
        <>
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>Complete Your BTO Analysis</DialogTitle>
            <DialogDescription>
              Fill in all required fields below. We'll analyze your budget, transportation options, and BTO affordability all at once.
            </DialogDescription>
          </DialogHeader>

          {/* Scrollable form content */}
          <div className="flex-1 overflow-y-auto space-y-4 py-2">{/* Location row */}
          { btoProject && (
              <div className="grid gap-2 pb-4">
              <Label htmlFor="location">BTO location in mind</Label>
              <Input
                id="location"
                disabled
                type="text"
                placeholder={btoProject}
                value={btoProject}
                required
              />
            </div>
          )}

          <div className="grid gap-2 pb-4">
            <Label htmlFor="flat-type">Preferred Flat Type</Label>
            <Select 
              value={selectedFlatType} 
              onValueChange={setSelectedFlatType}
            >
              <SelectTrigger className="bg-white">
                <SelectValue placeholder="Choose flat type" />
              </SelectTrigger>
                            <SelectContent position="popper" className="z-[3001]">
                {availableFlatTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Occupant 1 Details */}
          <div className="space-y-4 py-2 border-t">
            <h4 className="font-medium">First Occupant Details</h4>
            <div className="grid gap-2">
              <div className="grid gap-1.5">
                <Label htmlFor="occupant1-age">Age</Label>
                <Input
                  id="occupant1-age"
                  type="number"
                  min="21"
                  max="99"
                  placeholder="Enter age (21+)"
                  value={occupant1Age}
                  onChange={(e) => setOccupant1Age(e.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="occupant1-status">Status</Label>
                <Select 
                  value={occupant1Status} 
                  onValueChange={setOccupant1Status}
                >
                  <SelectTrigger className="bg-white">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[3001]">
                    {occupantStatuses.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Occupant 2 Details */}
          <div className="space-y-4 py-2 border-t">
            <h4 className="font-medium">Second Occupant Details (Optional)</h4>
            <div className="grid gap-2">
              <div className="grid gap-1.5">
                <Label htmlFor="occupant2-age">Age</Label>
                <Input
                  id="occupant2-age"
                  type="number"
                  min="21"
                  max="99"
                  placeholder="Enter age (21+)"
                  value={occupant2Age}
                  onChange={(e) => setOccupant2Age(e.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="occupant2-status">Status</Label>
                <Select 
                  value={occupant2Status} 
                  onValueChange={setOccupant2Status}
                >
                  <SelectTrigger className="bg-white">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[3001]">
                    {occupantStatuses.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Budget Information */}
          <div className="space-y-4 py-2 border-t">
            <h4 className="font-medium">Budget Information</h4>
            <div className="grid gap-2">
              <div className="grid gap-1.5">
                <Label htmlFor="monthly-income">Monthly Household Income *</Label>
                <Input
                  id="monthly-income"
                  type="number"
                  placeholder="e.g. 6000"
                  value={monthlyIncome}
                  onChange={(e) => setMonthlyIncome(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="cpf-savings">CPF OA Savings *</Label>
                <Input
                  id="cpf-savings"
                  type="number"
                  placeholder="e.g. 40000"
                  value={cpfSavings}
                  onChange={(e) => setCpfSavings(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="cash-savings">Cash Savings *</Label>
                <Input
                  id="cash-savings"
                  type="number"
                  placeholder="e.g. 30000"
                  value={cashSavings}
                  onChange={(e) => setCashSavings(e.target.value)}
                  required
                />
              </div>
            </div>
          </div>

          {/* Transportation Information */}
          <div className="space-y-4 py-2 border-t">
            <h4 className="font-medium">Transportation Analysis</h4>
            <div className="grid gap-2">
              <div className="grid gap-1.5">
                <Label htmlFor="destination-postal">Destination Postal Code *</Label>
                <Input
                  id="destination-postal"
                  type="text"
                  inputMode="numeric"
                  placeholder="e.g. 079903 (workplace/frequent destination)"
                  value={destinationPostal}
                  onChange={(e) => setDestinationPostal(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="time-period">Time Period *</Label>
                <Select 
                  value={timePeriod} 
                  onValueChange={setTimePeriod}
                >
                  <SelectTrigger className="bg-white">
                    <SelectValue placeholder="Select time period" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[3001]">
                    <SelectItem value="Morning Peak">Morning Peak</SelectItem>
                    <SelectItem value="Evening Peak">Evening Peak</SelectItem>
                    <SelectItem value="Daytime Off-Peak">Daytime Off-Peak</SelectItem>
                    <SelectItem value="Nighttime Off-Peak">Nighttime Off-Peak</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Query Input */}
          <div className="grid gap-2 py-4 border-t">
            <Label htmlFor="query">Additional Questions or Concerns</Label>
            <Input
              id="query"
              type="text"
              placeholder="Any specific questions about this BTO project?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          {!isFormValid && (
            <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
              <p className="font-medium mb-1">Required fields:</p>
              <ul className="text-xs space-y-1">
                {!occupant1Age && <li>• First occupant age</li>}
                {!occupant1Status && <li>• First occupant status</li>}
                {!selectedFlatType && <li>• Preferred flat type</li>}
                {!monthlyIncome && <li>• Monthly household income</li>}
                {!cpfSavings && <li>• CPF OA savings</li>}
                {!cashSavings && <li>• Cash savings</li>}
                {!destinationPostal && <li>• Destination postal code</li>}
                {!timePeriod && <li>• Travel time period</li>}
              </ul>
            </div>
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">
              {error}
            </div>
          )}

          </div> {/* End of scrollable content */}

          <DialogFooter className="gap-2 sm:gap-0 flex-shrink-0 border-t pt-4">
            <Button variant="outline" className="mr-2" onClick={() => setOpen(false)} disabled={isLoading}>
              Cancel
            </Button>
            <TealButton onClick={onSubmit} disabled={!isFormValid || isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running Analysis...
                </>
              ) : (
                'Submit'
              )}
            </TealButton>
          </DialogFooter>
        </>
      </DialogContent>
    </Dialog>
  )
}
