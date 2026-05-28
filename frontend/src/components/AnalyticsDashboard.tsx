import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5000/api');

interface Server {
  id: number;
  name: string;
  url: string;
  last_status: string;
}

interface Analytics {
  total_checks:  number;
  avg_latency:   number | null;
  max_latency:   number | null;
  min_latency:   number | null;
  up_count:      number;
  down_count:    number;
  warning_count: number;
  uptime_pct:    number | null;
  uptime_24h:    number | null;
  uptime_7d:     number | null;
  uptime_30d:    number | null;
  latency_trend: Array<{
    hour:     string;
    avg_rt:   number | null;
    checks:   number;
    failures: number;
  }>;
}

interface AnalyticsDashboardProps {
  servers: Server[];
}

function UptimeRing({ pct, label, size = 80 }: { pct: number | null; label: string; size?: number }) {
  const value     = pct ?? 0;
  const radius    = (size - 10) / 2;
  const circ      = 2 * Math.PI * radius;
  const filled    = (value / 100) * circ;
  const color     = value >= 99 ? '#10b981' : value >= 95 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={8} />
          <circle cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke={color} strokeWidth={8}
            strokeDasharray={`${filled} ${circ}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.6s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-extrabold text-white font-mono">
            {pct !== null ? `${pct.toFixed(1)}%` : 'N/A'}
          </span>
        </div>
      </div>
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
    </div>
  );
}

function StatCard({ label, value, unit, color }: {
  label: string; value: string | number; unit?: string; color?: string;
}) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-extrabold font-mono ${color ?? 'text-white'}`}>
        {value}<span className="text-sm font-normal text-slate-400 ml-1">{unit}</span>
      </p>
    </div>
  );
}

export default function AnalyticsDashboard({ servers }: AnalyticsDashboardProps) {
  const [selectedId, setSelectedId]   = useState<number | null>(servers[0]?.id ?? null);
  const [analytics, setAnalytics]     = useState<Analytics | null>(null);
  const [days, setDays]               = useState(7);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState<string | null>(null);

  useEffect(() => {
    if (servers.length > 0 && !selectedId) {
      setSelectedId(servers[0].id);
    }
  }, [servers]);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    axios.get(`${API_URL}/analytics/${selectedId}?days=${days}`)
      .then(res => setAnalytics(res.data))
      .catch(() => setError('Failed to load analytics data.'))
      .finally(() => setLoading(false));
  }, [selectedId, days]);

  const chartData = (analytics?.latency_trend ?? []).map(t => ({
    time:     t.hour ? t.hour.substring(11, 16) : '',
    latency:  t.avg_rt ?? 0,
    failures: t.failures,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-slate-900 border border-white/20 rounded-lg px-3 py-2 text-xs shadow-xl">
        <p className="text-slate-400 mb-1">{label}</p>
        {payload.map((p: any) => (
          <p key={p.name} style={{ color: p.color }} className="font-mono font-semibold">
            {p.name === 'latency' ? `${p.value.toFixed(3)}s` : `${p.value} failures`}
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="px-6 py-5 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-700 rounded-lg shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Performance Analytics</h3>
              <p className="text-xs text-slate-400 mt-0.5">Latency trends, uptime, and reliability metrics</p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Server selector */}
            <select
              id="analytics-server-select"
              value={selectedId ?? ''}
              onChange={e => setSelectedId(Number(e.target.value))}
              className="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white
                         focus:outline-none focus:ring-2 focus:ring-indigo-500/50 cursor-pointer"
            >
              {servers.map(s => (
                <option key={s.id} value={s.id} className="bg-slate-900">
                  {s.name}
                </option>
              ))}
            </select>

            {/* Time range selector */}
            <div className="flex bg-white/5 rounded-lg border border-white/10 overflow-hidden text-xs font-semibold">
              {[1, 7, 30].map(d => (
                <button
                  key={d}
                  id={`analytics-range-${d}d`}
                  onClick={() => setDays(d)}
                  className={`px-3 py-1.5 transition-colors duration-150 ${
                    days === d ? 'bg-white/15 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {d === 1 ? '24h' : `${d}d`}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {servers.length === 0 ? (
          <div className="py-12 text-center">
            <div className="text-5xl mb-4 opacity-30">📊</div>
            <p className="text-slate-400 font-semibold">No servers to analyze</p>
          </div>
        ) : loading ? (
          <div className="py-12 text-center">
            <div className="inline-block w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-slate-400 text-sm">Loading analytics...</p>
          </div>
        ) : error ? (
          <div className="py-12 text-center">
            <div className="text-4xl mb-4 opacity-50">⚠️</div>
            <p className="text-red-400 font-semibold">{error}</p>
          </div>
        ) : analytics ? (
          <>
            {/* Uptime rings */}
            <div className="bg-slate-900/50 border border-white/10 rounded-xl p-5">
              <h4 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                SLA Uptime Overview
              </h4>
              <div className="flex items-center justify-around">
                <UptimeRing pct={analytics.uptime_24h} label="24 Hours" size={90} />
                <UptimeRing pct={analytics.uptime_7d}  label="7 Days"   size={90} />
                <UptimeRing pct={analytics.uptime_30d} label="30 Days"  size={90} />
              </div>
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard
                label="Avg Latency"
                value={analytics.avg_latency !== null ? analytics.avg_latency.toFixed(3) : 'N/A'}
                unit={analytics.avg_latency !== null ? 's' : ''}
                color="text-cyan-400"
              />
              <StatCard
                label="Peak Latency"
                value={analytics.max_latency !== null ? analytics.max_latency.toFixed(3) : 'N/A'}
                unit={analytics.max_latency !== null ? 's' : ''}
                color="text-blue-400"
              />
              <StatCard
                label="Min Latency"
                value={analytics.min_latency !== null ? analytics.min_latency.toFixed(3) : 'N/A'}
                unit={analytics.min_latency !== null ? 's' : ''}
                color="text-emerald-400"
              />
              <StatCard
                label="Warnings"
                value={analytics.warning_count}
                color={analytics.warning_count > 0 ? 'text-amber-400' : 'text-emerald-400'}
              />
            </div>

            {/* Latency trend chart */}
            <div className="bg-slate-900/50 border border-white/10 rounded-xl p-5">
              <h4 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-400" />
                Latency Trend (24h)
              </h4>
              {chartData.length === 0 ? (
                <div className="h-48 flex items-center justify-center">
                  <p className="text-slate-500 text-sm">No data in this period</p>
                </div>
              ) : (
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="analyticsGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor="#818cf8" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#818cf8" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="time" stroke="#475569" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                      <YAxis stroke="#475569" tickLine={false} axisLine={false} unit="s" tick={{ fontSize: 10 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area type="monotone" dataKey="latency" name="latency"
                        stroke="#818cf8" strokeWidth={2} fill="url(#analyticsGradient)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Failures bar chart */}
            {chartData.some(d => d.failures > 0) && (
              <div className="bg-slate-900/50 border border-white/10 rounded-xl p-5">
                <h4 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-400" />
                  Failure Distribution (24h)
                </h4>
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 0, right: 5, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="time" stroke="#475569" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                      <YAxis stroke="#475569" tickLine={false} axisLine={false} allowDecimals={false} tick={{ fontSize: 10 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="failures" name="failures" radius={[4, 4, 0, 0]} maxBarSize={20}>
                        {chartData.map((_, idx) => (
                          <Cell key={idx} fill={_ .failures > 0 ? '#ef4444' : '#334155'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Check summary */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-4 py-2 text-center">
                <p className="text-2xl font-extrabold text-emerald-400 font-mono">{analytics.up_count}</p>
                <p className="text-xs text-emerald-500/70 font-semibold uppercase tracking-wider mt-0.5">Healthy</p>
              </div>
              <div className="flex-1 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-2 text-center">
                <p className="text-2xl font-extrabold text-amber-400 font-mono">{analytics.warning_count}</p>
                <p className="text-xs text-amber-500/70 font-semibold uppercase tracking-wider mt-0.5">Warning</p>
              </div>
              <div className="flex-1 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 text-center">
                <p className="text-2xl font-extrabold text-red-400 font-mono">{analytics.down_count}</p>
                <p className="text-xs text-red-500/70 font-semibold uppercase tracking-wider mt-0.5">Failed</p>
              </div>
              <div className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-center">
                <p className="text-2xl font-extrabold text-slate-300 font-mono">{analytics.total_checks}</p>
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mt-0.5">Total</p>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
