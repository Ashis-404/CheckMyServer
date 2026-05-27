import { useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Server {
  id: number;
  name: string;
  url: string;
  email: string;
}

interface HistoryItem {
  timestamp: string;
  status: string;
  response_time: number;
  http_status_code: number | null;
  error_message?: string | null;
  error_category?: string | null;
  severity?: string | null;
}

interface HistoryModalProps {
  server: Server;
  history: HistoryItem[];
  onClose: () => void;
}

export default function HistoryModal({ server, history, onClose }: HistoryModalProps) {
  const [chartRange, setChartRange] = useState<20 | 50 | 100>(20);

  const getStatusBadgeColor = (status: string) => {
    if (status === 'UP')      return 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50';
    if (status === 'DOWN')    return 'bg-red-500/20 text-red-300 border border-red-400/50';
    if (status === 'WARNING') return 'bg-amber-500/20 text-amber-300 border border-amber-400/50';
    return 'bg-slate-500/20 text-slate-300 border border-slate-400/50';
  };

  const getStatusDotColor = (status: string) => {
    if (status === 'UP')      return 'bg-emerald-400 shadow-lg shadow-emerald-400/50';
    if (status === 'DOWN')    return 'bg-red-400 shadow-lg shadow-red-400/50';
    if (status === 'WARNING') return 'bg-amber-400 shadow-lg shadow-amber-400/50';
    return 'bg-slate-400';
  };

  const getErrorBadge = (category: string | null | undefined, severity: string | null | undefined) => {
    if (!category || category === 'Healthy') return null;
    if (severity === 'critical') return 'bg-red-500/15 text-red-300 border border-red-500/30';
    if (severity === 'warning')  return 'bg-amber-500/15 text-amber-300 border border-amber-500/30';
    return 'bg-slate-500/15 text-slate-300 border border-slate-500/30';
  };

  const formatTime = (timestamp: string) => {
    if (!timestamp) return 'Never';
    try {
      const iso = timestamp.replace(' ', 'T') + 'Z';
      return new Date(iso).toLocaleString([], {
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      });
    } catch { return timestamp; }
  };

  const formatFullDate = (timestamp: string) => {
    if (!timestamp) return 'Never';
    try {
      const iso = timestamp.replace(' ', 'T') + 'Z';
      return new Date(iso).toLocaleString([], {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      });
    } catch { return timestamp; }
  };

  // Stats calculations
  const validChecks = history.filter(h => h.response_time !== null);
  const avgLatency  = validChecks.length > 0
    ? validChecks.reduce((sum, h) => sum + h.response_time, 0) / validChecks.length : 0;
  const maxLatency  = validChecks.length > 0 ? Math.max(...validChecks.map(h => h.response_time)) : 0;
  const minLatency  = validChecks.length > 0 ? Math.min(...validChecks.map(h => h.response_time)) : 0;
  const upCount     = history.filter(h => h.status === 'UP').length;
  const downCount   = history.filter(h => h.status === 'DOWN').length;
  const warnCount   = history.filter(h => h.status === 'WARNING').length;
  const historySLA  = history.length > 0 ? (upCount / history.length) * 100 : 100;

  // Chart data (most recent `chartRange` checks, reversed to chronological order)
  const slicedHistory = history.slice(0, chartRange);
  const chartData = [...slicedHistory].reverse().map(item => ({
    time:    formatTime(item.timestamp),
    latency: item.response_time ? parseFloat(item.response_time.toFixed(3)) : 0,
    status:  item.status,
    rawTime: item.timestamp,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const p = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-white/20 rounded-lg px-3 py-2.5 text-xs shadow-xl">
        <p className="text-slate-400 mb-1 font-mono">{formatFullDate(p.rawTime)}</p>
        <p className="text-cyan-400 font-bold font-mono">{p.latency.toFixed(3)}s</p>
        <p className={`font-semibold ${
          p.status === 'UP' ? 'text-emerald-400' :
          p.status === 'WARNING' ? 'text-amber-400' : 'text-red-400'
        }`}>{p.status}</p>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 rounded-2xl shadow-2xl
                      max-w-4xl w-full max-h-[92vh] flex flex-col border border-white/10">

        {/* Header */}
        <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 px-8 py-5 border-b border-white/10 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className="p-2.5 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">{server.name} — Health Metrics</h3>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">{server.url}</p>
            </div>
          </div>
          <button onClick={onClose}
            className="text-slate-400 hover:text-white text-xl transition-colors p-1.5 hover:bg-white/10 rounded-lg">
            ✕
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">

          {history.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-6xl mb-4 opacity-30">📭</div>
              <p className="text-slate-400 font-medium">No monitoring history available yet.</p>
            </div>
          ) : (
            <>
              {/* Stat widgets */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Avg Latency</p>
                  <p className="text-2xl font-extrabold text-cyan-400 font-mono">{avgLatency.toFixed(3)}<span className="text-sm text-slate-400 font-normal ml-1">s</span></p>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Peak Latency</p>
                  <p className="text-2xl font-extrabold text-blue-400 font-mono">{maxLatency.toFixed(3)}<span className="text-sm text-slate-400 font-normal ml-1">s</span></p>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Min Latency</p>
                  <p className="text-2xl font-extrabold text-emerald-400 font-mono">{minLatency.toFixed(3)}<span className="text-sm text-slate-400 font-normal ml-1">s</span></p>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">SLA Uptime</p>
                  <p className={`text-2xl font-extrabold font-mono ${
                    historySLA >= 99 ? 'text-emerald-400' : historySLA >= 95 ? 'text-amber-400' : 'text-red-400'
                  }`}>{historySLA.toFixed(1)}<span className="text-sm text-slate-400 font-normal ml-0.5">%</span></p>
                </div>
              </div>

              {/* Check summary bar */}
              <div className="flex gap-2">
                <div className="flex-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2 text-center">
                  <p className="text-lg font-bold text-emerald-400 font-mono">{upCount}</p>
                  <p className="text-xs text-emerald-500/70 font-semibold uppercase tracking-wider">Up</p>
                </div>
                <div className="flex-1 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 text-center">
                  <p className="text-lg font-bold text-amber-400 font-mono">{warnCount}</p>
                  <p className="text-xs text-amber-500/70 font-semibold uppercase tracking-wider">Warning</p>
                </div>
                <div className="flex-1 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-center">
                  <p className="text-lg font-bold text-red-400 font-mono">{downCount}</p>
                  <p className="text-xs text-red-500/70 font-semibold uppercase tracking-wider">Down</p>
                </div>
              </div>

              {/* Latency chart */}
              <div className="bg-slate-900/60 border border-white/10 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                    Latency Timeline
                  </h4>
                  <div className="flex bg-white/5 rounded-lg border border-white/10 overflow-hidden text-xs font-semibold">
                    {([20, 50, 100] as const).map(r => (
                      <button key={r} onClick={() => setChartRange(r)}
                        className={`px-2.5 py-1 transition-colors ${
                          chartRange === r ? 'bg-white/15 text-white' : 'text-slate-400 hover:text-white'
                        }`}>
                        {r}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="h-52 w-full font-mono text-xs">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor="#06b6d4" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="time" stroke="#94a3b8" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                      <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} unit="s" tick={{ fontSize: 10 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area type="monotone" dataKey="latency"
                        stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#colorLatency)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Check log table */}
              <div className="bg-slate-900/60 border border-white/10 rounded-xl overflow-hidden">
                <div className="px-5 py-3.5 border-b border-white/10 bg-white/5 flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white">Check Log</h4>
                  <span className="text-xs text-slate-400">Last {history.length} checks</span>
                </div>
                <div className="max-h-[28vh] overflow-y-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="sticky top-0 bg-slate-900 border-b border-white/10 z-10">
                      <tr>
                        <th className="px-5 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Timestamp</th>
                        <th className="px-5 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                        <th className="px-5 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Issue</th>
                        <th className="px-5 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Response</th>
                        <th className="px-5 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">HTTP</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {history.map((item, idx) => {
                        const errorBadge = getErrorBadge(item.error_category, item.severity);
                        return (
                          <tr key={idx} className="hover:bg-white/5 transition-colors">
                            <td className="px-5 py-2.5 text-slate-300 font-mono text-xs">{formatFullDate(item.timestamp)}</td>
                            <td className="px-5 py-2.5">
                              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-xs font-semibold ${getStatusBadgeColor(item.status)}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${getStatusDotColor(item.status)}`} />
                                {item.status}
                              </span>
                            </td>
                            <td className="px-5 py-2.5">
                              {item.error_category && item.error_category !== 'Healthy' ? (
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                                  errorBadge ?? 'bg-slate-500/15 text-slate-300 border border-slate-500/30'
                                }`}>
                                  {item.error_category}
                                </span>
                              ) : (
                                <span className="text-emerald-400/50 text-xs">—</span>
                              )}
                            </td>
                            <td className="px-5 py-2.5 text-slate-400 font-mono text-xs">
                              {item.response_time != null ? `${item.response_time.toFixed(3)}s` : 'N/A'}
                            </td>
                            <td className="px-5 py-2.5 text-slate-400 font-mono text-xs font-semibold">
                              {item.http_status_code || '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="bg-white/5 border-t border-white/10 px-8 py-4 flex justify-end flex-shrink-0">
          <button onClick={onClose}
            className="px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500
                       text-white rounded-lg font-semibold text-sm transition-all duration-200 shadow-lg shadow-cyan-500/20">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
