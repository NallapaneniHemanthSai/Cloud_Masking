import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Models } from './pages/Models';
import { Predict } from './pages/Predict';
import { Evaluate } from './pages/Evaluate';
import { Comparison } from './pages/Comparison';
import { Upload } from './pages/Upload';
import { History } from './pages/History';
import { Metrics } from './pages/Metrics';
import { MapViewer } from './pages/MapViewer';
import { SystemHealth } from './pages/SystemHealth';
import { Status } from './pages/Status';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="models" element={<Models />} />
        <Route path="predict" element={<Predict />} />
        <Route path="evaluate" element={<Evaluate />} />
        <Route path="comparison" element={<Comparison />} />
        <Route path="upload" element={<Upload />} />
        <Route path="history" element={<History />} />
        <Route path="metrics" element={<Metrics />} />
        <Route path="map" element={<MapViewer />} />
        <Route path="status" element={<Status />} />
        <Route path="system" element={<SystemHealth />} />
        <Route path="*" element={<div className="page"><h1>Not found</h1></div>} />
      </Route>
    </Routes>
  );
}
