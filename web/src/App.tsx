import { Route, Routes } from 'react-router-dom'
import { LiveOperations } from './pages/LiveOperations'
import { IncidentDetail } from './pages/IncidentDetail'
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
      {/* Signature-component design-system check (UX-APPFLOW.md §7) --
          kept reachable for QA, not part of the operator-facing flow. */}
      <Route path="/gallery" element={<ComponentGallery />} />
    </Routes>
  )
}

export default App
