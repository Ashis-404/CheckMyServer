import { useState } from 'react';

interface Incident {
  id: number;
  server_id: number;
  server_name: string;
  server_url: string;
  started_at: string;
  resolved_at: string | null;
  duration_seconds: number | null;
  reason: string;
  error_category: string | null;
  severity: 'critical' | 'warning' | string;
  status: 'active' | 'resolved';
}

interface IncidentTimelineProps {
  incidents: Incident[];
}

type FilterStatus = 'all' | 'active' | 'resolved';
type FilterSeverity = 'all' | 'critical' | 'warning';

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return 'Ongoing';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
  }
  const h = Math.floor(seconds / 3600);
  const rem = seconds % 3600;
  const m = Math.floor(rem / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return '—';
  try {
    const iso = ts.includes('T') ? ts : ts.replace(' ', 'T') + (ts.endsWith('Z') ? '' : 'Z');
    return new Date(iso).toLocaleString([], {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return ts;
  }
}

export default function IncidentTimeline({ incidents }: IncidentTimelineProps) {
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [severityFilter, setSeverityFilter] = useState<FilterSeverity>('all');

  const filtered = incidents.filter((inc) => {
    const matchStatus   = statusFilter   === 'all' || inc.status   === statusFilter;
    const matchSeverity = severityFilter === 'all' || inc.severity === severityFilter;
    return matchStatus && matchSeverity;
  });

  const activeCount   = incidents.filter(i => i.status === 'active').length;
  const criticalCount = incidents.filter(i => i.severity === 'critical').length;

  const getSeverityConfig = (severity: string) => {
    if (severity === 'critical') return {
      dot:    'bg-red-500 shadow-red-500/50',
      badge:  'bg-red-500/15 text-red-300 border border-red-500/30',
      pulse:  true,
    };
    return {
      dot:    'bg-amber-400 shadow-amber-400/50',
      badge:  'bg-amber-500/15 text-amber-300 border border-amber-500/30',
      pulse:  false,
    };
  };

  const getStatusConfig = (status: string) => {
    if (status === 'active') return {
      badge: 'bg-red-500/15 text-red-300 border border-red-500/30',
      label: 'Active',
    };
    return {
      badge: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
      label: 'Resolved',
    };
  };

  return (
    <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="px-6 py-5 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-rose-500 to-red-700 rounded-lg shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Incident Timeline</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {activeCount > 0
                  ? <span className="text-red-400 font-semibold">{activeCount} active incident{activeCount !== 1 ? 's' : ''}</span>
                  : <span className="text-emerald-400 font-semibold">No active incidents</span>
                }
                {criticalCount > 0 && <span className="ml-2 text-slate-500">• {criticalCount} critical</span>}
              </p>
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Status filter */}
            <div className="flex bg-white/5 rounded-lg border border-white/10 overflow-hidden text-xs font-semibold">
              {(['all', 'active', 'resolved'] as FilterStatus[]).map(f => (
                <button
                  key={f}
                  id={`incident-filter-status-${f}`}
                  onClick={() => setStatusFilter(f)}
                  className={`px-3 py-1.5 capitalize transition-colors duration-150 ${
                    statusFilter === f
                      ? 'bg-white/15 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            {/* Severity filter */}
            <div className="flex bg-white/5 rounded-lg border border-white/10 overflow-hidden text-xs font-semibold">
              {(['all', 'critical', 'warning'] as FilterSeverity[]).map(f => (
                <button
                  key={f}
                  id={`incident-filter-severity-${f}`}
                  onClick={() => setSeverityFilter(f)}
                  className={`px-3 py-1.5 capitalize transition-colors duration-150 ${
                    severityFilter === f
                      ? 'bg-white/15 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Timeline content */}
      <div className="divide-y divide-white/5">
        {filtered.length === 0 ? (
          <div className="py-16 text-center">
            <div className="text-5xl mb-4 opacity-30">🛡️</div>
            <p className="text-slate-400 font-semibold">No incidents match the current filter</p>
            <p className="text-slate-500 text-sm mt-1">
              {incidents.length === 0 ? 'No incidents have been recorded yet.' : 'Try adjusting the filters above.'}
            </p>
          </div>
        ) : (
          filtered.map((incident) => {
            const sev = getSeverityConfig(incident.severity);
            const sta = getStatusConfig(incident.status);
            return (
              <div
                key={incident.id}
                className="px-6 py-4 hover:bg-white/5 transition-colors duration-150 flex items-start gap-4"
              >
                {/* Timeline dot */}
                <div className="flex flex-col items-center mt-1.5 flex-shrink-0">
                  <div className={`w-3 h-3 rounded-full shadow-lg ${sev.dot} ${sev.pulse ? 'animate-pulse' : ''}`} />
                  <div className="w-px flex-1 bg-white/10 mt-1 min-h-[20px]" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-semibold text-white text-sm truncate">
                          {incident.server_name}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${sev.badge}`}>
                          {incident.severity.toUpperCase()}
                        </span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${sta.badge}`}>
                          {sta.label}
                        </span>
                      </div>
                      <p className="text-sm text-slate-300 mb-1">
                        {incident.error_category && (
                          <span className="font-medium text-amber-300">[{incident.error_category}] </span>
                        )}
                        {incident.reason}
                      </p>
                    </div>

                    {/* Duration chip */}
                    <div className="flex-shrink-0 text-right">
                      <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold ${
                        incident.status === 'active'
                          ? 'bg-red-500/15 text-red-300 border border-red-500/30'
                          : 'bg-slate-700/50 text-slate-300 border border-white/10'
                      }`}>
                        <svg className="w-3.5 h-3.5 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {incident.status === 'active' ? 'Ongoing' : formatDuration(incident.duration_seconds)}
                      </div>
                    </div>
                  </div>

                  {/* Timestamps */}
                  <div className="flex items-center gap-4 text-xs text-slate-500 font-mono mt-1">
                    <span>
                      <span className="text-slate-600 mr-1">Started</span>
                      {formatTimestamp(incident.started_at)}
                    </span>
                    {incident.resolved_at && (
                      <span>
                        <span className="text-slate-600 mr-1">Resolved</span>
                        {formatTimestamp(incident.resolved_at)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {filtered.length > 0 && (
        <div className="px-6 py-3 border-t border-white/5 bg-white/2">
          <p className="text-xs text-slate-500">
            Showing {filtered.length} of {incidents.length} incident{incidents.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </div>
  );
}
