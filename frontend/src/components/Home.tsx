import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import IncomeDetailsPopup from "./IncomeDetailsPopup";

export default function Home() {
  return (
    <div className="flex flex-col items-center min-h-screen bg-gray-50 p-6">
      {/* Title */}
      <h1 className="mt-36 text-center text-7xl md:text-8xl font-semibold text-gray-800 text-shadow-md">
        Let's{" "}
        <span className="text-8xl ml-2 md:text-9xl font-extrabold tracking-wide text-[#1f8088] text-shadow-md">
          BTO
        </span>
        <span className="font-semibold text-gray-700 text-shadow-md">gether</span>
      </h1>
      <p className="mt-4 text-center text-lg md:text-2xl text-gray-600 max-w-2xl">
        Agentic website to find the ⭐ best ⭐ BTO choice for you.
      </p>

      {/* Buttons section */}
      <div className="mt-16 flex flex-col items-center gap-6">
        {/* Top row: 2 buttons side by side */}
        <div className="flex gap-6">
          <IncomeDetailsPopup hasLocation={true}/>
          <IncomeDetailsPopup hasLocation={false}/>
        </div>

        {/* Bottom button */}
        <Link to="/visualise">
          <Button
            size="lg"
            className="px-10 py-6 text-lg bg-[#cc0202] hover:bg-red-700 text-white"
          >
            Visualise my BTO
          </Button>
        </Link>
      </div>
    </div>
  );
}