import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

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
    </BrowserRouter>
  );
}

export default App;
