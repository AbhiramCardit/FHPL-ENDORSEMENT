import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../lib/api-client';

interface PipelineRunSummary {
  id: string;
  insurer_code: string;
  insurer_name: string | null;
  status: string;
  total_steps: number | null;
  steps_completed: number | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
}

const statusColors: Record<string, string> = {
  COMPLETED: 'bg-emerald-100 text-emerald-800',
  FAILED: 'bg-red-100 text-red-800',
  RUNNING: 'bg-blue-100 text-blue-800',
  PENDING: 'bg-amber-100 text-amber-800',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusColors[status] || 'bg-gray-100 text-gray-700'}`}>
      {status}
    </span>
  );
}

function formatDuration(ms: number | null): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  const secs = (ms / 1000).toFixed(1);
  return `${secs}s`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

export default function PipelineDashboard() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<PipelineRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState<string | null>(null);

  const fetchRuns = async () => {
    try {
      const res = await apiClient.getPipelineRuns({ limit: 50 });
      setRuns(res.data || []);
    } catch (err) {
      console.error('Failed to fetch runs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRuns(); }, []);

  // Auto-refresh every 5s
  useEffect(() => {
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTrigger = async () => {
    setTriggering(true);
    setTriggerResult(null);
    try {
      const res = await apiClient.triggerPipeline();
      setTriggerResult(`Pipeline triggered — ${res.execution_id}`);
      // Refresh immediately after 2s
      setTimeout(fetchRuns, 2000);
    } catch (err: any) {
      setTriggerResult(`Error: ${err.message}`);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Monitor and trigger pipeline executions</p>
        </div>
        <button
          onClick={handleTrigger}
          disabled={triggering}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#0f3460] text-white text-sm font-medium rounded-lg hover:bg-[#1a4a7a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          {triggering ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Running…
            </>
          ) : (
            <>
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1.5-5.5V7.5l5 2.5-5 2.5z" clipRule="evenodd" />
              </svg>
              Trigger ABHI Pipeline
            </>
          )}
        </button>
      </div>

      {/* Trigger result banner */}
      {triggerResult && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm font-medium ${
          triggerResult.startsWith('Error') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
        }`}>
          {triggerResult}
        </div>
      )}

      {/* Runs Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">Recent Runs</h2>
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-400">
            <svg className="animate-spin h-8 w-8 mx-auto mb-3 text-gray-300" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading…
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <p className="text-lg font-medium mb-1">No pipeline runs yet</p>
            <p className="text-sm">Click "Trigger ABHI Pipeline" to start your first run</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 text-left">
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Insurer</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Steps</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Duration</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    onClick={() => navigate(`/pipelines/${run.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <span className="font-medium text-gray-900">{run.insurer_code}</span>
                      {run.insurer_name && (
                        <span className="ml-2 text-xs text-gray-400">{run.insurer_name}</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-5 py-3.5 text-sm text-gray-600">
                      {run.steps_completed ?? 0}/{run.total_steps ?? '?'}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-gray-600 font-mono">
                      {formatDuration(run.duration_ms)}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-gray-500">
                      {formatTime(run.started_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
