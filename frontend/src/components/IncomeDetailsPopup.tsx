import { useMemo, useState } from "react"
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
import { TealButton } from "./TealButton"
import { useNavigate } from "react-router-dom"

interface BTOIntentDialogProps {
  btoProject: string | undefined
}

export default function BTOIntentDialog({ btoProject }: BTOIntentDialogProps) {
  const [open, setOpen] = useState(false);  
  const [query, setQuery] = useState<string>("");

  const navigate = useNavigate();
;
   function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) reset()
  }

  function reset() {
    setQuery("");
  }

  const sentence = useMemo(() => {
    const parts: string[] = [];
    if (btoProject) {
      parts.push(`Sentiment analysis on BTO Project: ${btoProject}`);
    }
    if (query) {
      parts.push(`Query: ${query}`);
    } 
    return (parts.join(". ") + (parts.length ? "." : "")).trim() || "No details provided.";
  }, [btoProject, query]);
  
  async function onSubmit() {
    const payload = { text: sentence };

    navigate("/results", { state: { payload, btoProject } });
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
            <Label htmlFor="query">Enter any additional queries</Label>
            <Input
              id="query"
              type="text"
              placeholder="Enter your questions or concerns"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
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