import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import LandingPage from './pages/LandingPage'

// Placeholder dashboard – will be replaced with real route later
function Dashboard() {
  return (
    <div className="min-h-screen bg-[#0a0010] flex items-center justify-center">
      <p className="text-purple-300 text-xl font-display font-semibold">
        🚧 Dashboard — Agent UI & Telemetry coming soon
      </p>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}


