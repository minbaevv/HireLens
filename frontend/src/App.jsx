import { Routes, Route, Navigate } from 'react-router-dom'
import { LanguageProvider } from './i18n'
import { useAuth } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import DashboardPage from './pages/DashboardPage'
import JobsPage from './pages/JobsPage'
import JobDetailPage from './pages/JobDetailPage'
import CandidatesPage from './pages/CandidatesPage'
import CandidateDetailPage from './pages/CandidateDetailPage'
import KanbanPage from './pages/KanbanPage'
import AnalyticsPage from './pages/AnalyticsPage'
import CopilotPage from './pages/CopilotPage'
import BillingPage from './pages/BillingPage'
import AdminPage from './pages/AdminPage'
import TeamPage from './pages/TeamPage'
import IntegrationsPage from './pages/IntegrationsPage'
import BiasReportPage from './pages/BiasReportPage'
import AcceptInvitePage from './pages/AcceptInvitePage'
import ApplyPage from './pages/ApplyPage'
import InterviewPage from './pages/InterviewPage'
import LandingPage from './pages/LandingPage'
import CodingPage from './pages/CodingPage'
import CodingChallengePage from './pages/CodingChallengePage'
import AuditLogPage from './pages/AuditLogPage'
import CareersPage from './pages/CareersPage'
import Layout from './components/Layout'

function PrivateRoute({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/landing" replace />
}

export default function App() {
  return (
    <LanguageProvider>
    <Routes>
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/apply/:token" element={<ApplyPage />} />
      <Route path="/team/accept" element={<AcceptInvitePage />} />
      <Route path="/interview/:interviewId" element={<InterviewPage />} />
      <Route path="/coding/:token" element={<CodingChallengePage />} />
      <Route path="/careers/:companyId" element={<CareersPage />} />
      <Route path="/" element={
        <PrivateRoute>
          <Layout />
        </PrivateRoute>
      }>
        <Route index element={<DashboardPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailPage />} />
        <Route path="candidates" element={<CandidatesPage />} />
        <Route path="candidates/:id" element={<CandidateDetailPage />} />
        <Route path="kanban" element={<KanbanPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="copilot" element={<CopilotPage />} />
        <Route path="team" element={<TeamPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="coding" element={<CodingPage />} />
        <Route path="governance" element={<BiasReportPage />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="audit" element={<AuditLogPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </LanguageProvider>
  )
}
