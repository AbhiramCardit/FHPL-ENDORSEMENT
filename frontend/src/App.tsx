import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from 'sonner';
import { CheckCircle2, CircleAlert } from 'lucide-react';

import AppShell from '@/components/layout/AppShell';
import { AuthProvider } from '@/features/auth/AuthContext';
import { PublicOnly, RequireAuth } from '@/features/auth/route-guards';
import LoginPage from '@/pages/LoginPage';
import PipelineDashboard from '@/pages/PipelineDashboard';
import PipelineRunDetail from '@/pages/PipelineRunDetail';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route
            path="/login"
            element={(
              <PublicOnly>
                <LoginPage />
              </PublicOnly>
            )}
          />

          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<Navigate to="/pipelines" replace />} />
              <Route path="/pipelines" element={<PipelineDashboard />} />
              <Route path="/pipelines/:runId" element={<PipelineRunDetail />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
      <Toaster 
        position="bottom-right"
        icons={{
          success: <CheckCircle2 className="h-5 w-5 text-[#0f766e]" />,
          error: <CircleAlert className="h-5 w-5 text-red-600" />
        }}
        toastOptions={{
          style: {
            padding: '16px',
            fontSize: '14px',
            fontWeight: 500,
            borderRadius: '8px',
          },
          classNames: {
            toast: 'group [&[data-type="success"]]:bg-[#f0fdf4] [&[data-type="success"]]:text-[#0f766e] [&[data-type="success"]]:border [&[data-type="success"]]:border-[#a7f3d0] [&[data-type="success"]]:shadow-sm [&[data-type="error"]]:bg-red-50 [&[data-type="error"]]:text-red-700 [&[data-type="error"]]:border [&[data-type="error"]]:border-red-200 [&[data-type="error"]]:shadow-sm',
            icon: 'mr-2',
          }
        }}
      />
    </BrowserRouter>
  );
}

export default App;


