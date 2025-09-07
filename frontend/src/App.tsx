import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom"
import Home from "./components/Home"
import Results from "./components/Results"

function App() {

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="sticky top-0 z-[2000] flex gap-4 p-4 bg-white shadow">
          <Link to="/" className="font-semibold text-lg px-3 py-2">Home</Link>
          <a
            href="https://www.hdb.gov.sg/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-lg px-3 py-2"
          >
            HDB Website
          </a>
        </nav>

        {/* Routes */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/results" element={<Results />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
