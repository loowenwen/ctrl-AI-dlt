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
  
  const navigate = useNavigate();

  // Load available flat types for the selected BTO project
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
        }
      } catch (error) {
        console.error("Error loading BTO project data:", error);
        // Fallback to basic flat types if data loading fails
        setAvailableFlatTypes(["2-Room", "3-Room", "4-Room", "5-Room", "3Gen"]);
      }
    }

    if (btoProject) {
      loadProjectData();
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
  }

  const generatedText = useMemo(() => {
    if (!btoProject || !selectedFlatType || !occupant1Age || !occupant1Status) {
      return "";
    }

    let text = `I'm ${occupant1Age} years old and ${occupant1Status.toLowerCase()}. `;
    
    if (occupant2Age && occupant2Status) {
      text += `My partner is ${occupant2Age} years old and ${occupant2Status.toLowerCase()}. `;
    }
    
    text += `We're interested in a ${selectedFlatType} flat at ${btoProject}. `;
    
    if (query) {
      text += query;
    }
    
    return text;
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
      ].filter(Boolean)
    };
  }, [generatedText, btoProject, selectedFlatType, occupant1Age, occupant1Status, occupant2Age, occupant2Status]);
  
  async function onSubmit() {
    if (!btoProject || !selectedFlatType || !occupant1Age || !occupant1Status) {
      return;
    }

    navigate("/results", { 
      state: { 
        payload,
        btoProject,
        selectedFlatType 
      } 
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
      <DialogContent className="sm:max-w-lg z-[3000]">
        {/* Form */}
        <>
          <DialogHeader>
            <DialogTitle>Tell us about your plans</DialogTitle>
            <DialogDescription>
              Provide any additional details or concerns
            </DialogDescription>
          </DialogHeader>

          {/* Location row */}
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

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="mr-2" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <TealButton onClick={onSubmit}>Submit</TealButton>
          </DialogFooter>
        </>
      </DialogContent>
    </Dialog>
  )
}