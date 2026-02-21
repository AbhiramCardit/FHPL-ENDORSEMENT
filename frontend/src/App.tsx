import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import PipelineDashboard from './pages/PipelineDashboard';
import PipelineRunDetail from './pages/PipelineRunDetail';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<Navigate to="/pipelines" replace />} />
          <Route path="/pipelines" element={<PipelineDashboard />} />
          <Route path="/pipelines/:runId" element={<PipelineRunDetail />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
