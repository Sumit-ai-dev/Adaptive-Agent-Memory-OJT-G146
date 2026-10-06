import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'
import AgentWorkspacePage from './pages/AgentWorkspacePage'
import AgentMemoryPage from './pages/AgentMemoryPage'
import AgentRunsPage from './pages/AgentRunsPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Landing & Authentication */}
          <Route path="/" element={<LandingPage />} />

          {/* Authenticated Product Workspace */}
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/agent" element={<AgentWorkspacePage />} />
          <Route path="/agent/chat" element={<AgentWorkspacePage />} />
          <Route path="/agent/memory" element={<AgentMemoryPage />} />
          <Route path="/agent/runs" element={<AgentRunsPage />} />

          {/* Catch-all redirect to landing */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
