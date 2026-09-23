import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/layout/Layout';
import Landing from '@/pages/Landing';
import Workspace from '@/pages/Workspace';
import Chat from '@/pages/Chat';
import Documents from '@/pages/Documents';
import Cases from '@/pages/Cases';
import Profile from '@/pages/Profile';
import Login from '@/pages/auth/Login';
import Register from '@/pages/auth/Register';
import ForgotPassword from '@/pages/auth/ForgotPassword';
import ChangeEmail from '@/pages/auth/ChangeEmail';
import { authService } from '@/lib/authService';
import { APP_BASE } from '@/lib/appPaths';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  if (!authService.getCurrentUser()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />

      <Route path={APP_BASE} element={<Layout />}>
        <Route index element={<Workspace />} />
        <Route path="chat" element={<Chat />} />
        <Route path="documents" element={<Documents />} />
        <Route path="cases" element={<Cases />} />
        <Route
          path="profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route
          path="settings/email"
          element={
            <ProtectedRoute>
              <ChangeEmail />
            </ProtectedRoute>
          }
        />
        <Route
          path="*"
          element={
            <div className="p-8 text-center font-black text-[10px] uppercase tracking-widest text-slate-500">
              Repository path not found
            </div>
          }
        />
      </Route>

      <Route path="/chat" element={<Navigate to={`${APP_BASE}/chat`} replace />} />
      <Route path="/documents" element={<Navigate to={`${APP_BASE}/documents`} replace />} />
      <Route path="/cases" element={<Navigate to={`${APP_BASE}/cases`} replace />} />
      <Route path="/profile" element={<Navigate to={`${APP_BASE}/profile`} replace />} />
      <Route path="/settings/email" element={<Navigate to={`${APP_BASE}/settings/email`} replace />} />
    </Routes>
  );
}
