interface PerfMetrics {
  avg_latency_ms:   number | null;
  p95_latency_ms:   number | null;
  max_latency_ms:   number | null;
  min_latency_ms:   number | null;
  success_rate:     number | null;
  failure_rate:     number | null;
  requests_per_sec: number | null;
  total_requests:   number | null;
  total_failed:     number | null;
  degradation_pct:  number | null;
  warning_level:    'none' | 'warning' | 'critical' | 'degraded' | null;
}

export interface PerfTest {
  id:               number;
  url:              string;
  vus:              number;
  duration_seconds: number;
  method:           string;
  status:           'pending' | 'running' | 'completed' | 'failed';
  created_at:       string;
  started_at:       string | null;
  completed_at:     string | null;
  error_message:    string | null;
  // flat metrics from joined query
  avg_latency_ms?:   number | null;
  p95_latency_ms?:   number | null;
  max_latency_ms?:   number | null;
  success_rate?:     number | null;
  failure_rate?:     number | null;
  requests_per_sec?: number | null;
  total_requests?:   number | null;
  degradation_pct?:  number | null;
  warning_level?:    string | null;
  // nested metrics (from /api/perf/tests/:id)
  metrics?: PerfMetrics | null;
}

interface PerformanceResultCardProps {
  test: PerfTest;
  onDelete?: (id: number) => void;
}

function ms(val: number | null | undefined, decimals = 1): string {
  if (val === null || val === undefined) return 'N/A';
  if (val >= 1000) return `${(val / 1000).toFixed(decimals)}s`;
  return `${val.toFixed(decimals)}ms`;
}

function pct(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'N/A';
  return `${val.toFixed(1)}%`;
}

function rps(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'N/A';
  return `${val.toFixed(1)}/s`;
}

type WarningLevel = 'none' | 'warning' | 'critical' | 'degraded' | string | null | undefined;

function WarningBadge({ level }: { level: WarningLevel }) {
  const config = {
    none:     { label: 'Healthy',  cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', icon: '✓' },
    warning:  { label: 'Warning',  cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30',       icon: '⚠' },
    critical: { label: 'Critical', cls: 'bg-red-500/15 text-red-400 border-red-500/30',             icon: '✕' },
    degraded: { label: 'Degraded', cls: 'bg-orange-500/15 text-orange-400 border-orange-500/30',    icon: '↓' },
  };
  const key = (level ?? 'none') as keyof typeof config;
  const c   = config[key] ?? config.none;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border ${c.cls}`}>
      <span>{c.icon}</span>{c.label}
    </span>
  );
}

function StatPill({ label, value, color = 'text-white' }: {
  label: string; value: string; color?: string;
}) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
      <p className={`text-lg font-extrabold font-mono ${color}`}>{value}</p>
      <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mt-0.5">{label}</p>
    </div>
  );
}

function DegradationTag({ pct }: { pct: number | null | undefined }) {
  if (pct === null || pct === undefined) return null;
  const improved = pct < 0;
  const abs      = Math.abs(pct).toFixed(1);
  if (Math.abs(pct) < 1) return null; // insignificant delta
  return (
    <span className={`text-xs font-semibold flex items-center gap-1 ${
      improved ? 'text-emerald-400' : pct > 50 ? 'text-red-400' : 'text-amber-400'
    }`}>
      {improved ? '↑' : '↓'}
      {improved
        ? `${abs}% faster than historical avg`
        : `${abs}% slower than historical avg`}
    </span>
  );
}

function LatencyBar({ avg, p95, max }: {
  avg: number | null | undefined;
  p95: number | null | undefined;
  max: number | null | undefined;
}) {
  if (!max || max === 0) return null;
  const toW = (v: number | null | undefined) =>
    v ? `${Math.min((v / max) * 100, 100).toFixed(1)}%` : '0%';

  return (
    <div className="space-y-1.5 mt-3">
      {[
        { label: 'Avg', value: avg, color: 'bg-cyan-500', w: toW(avg) },
        { label: 'P95', value: p95, color: 'bg-amber-500', w: toW(p95) },
        { label: 'Max', value: max, color: 'bg-red-500',  w: '100%'   },
      ].map(({ label, value, color, w }) => (
        <div key={label} className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-500 w-6">{label}</span>
          <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: w }} />
          </div>
          <span className="text-[10px] font-mono text-slate-400 w-16 text-right">{ms(value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function PerformanceResultCard({ test, onDelete }: PerformanceResultCardProps) {
  // Support both flat (list) and nested (detail) metric shapes
  const m = test.metrics ?? test;

  const avgMs    = m.avg_latency_ms;
  const p95Ms    = m.p95_latency_ms;
  const maxMs    = m.max_latency_ms;
  const succRate = m.success_rate;
  const rpsStat  = m.requests_per_sec;
  const totalReq = m.total_requests;
  const degPct   = m.degradation_pct;
  const warnLvl  = m.warning_level;

  const isRunning = test.status === 'running' || test.status === 'pending';
  const isFailed  = test.status === 'failed';

  const timeLabel = test.completed_at
    ? new Date(test.completed_at + 'Z').toLocaleTimeString()
    : test.started_at
      ? new Date(test.started_at + 'Z').toLocaleTimeString()
      : new Date(test.created_at + 'Z').toLocaleTimeString();

  return (
    <div className={`bg-white/5 border rounded-2xl p-5 transition-all duration-300 hover:border-white/20 ${
      isRunning ? 'border-violet-500/40 shadow-lg shadow-violet-500/10 animate-pulse-slow'
      : isFailed ? 'border-red-500/30'
      : 'border-white/10'
    }`}>
      {/* Card header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-slate-500">#{test.id}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              test.method === 'GET'  ? 'bg-emerald-500/15 text-emerald-400' :
              test.method === 'POST' ? 'bg-blue-500/15 text-blue-400' :
              test.method === 'PUT'  ? 'bg-amber-500/15 text-amber-400' :
              'bg-slate-500/15 text-slate-400'
            }`}>{test.method}</span>
            {isRunning && (
              <span className="text-xs text-violet-400 font-semibold flex items-center gap-1">
                <span className="inline-block w-2 h-2 bg-violet-400 rounded-full animate-pulse" />
                Running…
              </span>
            )}
            {isFailed && <span className="text-xs text-red-400 font-semibold">Failed</span>}
            {test.status === 'completed' && (
              <WarningBadge level={warnLvl} />
            )}
          </div>
          <p className="text-sm font-mono text-slate-300 mt-1 truncate" title={test.url}>
            {test.url}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">
            {test.vus} VUs · {test.duration_seconds}s · {timeLabel}
          </p>
        </div>
        {onDelete && !isRunning && (
          <button
            onClick={() => onDelete(test.id)}
            className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-colors flex-shrink-0"
            title="Delete test"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>

      {/* Failed state */}
      {isFailed && test.error_message && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-xs text-red-400 font-mono break-all">
          {test.error_message}
        </div>
      )}

      {/* Running state */}
      {isRunning && (
        <div className="flex items-center gap-2 py-4">
          <div className="w-5 h-5 border-2 border-violet-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
          <span className="text-sm text-slate-400">Test is running, please wait…</span>
        </div>
      )}

      {/* Completed state — metrics */}
      {test.status === 'completed' && (
        <>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3">
            <StatPill label="Avg"    value={ms(avgMs)}    color="text-cyan-400"    />
            <StatPill label="P95"    value={ms(p95Ms)}    color="text-amber-400"   />
            <StatPill label="Max"    value={ms(maxMs)}    color="text-red-400"     />
            <StatPill label="RPS"    value={rps(rpsStat)} color="text-blue-400"    />
            <StatPill label="OK"     value={pct(succRate)} color={
              (succRate ?? 100) >= 95 ? 'text-emerald-400' :
              (succRate ?? 100) >= 80 ? 'text-amber-400' : 'text-red-400'
            } />
            <StatPill label="Reqs"   value={String(totalReq ?? 'N/A')} color="text-white" />
          </div>

          <LatencyBar avg={avgMs} p95={p95Ms} max={maxMs} />

          {degPct !== null && degPct !== undefined && (
            <div className="mt-3">
              <DegradationTag pct={degPct} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
