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
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select"
import { TealButton } from "./TealButton"
import { useNavigate } from "react-router-dom"

interface BTOIntentDialogProps {
  btoProject: string | undefined
}

export default function BTOIntentDialog({ btoProject }: BTOIntentDialogProps) {
  const [open, setOpen] = useState(false);
  const [deferred, setDeferred] = useState(false);
  
  const [income, setIncome] = useState<string>("");
  const [cpf, setCpf] = useState<string>("");
  const [cash, setCash] = useState<string>("");
  const [flatType, setFlatType] = useState<string>("");

  const navigate = useNavigate();
;
   function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) reset()
  }

  function reset() {
    setDeferred(false);
    setIncome("");
    setCpf("");
    setCash("");
    setFlatType("");
  }

  const sentence = useMemo(() => {
    const parts: string[] = [];
    if (btoProject) parts.push(`Location: ${btoProject}`);
    if (deferred) {
      parts.push("Deferred income assessment selected");
    } else {
      if (income) parts.push(`Income: ${income}`);
      if (cpf) parts.push(`CPF savings: ${cpf}`);
      if (cash) parts.push(`Cash savings: ${cash}`);
      if (!btoProject && flatType) parts.push(`Flat type: ${flatType}`);
    }
    return (parts.join(". ") + (parts.length ? "." : "")).trim() || "No details provided.";
  }, [location, deferred, income, cpf, cash, flatType, btoProject]);
  
  async function onSubmit() {
    const payload = { text: sentence };

    navigate("/results", { state: { payload } });
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
              Choose whether to defer income assessment or provide your current details.
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

          {/* Checkbox row */}
          <div className="flex items-center gap-3">
            <Checkbox
              id="deferred"
              checked={deferred}
              className="cursor-pointer"
              onCheckedChange={(v) => setDeferred(Boolean(v))}
            />
            <Label htmlFor="deferred" className="cursor-pointer">
              Deferred income assessment
            </Label>
          </div>

          {/* Conditional fields (only when NOT deferred) */}
          {!deferred && (
            <div className="grid gap-4 pt-2">
              <div className="grid gap-2">
                <Label htmlFor="income">Monthly income (SGD)</Label>
                <Input
                  id="income"
                  type="number"
                  min={0}
                  placeholder="e.g. 5000"
                  value={income}
                  onChange={(e) => setIncome(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="cpf">CPF savings (SGD)</Label>
                <Input
                  id="cpf"
                  type="number"
                  min={0}
                  placeholder="e.g. 30000"
                  value={cpf}
                  onChange={(e) => setCpf(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="cash">Cash savings (SGD)</Label>
                <Input
                  id="cash"
                  type="number"
                  min={0}
                  placeholder="e.g. 20000"
                  value={cash}
                  onChange={(e) => setCash(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label>Flat type preference</Label>
                <Select value={flatType} onValueChange={setFlatType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a flat type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2-room">2-Room Flexi</SelectItem>
                    <SelectItem value="3-room">3-Room</SelectItem>
                    <SelectItem value="4-room">4-Room</SelectItem>
                    <SelectItem value="5-room">5-Room</SelectItem>
                    <SelectItem value="executive">3Gen flats</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

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