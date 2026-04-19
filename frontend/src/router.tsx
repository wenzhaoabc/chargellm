import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { getAdminToken } from '@/api/admin'
import { AppShell } from '@/components/AppShell'
import { AdminLoginPage } from '@/pages/AdminLoginPage'
import { AdminPage } from '@/pages/AdminPage'
import { ChatPage } from '@/pages/ChatPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { LandingPage } from '@/pages/LandingPage'
import { RecordsPage } from '@/pages/RecordsPage'

function AdminRoute() {
  return getAdminToken() ? <AdminPage /> : <AdminLoginPage />
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin" element={<AdminRoute />} />
        <Route element={<AppShell />}>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/records" element={<RecordsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
