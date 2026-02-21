import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ChevronDown, CircleAlert, Clock3, FileText, ListChecks, RefreshCw } from 'lucide-react';
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
  metadata: Record<string, unknown> | null;
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
  raw_data: unknown;
  data: unknown;
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
  config_snapshot: unknown;
  context_summary: unknown;
  created_at?: string | null;
  updated_at?: string | null;
  steps: StepLog[];
  files: PipelineFileInfo[];
  extracted_data: ExtractedData[];
}

const ACTIVE_RUN_STATUSES = new Set(['PENDING', 'RUNNING']);

const statusColors: Record<string, string> = {
  COMPLETED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  FAILED: 'bg-red-50 text-red-700 border-red-200',
  RUNNING: 'bg-blue-50 text-blue-700 border-blue-200',
  PENDING: 'bg-amber-50 text-amber-700 border-amber-200',
  SKIPPED: 'bg-gray-100 text-gray-600 border-gray-200',
  RETRYING: 'bg-orange-50 text-orange-700 border-orange-200',
  PARTIALLY_COMPLETED: 'bg-yellow-50 text-yellow-700 border-yellow-200',
};

const stepCardStyles: Record<string, string> = {
  COMPLETED: 'border-emerald-100',
  FAILED: 'border-red-200 bg-red-50/40',
  RUNNING: 'border-blue-200 bg-blue-50/30',
  PENDING: 'border-gray-200 bg-gray-50/60',
  SKIPPED: 'border-gray-200',
  RETRYING: 'border-orange-200 bg-orange-50/30',
};

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ');
}

function formatDuration(ms: number | null): string {
  if (ms == null) return '--';
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`;
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '--';
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function isEmptyData(data: unknown): boolean {
  if (data == null) return true;
  if (Array.isArray(data)) return data.length === 0;
  if (typeof data === 'object') return Object.keys(data as Record<string, unknown>).length === 0;
  return false;
}

function safeJsonStringify(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return 'Unable to render JSON payload';
  }
}

function StatusBadge({ status, compact = false }: { status: string; compact?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border font-semibold tracking-wide ${
        compact ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'
      } ${statusColors[status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}
    >
      {formatStatus(status)}
    </span>
  );
}

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50/70 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">{label}</p>
      <div className="mt-1 flex items-end justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900">{value}</p>
        {hint && <p className="text-[11px] font-medium text-gray-500">{hint}</p>}
      </div>
    </div>
  );
}

function SectionCard({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
        </div>
        {actions}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

function JsonPanel({
  label,
  data,
  defaultOpen = false,
}: {
  label: string;
  data: unknown;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  if (isEmptyData(data)) {
    return null;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 bg-gray-50/70 px-3 py-2 text-left text-xs font-semibold text-gray-700 hover:bg-gray-100"
      >
        <span>{label}</span>
        <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <pre className="max-h-72 overflow-auto border-t border-gray-100 bg-gray-50/40 p-3 text-[11px] leading-relaxed text-gray-700">
          {safeJsonStringify(data)}
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
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);
  const runStatus = run?.status;

  const fetchRun = useCallback(async () => {
    if (!runId) return;

    try {
      const response = await apiClient.getPipelineRun(runId);
      setRun(response as RunDetail);
      setError(null);
      setLastRefreshAt(new Date().toISOString());
    } catch (fetchError: unknown) {
      const message = fetchError instanceof Error ? fetchError.message : 'Failed to fetch pipeline run';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    void fetchRun();
  }, [fetchRun]);

  useEffect(() => {
    if (!runStatus || !ACTIVE_RUN_STATUSES.has(runStatus)) return;
    const intervalId = window.setInterval(() => {
      void fetchRun();
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [fetchRun, runStatus]);

  const metrics = useMemo(() => {
    if (!run) {
      return {
        totalSteps: 0,
        completedSteps: 0,
        failedSteps: 0,
        progressPercent: 0,
        totalFiles: 0,
        totalRecords: 0,
      };
    }

    const totalSteps = run.total_steps ?? run.steps.length;
    const completedSteps = run.steps_completed ?? run.steps.filter((step) => step.status === 'COMPLETED').length;
    const failedSteps = run.steps.filter((step) => step.status === 'FAILED').length;
    const progressPercent = totalSteps > 0 ? Math.min(100, Math.round((completedSteps / totalSteps) * 100)) : 0;
    const totalFiles = run.files.length;
    const totalRecords = run.files.reduce((sum, file) => sum + file.record_count, 0);

    return {
      totalSteps,
      completedSteps,
      failedSteps,
      progressPercent,
      totalFiles,
      totalRecords,
    };
  }, [run]);

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-6xl items-center justify-center px-4">
        <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-600 shadow-sm">
          <RefreshCw className="h-4 w-4 animate-spin text-gray-500" />
          Loading pipeline run details...
        </div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center">
        <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          Failed to load run details: {error || 'Not found'}
        </div>
        <button
          type="button"
          onClick={() => navigate('/pipelines')}
          className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to pipeline dashboard
        </button>
      </div>
    );
  }

  const progressBarColor =
    run.status === 'FAILED'
      ? 'bg-red-500'
      : run.status === 'COMPLETED'
        ? 'bg-emerald-500'
        : run.status === 'PARTIALLY_COMPLETED'
          ? 'bg-yellow-500'
          : 'bg-blue-500';

  const sortedSteps = [...run.steps].sort((a, b) => a.step_index - b.step_index);

  return (
    <div className="mx-auto min-h-screen max-w-[1200px] space-y-4 px-4 py-4 md:px-6 md:py-6">
      <button
        type="button"
        onClick={() => navigate('/pipelines')}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600 transition-colors hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to pipeline dashboard
      </button>

      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm md:p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-semibold text-gray-900">{run.insurer_code}</h1>
              <StatusBadge status={run.status} />
              {ACTIVE_RUN_STATUSES.has(run.status) && (
                <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                  LIVE
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-600">{run.insurer_name || 'Insurer name unavailable'}</p>
            <p className="mt-1 font-mono text-[11px] text-gray-500">Run ID: {run.id}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void fetchRun()}
              className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </button>
            {lastRefreshAt && <span className="text-[11px] font-medium text-gray-500">Updated {formatTime(lastRefreshAt)}</span>}
          </div>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            label="Progress"
            value={`${metrics.completedSteps}/${metrics.totalSteps || 0}`}
            hint={`${metrics.progressPercent}%`}
          />
          <MetricCard label="Failed Steps" value={`${metrics.failedSteps}`} />
          <MetricCard label="Duration" value={formatDuration(run.duration_ms)} />
          <MetricCard label="Files Processed" value={`${metrics.totalFiles}`} />
          <MetricCard label="Records Extracted" value={`${metrics.totalRecords}`} />
        </div>

        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-[11px] font-medium text-gray-500">
            <span>Execution progress</span>
            <span>{metrics.progressPercent}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-gray-100">
            <div className={`h-full rounded-full transition-all ${progressBarColor}`} style={{ width: `${metrics.progressPercent}%` }} />
          </div>
        </div>

        {run.error_message && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Execution error</p>
              <p className="mt-0.5 leading-relaxed">{run.error_message}</p>
            </div>
          </div>
        )}
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.7fr_1fr]">
        <div className="space-y-4">
          <SectionCard
            title="Execution Steps"
            subtitle={`${sortedSteps.length} steps with timing, retry, and error diagnostics`}
            actions={
              <div className="inline-flex items-center gap-1 text-xs text-gray-500">
                <ListChecks className="h-3.5 w-3.5" />
                compact timeline
              </div>
            }
          >
            <div className="space-y-2.5">
              {sortedSteps.length === 0 && (
                <p className="rounded-md border border-dashed border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-500">
                  No step logs available for this run yet.
                </p>
              )}

              {sortedSteps.map((step, index) => {
                const displayIndex = step.step_index <= 0 ? step.step_index + 1 : step.step_index;
                return (
                  <article
                    key={step.id}
                    className={`rounded-lg border p-3 ${stepCardStyles[step.status] || 'border-gray-200'}`}
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-md border border-gray-200 bg-white text-[11px] font-semibold text-gray-600">
                            {Number.isFinite(displayIndex) ? displayIndex : index + 1}
                          </span>
                          <h3 className="truncate text-sm font-semibold text-gray-900">{step.step_name}</h3>
                          <StatusBadge status={step.status} compact />
                        </div>
                        {step.step_description && <p className="mt-1 text-xs leading-snug text-gray-600">{step.step_description}</p>}
                      </div>

                      <div className="flex items-center gap-2 text-[11px] text-gray-600">
                        <Clock3 className="h-3.5 w-3.5" />
                        <span className="font-semibold text-gray-700">{formatDuration(step.duration_ms)}</span>
                      </div>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-gray-500">
                      <span>Started: {formatTime(step.started_at)}</span>
                      <span>Completed: {formatTime(step.completed_at)}</span>
                      {step.retry_count > 0 && <span>Retries: {step.retry_count}</span>}
                    </div>

                    {step.error_message && (
                      <div className="mt-2 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-2.5 py-2 text-[11px] text-red-700">
                        <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        <p className="leading-relaxed">{step.error_message}</p>
                      </div>
                    )}

                    <div className="mt-2">
                      <JsonPanel label="Step metadata" data={step.metadata} />
                    </div>
                  </article>
                );
              })}
            </div>
          </SectionCard>

          {run.files.length > 0 && (
            <SectionCard title="Processed Files" subtitle="Per-file status, detected format, and extracted record counts">
              <div className="overflow-hidden rounded-lg border border-gray-200">
                <div className="max-h-[360px] overflow-auto">
                  <table className="min-w-full text-left text-xs">
                    <thead className="sticky top-0 bg-gray-50">
                      <tr className="border-b border-gray-200">
                        <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">File</th>
                        <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Role</th>
                        <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Format</th>
                        <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Records</th>
                        <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {run.files.map((file) => (
                        <tr key={file.id} className="hover:bg-gray-50/70">
                          <td className="px-3 py-2 align-top">
                            <div className="flex items-start gap-2">
                              <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400" />
                              <div className="min-w-0">
                                <p className="truncate font-semibold text-gray-800">{file.filename}</p>
                                <p className="font-mono text-[10px] text-gray-500">{file.file_id}</p>
                                {file.error_message && <p className="mt-0.5 text-[10px] text-red-600">{file.error_message}</p>}
                              </div>
                            </div>
                          </td>
                          <td className="px-3 py-2 align-top">
                            <span className="rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-indigo-700">
                              {file.role}
                            </span>
                          </td>
                          <td className="px-3 py-2 align-top font-mono text-[11px] text-gray-600">{file.detected_format || '--'}</td>
                          <td className="px-3 py-2 align-top font-semibold text-gray-700">{file.record_count}</td>
                          <td className="px-3 py-2 align-top">
                            <StatusBadge status={file.status} compact />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </SectionCard>
          )}

          {run.extracted_data.length > 0 && (
            <SectionCard title="Extracted Data" subtitle="Raw payloads and normalized outputs captured per source role">
              <div className="space-y-3">
                {run.extracted_data.map((item) => (
                  <article key={item.id} className="rounded-lg border border-gray-200 bg-gray-50/40 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-indigo-700">
                        {item.source_role}
                      </span>
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-700">
                        {item.extraction_method}
                      </span>
                      {item.llm_model && (
                        <span className="rounded bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
                          {item.llm_model}
                        </span>
                      )}
                      <span className="ml-auto text-[11px] text-gray-500">{formatTime(item.created_at)}</span>
                    </div>
                    <div className="mt-2 space-y-2">
                      <JsonPanel label="Raw payload" data={item.raw_data} />
                      <JsonPanel label="Processed output" data={item.data} />
                    </div>
                  </article>
                ))}
              </div>
            </SectionCard>
          )}
        </div>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <SectionCard title="Run Metadata" subtitle="Execution timestamps and audit identifiers">
            <dl className="space-y-2 text-xs">
              <div className="grid grid-cols-[120px_1fr] gap-2">
                <dt className="font-semibold text-gray-500">Started</dt>
                <dd className="text-gray-800">{formatTime(run.started_at)}</dd>
              </div>
              <div className="grid grid-cols-[120px_1fr] gap-2">
                <dt className="font-semibold text-gray-500">Completed</dt>
                <dd className="text-gray-800">{formatTime(run.completed_at)}</dd>
              </div>
              <div className="grid grid-cols-[120px_1fr] gap-2">
                <dt className="font-semibold text-gray-500">Created</dt>
                <dd className="text-gray-800">{formatTime(run.created_at ?? null)}</dd>
              </div>
              <div className="grid grid-cols-[120px_1fr] gap-2">
                <dt className="font-semibold text-gray-500">Updated</dt>
                <dd className="text-gray-800">{formatTime(run.updated_at ?? null)}</dd>
              </div>
              <div className="grid grid-cols-[120px_1fr] gap-2">
                <dt className="font-semibold text-gray-500">Duration</dt>
                <dd className="text-gray-800">{formatDuration(run.duration_ms)}</dd>
              </div>
            </dl>
          </SectionCard>

          <SectionCard title="Run Context" subtitle="Collapsed JSON blocks for operational deep-dive">
            <div className="space-y-2">
              <JsonPanel label="Context summary" data={run.context_summary} defaultOpen />
              <JsonPanel label="Config snapshot" data={run.config_snapshot} />
            </div>
          </SectionCard>
        </aside>
      </div>
    </div>
  );
}
