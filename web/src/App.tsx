import { Route, Routes } from 'react-router-dom'
import { LiveOperations } from './pages/LiveOperations'
import { IncidentDetail } from './pages/IncidentDetail'
import { RiskMap } from './pages/RiskMap'
import { SimulatorConsole } from './pages/SimulatorConsole'
import { ComponentGallery } from './pages/ComponentGallery'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LiveOperations />} />
      {/* UX-APPFLOW.md §22. Reached from a Live Operations card's
          "Details →" affordance, not a standalone nav destination --
          Shell.tsx's own comment explains why "Incidents" stays disabled
          in the nav rail even though this route is real. */}
      <Route path="/incidents/:uuid" element={<IncidentDetail />} />
      {/* UX-APPFLOW.md §23. Nav rail destination, unlike Incident Detail. */}
      <Route path="/risk-map" element={<RiskMap />} />
      {/* UX-APPFLOW.md §25. Route exists regardless of VITE_DEMO_MODE --
          Shell.tsx only hides the nav entry point; the backend is the real
          gate (its /sim/* router isn't registered at all when
          RRX_DEMO_MODE is off, so this page's calls would just fail
          honestly rather than needing a second client-side lock). */}
      <Route path="/simulator" element={<SimulatorConsole />} />
      {/* Signature-component design-system check (UX-APPFLOW.md §7) --
          kept reachable for QA, not part of the operator-facing flow. */}
      <Route path="/gallery" element={<ComponentGallery />} />
    </Routes>
  )
}

export default App
