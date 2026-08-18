import { Route, Routes } from 'react-router-dom'
import { LiveOperations } from './pages/LiveOperations'
import { ComponentGallery } from './pages/ComponentGallery'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LiveOperations />} />
      {/* Signature-component design-system check (UX-APPFLOW.md §7) --
          kept reachable for QA, not part of the operator-facing flow. */}
      <Route path="/gallery" element={<ComponentGallery />} />
    </Routes>
  )
}

export default App
