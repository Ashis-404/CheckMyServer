import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import PerformanceTestPanel from './PerformanceTestPanel';
import PerformanceResultCard, { type PerfTest } from './PerformanceResultCard';

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5000/api');

interface Server {
  id: number;
  name: string;
  url: string;
  last_status: string;
}

interface PerformanceDashboardProps {
  servers: Server[];
  latestCompletedTestId?: number | null;
}

interface BenchmarkPoint {
  avg_latency_ms:   number | null;
  p95_latency_ms:   number | null;
  max_latency_ms:   number | null;
  test_created_at:  string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900 border border-white/20 rounded-xl px-4 py-3 text-xs shadow-2xl">
      <p className="text-slate-400 mb-2 font-semibold">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono font-bold">
          {p.name}: {p.value !== null ? `${Number(p.value).toFixed(1)}ms` : 'N/A'}
        </p>
      ))}
    </div>
  );
};

export default function PerformanceDashboard({
  servers,
  latestCompletedTestId,
}: PerformanceDashboardProps) {
  const [tests,        setTests]        = useState<PerfTest[]>([]);
  const [benchmarks,   setBenchmarks]   = useState<BenchmarkPoint[]>([]);
  const [benchmarkUrl, setBenchmarkUrl] = useState('');
  const [toastMsg,     setToastMsg]     = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3500);
  };

  const fetchTests = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/perf/tests?limit=20`);
      setTests(res.data);
    } catch {
      // ignore
    }
  }, []);

  const fetchBenchmarks = useCallback(async (url: string) => {
    if (!url) return;
    try {
      const res = await axios.get(
        `${API_URL}/perf/benchmarks?url=${encodeURIComponent(url)}&limit=12`
      );
      setBenchmarks(res.data.reverse()); // oldest first for chart
    } catch {
      setBenchmarks([]);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchTests();
  }, [fetchTests]);

  // Refresh when SSE notifies a test completed
  useEffect(() => {
    if (latestCompletedTestId != null) {
      fetchTests();
    }
  }, [latestCompletedTestId, fetchTests]);

  // When benchmark URL changes, fetch its history
  useEffect(() => {
    if (benchmarkUrl) fetchBenchmarks(benchmarkUrl);
  }, [benchmarkUrl, fetchBenchmarks]);

  const handleTestStarted = (testId: number) => {
    // Optimistically add a "running" placeholder
    const stub: PerfTest = {
      id: testId, url: benchmarkUrl || '', vus: 0, duration_seconds: 0,
      method: 'GET', status: 'running', created_at: new Date().toISOString(),
      started_at: null, completed_at: null, error_message: null,
    };
    setTests(prev => [stub, ...prev]);
  };

  const handleTestCompleted = () => {
    fetchTests();
    if (benchmarkUrl) fetchBenchmarks(benchmarkUrl);
    showToast('Test completed! Results are ready.');
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this test result?')) return;
    try {
      await axios.delete(`${API_URL}/perf/tests/${id}`);
      setTests(prev => prev.filter(t => t.id !== id));
      showToast('Test deleted.');
    } catch {
      showToast('Failed to delete test.');
    }
  };

  // Chart data
  const chartData = benchmarks.map((b, i) => ({
    name:    `#${benchmarks.length - i}`, // reverse: older = smaller number
    avg:     b.avg_latency_ms,
    p95:     b.p95_latency_ms,
    max:     b.max_latency_ms,
  }));

  // Build unique URL list from tests for benchmark picker
  const uniqueUrls = Array.from(new Set(
    tests.filter(t => t.status === 'completed').map(t => t.url)
  ));

  return (
    <div className="space-y-6">
      {/* Toast notification */}
      {toastMsg && (
        <div className="fixed top-6 right-6 z-50 bg-slate-800 border border-violet-500/40 rounded-xl px-5 py-3
                        shadow-2xl shadow-violet-500/10 text-sm text-white font-semibold flex items-center gap-2
                        animate-fade-in">
          <span className="text-violet-400">⚡</span> {toastMsg}
        </div>
      )}

      {/* Top row: test panel + recent results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Test creation panel */}
        <PerformanceTestPanel
          servers={servers}
          onTestStarted={handleTestStarted}
          onTestCompleted={handleTestCompleted}
        />

        {/* Recent results */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
          <div className="px-6 py-5 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent
                          flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg shadow-lg">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Recent Tests</h3>
                <p className="text-xs text-slate-400">Latest 20 runs</p>
              </div>
            </div>
            <button
              onClick={fetchTests}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
              title="Refresh"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>

          <div className="p-4 space-y-3 max-h-[520px] overflow-y-auto custom-scroll">
            {tests.length === 0 ? (
              <div className="py-16 text-center">
                <div className="text-5xl mb-4 opacity-20">⚡</div>
                <p className="text-slate-500 text-sm font-semibold">No tests yet</p>
                <p className="text-slate-600 text-xs mt-1">Run your first performance test!</p>
              </div>
            ) : (
              tests.map(test => (
                <PerformanceResultCard
                  key={test.id}
                  test={test}
                  onDelete={handleDelete}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Historical benchmark comparison chart */}
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
        <div className="px-6 py-5 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent
                        flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-lg shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Historical Benchmark Comparison</h3>
              <p className="text-xs text-slate-400">Latency trends across test runs for a URL</p>
            </div>
          </div>

          {/* URL picker */}
          <select
            id="perf-benchmark-url"
            value={benchmarkUrl}
            onChange={e => setBenchmarkUrl(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white max-w-xs
                       focus:outline-none focus:ring-2 focus:ring-indigo-500/50 cursor-pointer"
          >
            <option value="" className="bg-slate-900">— Select URL —</option>
            {uniqueUrls.map(u => (
              <option key={u} value={u} className="bg-slate-900">{u}</option>
            ))}
          </select>
        </div>

        <div className="p-6">
          {!benchmarkUrl ? (
            <div className="h-56 flex flex-col items-center justify-center gap-3 text-center">
              <div className="text-4xl opacity-20">📈</div>
              <p className="text-slate-500 text-sm font-semibold">Select a URL to view benchmark history</p>
              <p className="text-slate-600 text-xs">Run at least 2 tests on the same URL to see trend</p>
            </div>
          ) : chartData.length < 2 ? (
            <div className="h-56 flex flex-col items-center justify-center gap-3 text-center">
              <div className="text-4xl opacity-20">⏳</div>
              <p className="text-slate-500 text-sm font-semibold">Not enough data yet</p>
              <p className="text-slate-600 text-xs">Run at least 2 completed tests on this URL</p>
            </div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis
                    dataKey="name"
                    stroke="#475569"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                  />
                  <YAxis
                    stroke="#475569"
                    tickLine={false}
                    axisLine={false}
                    unit="ms"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
                    formatter={(val) => (
                      <span style={{ color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', fontSize: 10 }}>
                        {val}
                      </span>
                    )}
                  />
                  <Line
                    type="monotone" dataKey="avg" name="avg" stroke="#22d3ee"
                    strokeWidth={2} dot={{ fill: '#22d3ee', r: 3 }} activeDot={{ r: 5 }}
                  />
                  <Line
                    type="monotone" dataKey="p95" name="p95" stroke="#f59e0b"
                    strokeWidth={2} dot={{ fill: '#f59e0b', r: 3 }} activeDot={{ r: 5 }}
                    strokeDasharray="4 2"
                  />
                  <Line
                    type="monotone" dataKey="max" name="max" stroke="#f87171"
                    strokeWidth={1.5} dot={{ fill: '#f87171', r: 2.5 }} activeDot={{ r: 4 }}
                    strokeDasharray="2 4" opacity={0.7}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Benchmark summary stats */}
          {chartData.length >= 2 && (() => {
            const avgs = chartData.map(d => d.avg).filter((v): v is number => v !== null);
            const avgOfAvgs = avgs.length ? avgs.reduce((a, b) => a + b, 0) / avgs.length : null;
            const first = avgs[0], last = avgs[avgs.length - 1];
            const trend = (first && last) ? ((last - first) / first) * 100 : null;
            return (
              <div className="grid grid-cols-3 gap-3 mt-5">
                {[
                  { label: 'Avg of Avgs',   value: avgOfAvgs ? `${avgOfAvgs.toFixed(1)}ms` : 'N/A', color: 'text-cyan-400' },
                  { label: 'Test Runs',      value: String(chartData.length),  color: 'text-white' },
                  { label: 'Trend',
                    value: trend !== null ? `${trend > 0 ? '+' : ''}${trend.toFixed(1)}%` : 'N/A',
                    color: trend === null ? 'text-white' : trend > 10 ? 'text-red-400' : trend < -10 ? 'text-emerald-400' : 'text-amber-400'
                  },
                ].map(({ label, value, color }) => (
                  <div key={label} className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
                    <p className={`text-xl font-extrabold font-mono ${color}`}>{value}</p>
                    <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
