import { Routes, Route } from 'react-router-dom';
import CyberShell from './components/layout/CyberShell.jsx';
import Overview from './pages/Overview.jsx';
import NetworkPage from './pages/NetworkPage.jsx';
import ForecastPage from './pages/ForecastPage.jsx';
import AttackPathPage from './pages/AttackPathPage.jsx';
import TelemetryPage from './pages/TelemetryPage.jsx';
import ExplainabilityPage from './pages/ExplainabilityPage.jsx';
import IncidentsPage from './pages/IncidentsPage.jsx';
import ModelPage from './pages/ModelPage.jsx';

export default function App() {
  return (
    <CyberShell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/network" element={<NetworkPage />} />
        <Route path="/forecast" element={<ForecastPage />} />
        <Route path="/attack-path" element={<AttackPathPage />} />
        <Route path="/telemetry" element={<TelemetryPage />} />
        <Route path="/explainability" element={<ExplainabilityPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/model" element={<ModelPage />} />
      </Routes>
    </CyberShell>
  );
}
