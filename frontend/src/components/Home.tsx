import { useEffect, useMemo, useState } from "react"
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet"
import L from "leaflet"
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select"
import IncomeDetailsPopup from "./IncomeDetailsPopup";
import { Separator } from "./ui/separator";

function makePin(color = "#0ea5a8") {
  const svg = `
  <svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
        <feDropShadow dx="0" dy="1.5" stdDeviation="1.5" flood-color="rgba(0,0,0,0.35)"/>
      </filter>
    </defs>
    <!-- Teardrop pin -->
    <path filter="url(#shadow)"
      d="M24 4c-7.18 0-13 5.82-13 13 0 9.75 11.14 21.67 12.35 22.95a1 1 0 0 0 1.3 0C25.86 38.67 37 26.75 37 17 37 9.82 31.18 4 24 4z"
      fill="${color}" stroke="white" stroke-width="3" />
    <!-- Inner white circle -->
    <circle cx="24" cy="19" r="8" fill="white"/>
    <!-- House glyph -->
    <path d="M19 22v-3.2l5-3.8 5 3.8V22h-3.2v-2.4H22.2V22H19z"
      fill="${color}" />
  </svg>`;
  return L.icon({
    iconUrl: "data:image/svg+xml;utf8," + encodeURIComponent(svg),
    iconSize: [50, 50], 
    iconAnchor: [20, 40],   
    popupAnchor: [0, -36],   
  });
}

const housePin = makePin("#cc0202");

type FlatType = "2-Room" | "3-Room" | "4-Room" | "5-Room" | "3Gen"
type Listing = {
  id: string
  name: string
  town: string
  flatTypes: FlatType[]
  lat: number
  lng: number
  region?: string
  stage?: string
  ballotQtr?: string
}

function normalizeFlatTypes(s: string | undefined): FlatType[] {
  if (!s) return []
  return s
    .split(",")
    .map(t => t.trim())
    .map(t => {
      if (/^2[-\s]?room/i.test(t)) return "2-Room Flexi"
      if (/^3[-\s]?room/i.test(t)) return "3-Room"
      if (/^4[-\s]?room/i.test(t)) return "4-Room"
      if (/^5[-\s]?room/i.test(t)) return "5-Room"
      if (/executive/i.test(t)) return "Executive"
      return t as FlatType
    })
    .filter((t, i, a) => a.indexOf(t) === i)
    .filter((t): t is FlatType =>
      ["2-Room Flexi","3-Room","4-Room","5-Room","Executive"].includes(t)
    )
}

export default function Home() {
  const [allListings, setAllListings] = useState<Listing[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flatFilter, setFlatFilter] = useState<FlatType | "all">("all")
  
  useEffect(() => {
    let isMounted = true
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        const res = await fetch(`http://127.0.0.1:8000/bto_listings`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as Array<{
          lat: number; lng: number; town: string; flatType: string;
          projectId?: string; region?: string; stage?: string; ballotQtr?: string
        }>

        if (!isMounted) return
        const mapped: Listing[] = data.map((d, idx) => ({
          id: d.projectId || `bto-${idx}`,
          name: d.town || "BTO Project",
          town: d.town || "",
          flatTypes: normalizeFlatTypes(d.flatType),
          lat: d.lat, lng: d.lng,
          region: d.region,
          stage: d.stage,
          ballotQtr: d.ballotQtr,
        }))
        setAllListings(mapped)
      } catch (e: any) {
        if (!isMounted) return
        setError(e?.message || "Failed to load listings")
      } finally {
        if (isMounted) setLoading(false)
      }
    })()
    return () => { isMounted = false }
  }, [])

  const filtered = useMemo(() => {
    if (flatFilter === "all") return allListings
    return allListings.filter(l => l.flatTypes.includes(flatFilter))
  }, [allListings, flatFilter])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Heading top-left under navbar */}
      <div className="mx-auto max-w-6xl px-4 pt-8">
        <h1 className="text-4xl md:text-6xl font-extrabold text-gray-800">
          Let's <span className="text-teal-700 drop-shadow">BTO</span><span className="font-semibold">gether</span>
        </h1>
        <p className="mt-2 text-gray-600">
          Agentic website to find the ⭐ best ⭐ BTO choice for you.
        </p>

        {/* Filters row */}
        <div className="z-0 mt-6 flex flex-wrap items-center gap-3">
          <label className="text-sm text-gray-700">Flat type</label>
          <Select value={flatFilter} onValueChange={(v) => setFlatFilter(v as any)}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="All" />
            </SelectTrigger>
            <SelectContent className="z-[1000]">
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="2-Room Flexi">2-Room Flexi</SelectItem>
              <SelectItem value="3-Room">3-Room</SelectItem>
              <SelectItem value="4-Room">4-Room</SelectItem>
              <SelectItem value="5-Room">5-Room</SelectItem>
              <SelectItem value="3Gen">3Gen</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Map in the middle */}
      <div className="mx-auto max-w-6xl px-4 py-6">
        <label className="text-m text-gray-700">Select BTO location from map</label>
        <Separator className="mt-2" />
        <div className="rounded-xl mt-4 overflow-hidden border shadow-sm">
          <MapContainer
            center={[1.335, 103.85]}    // SG-ish center; set to fit your data
            zoom={13}
            scrollWheelZoom={true}
            style={{ height: "65vh", width: "100%" }}  // “middle” big map
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {loading && <div className="p-4 text-sm text-gray-600">Loading listings…</div>}
            {error && <div className="p-4 text-sm text-rose-600">Error: {error}</div>}

            {filtered.map(l => (
              <Marker key={l.id} position={[l.lat, l.lng]} icon={housePin}>
                <Popup>
                  <div className="space-y-1">
                    <div className="font-semibold flex items-center gap-2">
                      {l.name}
                      <IncomeDetailsPopup btoProject={l.name}/>
                    </div>
                    <div className="text-xs text-gray-600">{l.town}</div>
                    <div className="text-xs">
                      Flat types: <span className="font-medium">{l.flatTypes.join(", ")}</span>
                    </div>
                    {l.stage && <div className="text-xs">Stage: <span className="font-medium">{l.stage}</span></div>}
                    {l.ballotQtr && <div className="text-xs">Ballot Qtr: <span className="font-medium">{l.ballotQtr}</span></div>}
                    {l.region && <div className="text-xs text-gray-600">{l.region}</div>}
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 py-6">
        <IncomeDetailsPopup btoProject={undefined}/>
      </div>
    </div>
  )
}