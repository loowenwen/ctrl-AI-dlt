import { useMemo, useRef, useState } from "react"
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
import LoadingView, { type LoadingPhase } from "@/components/LoadingView"

interface BTOIntentDialogProps {
  hasLocation: boolean
}

type DialogPhase = "form" | LoadingPhase;

export default function BTOIntentDialog({ hasLocation }: BTOIntentDialogProps) {
  const [open, setOpen] = useState(false);
  const [phase, setPhase] = useState<DialogPhase>("form");
  const [deferred, setDeferred] = useState(false);
  
  const [location, setLocation] = useState<string>("");
  const [income, setIncome] = useState<string>("");
  const [cpf, setCpf] = useState<string>("");
  const [cash, setCash] = useState<string>("");
  const [flatType, setFlatType] = useState<string>("");

  const [apiData, setApiData] = useState<any>(null)
  const [apiError, setApiError] = useState<string | null>(null)

  const navigate = useNavigate();
  const abortRef = useRef<AbortController | null>(null)

   function handleOpenChange(next: boolean) {
    if (phase === "loading" && !next) return
    setOpen(next)
    if (!next) reset()
  }

  function reset() {
    setPhase("form")
    setDeferred(false)
    setLocation("")
    setIncome("")
    setCpf("")
    setCash("")
    setFlatType("")
    setApiData(null)
    setApiError(null)
    abortRef.current?.abort()
    abortRef.current = null
  }

  const sentence = useMemo(() => {
    const parts: string[] = []
    if (location.trim()) parts.push(`Location: ${location}`)
    if (deferred) {
      parts.push("Deferred income assessment selected")
    } else {
      if (income) parts.push(`Income: ${income}`)
      if (cpf) parts.push(`CPF savings: ${cpf}`)
      if (cash) parts.push(`Cash savings: ${cash}`)
      if (!hasLocation && flatType) parts.push(`Flat type: ${flatType}`)
    }
    return (parts.join(". ") + (parts.length ? "." : "")).trim() || "No details provided."
  }, [location, deferred, income, cpf, cash, flatType, hasLocation])
  
  async function onSubmit() {
    setPhase("loading")
    setApiError(null)

    const payload = { text: sentence }

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await fetch("https://ituhr6ycktc3r2yvoiiq3igs3q0ebbts.lambda-url.us-east-1.on.aws/", {
        method: "POST",
        body: JSON.stringify(payload),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      const data = await res.json()
      setApiData(data)
      setPhase("done")
    } catch (err: any) {
      if (err?.name === "AbortError") return
      setApiError(err?.message || "Unknown error")
      setPhase("error")
    } finally {
      abortRef.current = null
    }
  }

  function toResults() {
    if (!apiData) return
    navigate("/results", { state: { data: apiData } })
    setOpen(false)
    reset()
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <TealButton className="px-10 py-6 text-lg">
          { hasLocation? "I have BTOs in mind" : "I have no BTOs in mind" }
        </TealButton>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        {/* Form */}
        { phase === "form" && (
          <>
            <DialogHeader>
              <DialogTitle>Tell us about your plans</DialogTitle>
              <DialogDescription>
                Choose whether to defer income assessment or provide your current details.
              </DialogDescription>
            </DialogHeader>

            {/* Location row */}
            { hasLocation && (
                <div className="grid gap-2 pb-4">
                <Label htmlFor="location">BTO location in mind</Label>
                <Input
                  id="location"
                  type="text"
                  placeholder="e.g. Toa Payoh"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
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
        )}

        {/* Loading Screen */}
        {phase !== "form" && (
          <LoadingView
            phase={phase as Exclude<DialogPhase, "form">}
            sentence={sentence}
            onCancel={() => {
              abortRef.current?.abort();
              setPhase("error");
              setApiError("Cancelled by user");
            }}
            onViewReport={toResults}
            errorMessage={apiError ?? undefined}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}