import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './app/AppShell';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
      <Route path="/app/*" element={<AppShell />} />
      <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
    </Routes>
  );
}
