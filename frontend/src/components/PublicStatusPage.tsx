import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

interface PublicServer {
  name: string;
  url: string;
  last_status: string;
  last_check_time: string;
}

interface UptimeData {
  '24h': number | null;
  '7d':  number | null;
  '30d': number | null;
}

interface Incident {
  id: number;
  started_at: string;
  resolved_at: string | null;
  duration_seconds: number | null;
  reason: string;
  error_category: string | null;
  severity: string;
  status: 'active' | 'resolved';
}

interface DayEntry {
  day: string;
  uptime: number | null;
  checks: number;
}

interface StatusPageData {
  server:            PublicServer;
  uptime:            UptimeData;
  active_incident:   Incident | null;
  recent_incidents:  Incident[];
  daily_grid:        DayEntry[];
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return 'Ongoing';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatTime(ts: string | null): string {
  if (!ts) return '—';
  try {
    const iso = ts.includes('T') ? ts : ts.replace(' ', 'T') + (ts.endsWith('Z') ? '' : 'Z');
    return new Date(iso).toLocaleString([], {
      month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    });
  } catch { return ts; }
}

function UptimeBar({ pct, label }: { pct: number | null; label: string }) {
  const v = pct ?? 0;
  const color = v >= 99 ? 'bg-emerald-500' : v >= 95 ? 'bg-amber-500' : 'bg-red-500';
  const textColor = v >= 99 ? 'text-emerald-400' : v >= 95 ? 'text-amber-400' : 'text-red-400';
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-400 w-8 shrink-0">{label}</span>
      <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
        <div
          className={`${color} h-2 rounded-full transition-all duration-700`}
          style={{ width: `${Math.min(v, 100)}%` }}
        />
      </div>
      <span className={`text-xs font-bold font-mono w-14 text-right ${textColor}`}>
        {pct !== null ? `${pct.toFixed(2)}%` : 'N/A'}
      </span>
    </div>
  );
}

function DayCell({ entry }: { entry: DayEntry }) {
  const pct = entry.uptime;
  let color = 'bg-slate-800';
  let title = 'No data';
  if (pct !== null) {
    color = pct >= 99 ? 'bg-emerald-500' : pct >= 95 ? 'bg-amber-500/70' : 'bg-red-500/70';
    title = `${entry.day}: ${pct}% uptime (${entry.checks} checks)`;
  }
  return (
    <div
      title={title}
      className={`w-3 h-3 rounded-sm ${color} cursor-default transition-opacity hover:opacity-70`}
    />
  );
}

interface Props {
  slug: string;
  onBack: () => void;
}

export default function PublicStatusPage({ slug, onBack }: Props) {
  const [data, setData]       = useState<StatusPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API_URL}/status/${slug}`)
      .then(res => { setData(res.data); setLoading(false); })
      .catch(() => { setError('Status page not found.'); setLoading(false); });
  }, [slug]);

  if (loading) return (
    <div className="fixed inset-0 z-50 bg-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-block w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400">Loading status page...</p>
      </div>
    </div>
  );

  if (error || !data) return (
    <div className="fixed inset-0 z-50 bg-slate-950 flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        <div className="text-5xl mb-6">🔍</div>
        <h2 className="text-2xl font-bold text-white mb-3">Status Page Not Found</h2>
        <p className="text-slate-400 mb-6">{error ?? 'This status page does not exist.'}</p>
        <button onClick={onBack}
          className="px-5 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-white rounded-lg font-semibold text-sm transition-colors">
          ← Back to Dashboard
        </button>
      </div>
    </div>
  );

  const { server, uptime, active_incident, recent_incidents, daily_grid } = data;

  const statusConfig = {
    UP:      { label: 'Operational',      dot: 'bg-emerald-400', text: 'text-emerald-400', bg: 'from-emerald-950 to-emerald-900/30' },
    DOWN:    { label: 'Service Outage',   dot: 'bg-red-500',     text: 'text-red-400',     bg: 'from-red-950 to-red-900/30' },
    WARNING: { label: 'Degraded Service', dot: 'bg-amber-400',   text: 'text-amber-400',   bg: 'from-amber-950 to-amber-900/30' },
  }[server.last_status] ?? { label: 'Unknown', dot: 'bg-slate-500', text: 'text-slate-400', bg: 'from-slate-950 to-slate-900' };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950 overflow-y-auto">
      <div className="max-w-2xl mx-auto py-10 px-4">

        {/* Back button */}
        <button onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-white text-sm font-medium mb-8 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Dashboard
        </button>

        {/* Status hero */}
        <div className={`bg-gradient-to-br ${statusConfig.bg} border border-white/10 rounded-2xl p-8 mb-6`}>
          <div className="flex items-center gap-4 mb-6">
            <div className={`w-4 h-4 rounded-full ${statusConfig.dot} shadow-lg animate-pulse`} />
            <div>
              <h1 className="text-2xl font-bold text-white">{server.name}</h1>
              <a href={server.url} target="_blank" rel="noreferrer"
                className="text-sm text-slate-400 hover:text-cyan-400 transition-colors font-mono">
                {server.url}
              </a>
            </div>
          </div>
          <div className={`text-4xl font-extrabold ${statusConfig.text} mb-2`}>
            {statusConfig.label}
          </div>
          <p className="text-slate-400 text-sm">
            Last checked: {formatTime(server.last_check_time)}
          </p>
        </div>

        {/* Active incident banner */}
        {active_incident && (
          <div className="bg-red-950/60 border border-red-500/30 rounded-xl p-5 mb-6 flex items-start gap-4">
            <div className="text-2xl">🔴</div>
            <div>
              <p className="font-bold text-red-300 mb-1">Active Incident</p>
              <p className="text-sm text-red-200">{active_incident.reason}</p>
              <p className="text-xs text-red-400 mt-2 font-mono">
                Started: {formatTime(active_incident.started_at)}
              </p>
            </div>
          </div>
        )}

        {/* Uptime bars */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-5 mb-6 space-y-3">
          <h2 className="text-sm font-bold text-white mb-3">Uptime History</h2>
          <UptimeBar pct={uptime['24h']} label="24h" />
          <UptimeBar pct={uptime['7d']}  label="7d"  />
          <UptimeBar pct={uptime['30d']} label="30d" />
        </div>

        {/* 90-day grid */}
        {daily_grid.length > 0 && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-white">90-Day Uptime Grid</h2>
              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 inline-block" /> Up</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-amber-500/70 inline-block" /> Degraded</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-red-500/70 inline-block" /> Down</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-slate-800 inline-block" /> No data</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              {daily_grid.map((entry, i) => (
                <DayCell key={i} entry={entry} />
              ))}
            </div>
          </div>
        )}

        {/* Incident history */}
        {recent_incidents.length > 0 && (
          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden mb-6">
            <div className="px-5 py-4 border-b border-white/10 bg-white/5">
              <h2 className="text-sm font-bold text-white">Recent Incidents</h2>
            </div>
            <div className="divide-y divide-white/5">
              {recent_incidents.map(inc => (
                <div key={inc.id} className="px-5 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-2 h-2 rounded-full ${inc.status === 'active' ? 'bg-red-500 animate-pulse' : 'bg-slate-500'}`} />
                        <span className="text-sm font-semibold text-white">{inc.error_category ?? 'Incident'}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                          inc.severity === 'critical' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {inc.severity.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">{inc.reason}</p>
                      <p className="text-xs text-slate-500 mt-1 font-mono">{formatTime(inc.started_at)}</p>
                    </div>
                    <div className="text-xs font-mono font-bold text-slate-300 shrink-0">
                      {inc.status === 'active' ? (
                        <span className="text-red-400">Ongoing</span>
                      ) : formatDuration(inc.duration_seconds)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center">
          <p className="text-xs text-slate-600">
            Powered by <span className="text-slate-500 font-semibold">CheckMyServer</span> — Real-time Infrastructure Monitoring
          </p>
        </div>
      </div>
    </div>
  );
}
