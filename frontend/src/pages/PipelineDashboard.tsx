import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Play,
  RefreshCw,
  Timer,
  XCircle,
} from 'lucide-react';
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

interface PipelineRunsResponse {
  data: PipelineRunSummary[];
  total: number;
}

interface TriggerPipelineResponse {
  message?: string;
  run_id?: string;
  celery_task_id?: string;
  status?: string;
}

interface TriggerBanner {
  type: 'success' | 'error';
  message: string;
}

const ACTIVE_RUN_STATUSES = new Set(['PENDING', 'RUNNING']);

const statusColors: Record<string, string> = {
  COMPLETED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  FAILED: 'bg-red-50 text-red-700 border-red-200',
  RUNNING: 'bg-blue-50 text-blue-700 border-blue-200',
  PENDING: 'bg-amber-50 text-amber-700 border-amber-200',
  PARTIALLY_COMPLETED: 'bg-yellow-50 text-yellow-700 border-yellow-200',
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

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold tracking-wide ${
        statusColors[status] || 'bg-gray-50 text-gray-700 border-gray-200'
      }`}
    >
      {formatStatus(status)}
    </span>
  );
}

function MetricCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">{label}</p>
        <span className="text-gray-400">{icon}</span>
      </div>
      <p className="mt-1 text-base font-semibold text-gray-900">{value}</p>
      {hint && <p className="mt-0.5 text-[11px] font-medium text-gray-500">{hint}</p>}
    </div>
  );
}

export default function PipelineDashboard() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<PipelineRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [banner, setBanner] = useState<TriggerBanner | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      const response = (await apiClient.getPipelineRuns({ limit: 50 })) as PipelineRunsResponse;
      setRuns(response.data || []);
      setLastRefreshAt(new Date().toISOString());
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch pipeline runs';
      setBanner({ type: 'error', message: `Unable to refresh runs: ${message}` });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void fetchRuns();
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [fetchRuns]);

  const handleTrigger = useCallback(async () => {
    setTriggering(true);
    setBanner(null);
    try {
      const response = (await apiClient.triggerPipeline()) as TriggerPipelineResponse;
      const runId = response.run_id;
      const baseMessage = response.message || 'Pipeline queued';
      const message = runId ? `${baseMessage}. Run ID: ${runId}` : baseMessage;
      setBanner({ type: 'success', message });
      window.setTimeout(() => {
        void fetchRuns();
      }, 1500);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to trigger pipeline';
      setBanner({ type: 'error', message: `Trigger failed: ${message}` });
    } finally {
      setTriggering(false);
    }
  }, [fetchRuns]);

  const stats = useMemo(() => {
    const runsWithDuration = runs.filter((run) => run.duration_ms != null);
    const totalDuration = runsWithDuration.reduce((sum, run) => sum + (run.duration_ms || 0), 0);
    const total = runs.length;
    const running = runs.filter((run) => ACTIVE_RUN_STATUSES.has(run.status)).length;
    const completed = runs.filter((run) => run.status === 'COMPLETED').length;
    const failed = runs.filter((run) => run.status === 'FAILED').length;
    const avgDurationMs = runsWithDuration.length > 0 ? totalDuration / runsWithDuration.length : 0;
    const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;

    return {
      total,
      running,
      completed,
      failed,
      successRate,
      avgDurationMs,
    };
  }, [runs]);

  return (
    <div className="mx-auto min-h-screen max-w-[1200px] space-y-4 px-4 py-4 md:px-6 md:py-6">
      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm md:p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-gray-900">Pipeline Dashboard</h1>
              <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                LIVE
              </span>
            </div>
            <p className="mt-1 text-sm text-gray-600">
              Compact operations view for pipeline execution health, throughput, and run diagnostics.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void fetchRuns()}
              className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </button>
            <button
              type="button"
              onClick={() => void handleTrigger()}
              disabled={triggering}
              className="inline-flex items-center gap-1 rounded-md bg-[#0a2540] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#143a61] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {triggering ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              {triggering ? 'Triggering...' : 'Trigger Pipeline'}
            </button>
          </div>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            label="Total Runs"
            value={`${stats.total}`}
            hint="Latest 50 records"
            icon={<Activity className="h-3.5 w-3.5" />}
          />
          <MetricCard
            label="Active Runs"
            value={`${stats.running}`}
            hint="Pending + Running"
            icon={<RefreshCw className="h-3.5 w-3.5" />}
          />
          <MetricCard
            label="Completed"
            value={`${stats.completed}`}
            hint={`${stats.successRate}% success`}
            icon={<CheckCircle2 className="h-3.5 w-3.5" />}
          />
          <MetricCard
            label="Failed"
            value={`${stats.failed}`}
            hint="Needs investigation"
            icon={<XCircle className="h-3.5 w-3.5" />}
          />
          <MetricCard
            label="Avg Duration"
            value={formatDuration(stats.avgDurationMs || null)}
            hint="Across runs with duration"
            icon={<Timer className="h-3.5 w-3.5" />}
          />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-gray-500">
          <span className="inline-flex items-center gap-1">
            <Clock3 className="h-3.5 w-3.5" />
            Auto-refresh: 5s
          </span>
          <span>{lastRefreshAt ? `Last updated: ${formatTime(lastRefreshAt)}` : 'Last updated: --'}</span>
        </div>
      </section>

      {banner && (
        <section
          className={`rounded-lg border px-3 py-2.5 text-xs font-medium shadow-sm ${
            banner.type === 'error'
              ? 'border-red-200 bg-red-50 text-red-700'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700'
          }`}
        >
          <div className="flex items-start gap-2">
            {banner.type === 'error' ? <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" /> : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />}
            <p>{banner.message}</p>
          </div>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 bg-gray-50/70 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Recent Executions</h2>
            <p className="text-xs text-gray-500">Click any row to open run-level detail and diagnostics.</p>
          </div>
          <span className="rounded-md border border-gray-200 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-600">
            {runs.length} records
          </span>
        </header>

        {loading ? (
          <div className="flex min-h-[280px] flex-col items-center justify-center gap-2 text-sm text-gray-500">
            <RefreshCw className="h-5 w-5 animate-spin text-gray-400" />
            Fetching pipeline runs...
          </div>
        ) : runs.length === 0 ? (
          <div className="flex min-h-[260px] flex-col items-center justify-center px-6 text-center">
            <p className="text-sm font-semibold text-gray-800">No execution history yet</p>
            <p className="mt-1 text-xs text-gray-500">Trigger a pipeline run to populate this dashboard.</p>
          </div>
        ) : (
          <div className="max-h-[620px] overflow-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="sticky top-0 z-10 bg-white">
                <tr className="border-b border-gray-200">
                  <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Insurer</th>
                  <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Status</th>
                  <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Progress</th>
                  <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Duration</th>
                  <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Started</th>
                  <th className="px-3 py-2 font-semibold uppercase tracking-wider text-gray-500">Issue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {runs.map((run) => {
                  const totalSteps = run.total_steps ?? 0;
                  const completedSteps = run.steps_completed ?? 0;
                  const percent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
                  const progressBarColor =
                    run.status === 'FAILED'
                      ? 'bg-red-500'
                      : run.status === 'COMPLETED'
                        ? 'bg-emerald-500'
                        : run.status === 'PARTIALLY_COMPLETED'
                          ? 'bg-yellow-500'
                          : 'bg-blue-500';

                  return (
                    <tr
                      key={run.id}
                      onClick={() => navigate(`/pipelines/${run.id}`)}
                      className="cursor-pointer hover:bg-gray-50/80"
                    >
                      <td className="px-3 py-2.5 align-top">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-gray-900">{run.insurer_code}</p>
                          <p className="truncate text-[11px] text-gray-500">{run.insurer_name || 'Unknown insurer'}</p>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 align-top">
                        <StatusBadge status={run.status} />
                      </td>
                      <td className="px-3 py-2.5 align-top">
                        <div className="flex min-w-[140px] items-center gap-2">
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
                            <div className={`h-full rounded-full ${progressBarColor}`} style={{ width: `${percent}%` }} />
                          </div>
                          <span className="font-semibold text-gray-600">{completedSteps}/{totalSteps || '-'}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 align-top font-mono text-[11px] text-gray-700">{formatDuration(run.duration_ms)}</td>
                      <td className="px-3 py-2.5 align-top text-[11px] text-gray-600">{formatTime(run.started_at)}</td>
                      <td className="px-3 py-2.5 align-top">
                        {run.error_message ? (
                          <span className="line-clamp-2 text-[11px] font-medium text-red-700">{run.error_message}</span>
                        ) : (
                          <span className="text-[11px] text-gray-400">--</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
