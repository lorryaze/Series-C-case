import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { RequireAuth } from './components/layout/RequireAuth';
import { FeatureFlagsPage } from './pages/FeatureFlagsPage';
import { KycQueuePage } from './pages/KycQueuePage';
import { LoginPage } from './pages/LoginPage';
import { RefundsPage } from './pages/RefundsPage';

export function App(): JSX.Element {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/kyc" element={<KycQueuePage />} />
          <Route path="/refunds" element={<RefundsPage />} />
          <Route path="/feature-flags" element={<FeatureFlagsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/kyc" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
