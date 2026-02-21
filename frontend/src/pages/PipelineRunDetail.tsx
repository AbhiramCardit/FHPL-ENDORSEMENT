import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../lib/api-client';

interface StepLog {
  id: string;
  step_index: number;
  step_name: string;
  step_description: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  metadata: Record<string, any> | null;
  retry_count: number;
}

interface PipelineFileInfo {
  id: string;
  file_id: string;
  filename: string;
  role: string;
  detected_format: string | null;
  record_count: number;
  status: string;
  error_message: string | null;
}

interface ExtractedData {
  id: string;
  source_role: string;
  extraction_method: string;
  llm_model: string | null;
  raw_data: any;
  data: any;
  created_at: string | null;
}

interface RunDetail {
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
  config_snapshot: any;
  context_summary: any;
  steps: StepLog[];
  files: PipelineFileInfo[];
  extracted_data: ExtractedData[];
}

const statusColors: Record<string, string> = {
  COMPLETED: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  FAILED: 'bg-red-100 text-red-800 border-red-200',
  RUNNING: 'bg-blue-100 text-blue-800 border-blue-200',
  PENDING: 'bg-amber-100 text-amber-800 border-amber-200',
  SKIPPED: 'bg-gray-100 text-gray-600 border-gray-200',
};

const stepDotColors: Record<string, string> = {
  COMPLETED: 'bg-emerald-500',
  FAILED: 'bg-red-500',
  RUNNING: 'bg-blue-500 animate-pulse',
  PENDING: 'bg-gray-300',
  SKIPPED: 'bg-gray-300',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${statusColors[status] || 'bg-gray-100 text-gray-700 border-gray-200'}`}>
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

function CollapsibleJson({ label, data }: { label: string; data: any }) {
  const [open, setOpen] = useState(false);

  if (!data || (typeof data === 'object' && Object.keys(data).length === 0)) {
    return null;
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-sm font-medium text-gray-700"
      >
        <span>{label}</span>
        <svg className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>
      {open && (
        <pre className="px-4 py-3 text-xs text-gray-700 bg-gray-50/50 overflow-x-auto max-h-96 font-mono leading-relaxed">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function PipelineRunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    const fetchRun = async () => {
      try {
        const res = await apiClient.getPipelineRun(runId);
        setRun(res);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchRun();
    // Auto-refresh if RUNNING
    const interval = setInterval(fetchRun, 5000);
    return () => clearInterval(interval);
  }, [runId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <svg className="animate-spin h-8 w-8 text-gray-300" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="p-8 text-center">
        <p className="text-red-500 font-medium">Failed to load run: {error || 'Not found'}</p>
        <button onClick={() => navigate('/pipelines')} className="mt-4 text-sm text-blue-600 underline">← Back to pipelines</button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Back + Header */}
      <button
        onClick={() => navigate('/pipelines')}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-flex items-center gap-1 transition-colors"
      >
        <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
        </svg>
        Back to Dashboard
      </button>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-bold text-gray-900">{run.insurer_code}</h1>
              <StatusBadge status={run.status} />
            </div>
            {run.insurer_name && <p className="text-sm text-gray-500">{run.insurer_name}</p>}
          </div>
          <div className="text-right text-sm text-gray-500 space-y-1">
            <p>Started: <span className="text-gray-700 font-medium">{formatTime(run.started_at)}</span></p>
            <p>Completed: <span className="text-gray-700 font-medium">{formatTime(run.completed_at)}</span></p>
            <p>Duration: <span className="text-gray-900 font-mono font-semibold">{formatDuration(run.duration_ms)}</span></p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>Steps: {run.steps_completed ?? 0} / {run.total_steps ?? '?'}</span>
            {run.total_steps && <span>{Math.round(((run.steps_completed ?? 0) / run.total_steps) * 100)}%</span>}
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${run.status === 'FAILED' ? 'bg-red-500' : run.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-blue-500'}`}
              style={{ width: `${run.total_steps ? ((run.steps_completed ?? 0) / run.total_steps) * 100 : 0}%` }}
            />
          </div>
        </div>

        {run.error_message && (
          <div className="mt-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            <span className="font-semibold">Error: </span>{run.error_message}
          </div>
        )}
      </div>

      {/* Steps Timeline */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Steps Timeline</h2>
        <div className="space-y-0">
          {run.steps.map((step, i) => (
            <div key={step.id} className="flex gap-4">
              {/* Timeline dot + line */}
              <div className="flex flex-col items-center">
                <div className={`w-3 h-3 rounded-full mt-1.5 ${stepDotColors[step.status] || 'bg-gray-300'}`} />
                {i < run.steps.length - 1 && <div className="w-px flex-1 bg-gray-200 my-1" />}
              </div>

              {/* Step content */}
              <div className={`flex-1 pb-5 ${i < run.steps.length - 1 ? '' : ''}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">{step.step_name}</span>
                    <StatusBadge status={step.status} />
                  </div>
                  <span className="text-xs text-gray-400 font-mono">{formatDuration(step.duration_ms)}</span>
                </div>
                {step.step_description && (
                  <p className="text-xs text-gray-500 mt-0.5">{step.step_description}</p>
                )}
                {step.error_message && (
                  <p className="text-xs text-red-600 mt-1 bg-red-50 px-2 py-1 rounded">{step.error_message}</p>
                )}
                {step.metadata && Object.keys(step.metadata).length > 0 && (
                  <div className="mt-2">
                    <CollapsibleJson label="Step Metadata" data={step.metadata} />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Files */}
      {run.files.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Processed Files</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left">
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Filename</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Role</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Format</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Records</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {run.files.map((f) => (
                  <tr key={f.id}>
                    <td className="px-4 py-2.5 font-medium text-gray-900 truncate max-w-[250px]">{f.filename}</td>
                    <td className="px-4 py-2.5">
                      <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">{f.role}</span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600 font-mono text-xs">{f.detected_format || '—'}</td>
                    <td className="px-4 py-2.5 text-gray-600">{f.record_count}</td>
                    <td className="px-4 py-2.5"><StatusBadge status={f.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Extracted Data */}
      {run.extracted_data.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Extracted Data</h2>
          <div className="space-y-4">
            {run.extracted_data.map((ed) => (
              <div key={ed.id} className="border border-gray-100 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">{ed.source_role}</span>
                  <span className="text-xs text-gray-500">via {ed.extraction_method}</span>
                  {ed.llm_model && <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded">{ed.llm_model}</span>}
                  <span className="text-xs text-gray-400 ml-auto">{formatTime(ed.created_at)}</span>
                </div>
                <div className="space-y-2">
                  <CollapsibleJson label={`Raw Data (${ed.source_role})`} data={ed.raw_data} />
                  <CollapsibleJson label={`Processed Data (${ed.source_role})`} data={ed.data} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Context Summary */}
      <CollapsibleJson label="Context Summary" data={run.context_summary} />
    </div>
  );
}
