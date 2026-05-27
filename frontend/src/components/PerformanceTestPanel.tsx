import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const DURATION_OPTIONS = [
  { label: '10s',  value: 10  },
  { label: '30s',  value: 30  },
  { label: '60s',  value: 60  },
  { label: '120s', value: 120 },
];

interface Server {
  id: number;
  name: string;
  url: string;
}

interface PerformanceTestPanelProps {
  servers: Server[];
  onTestStarted: (testId: number) => void;
  onTestCompleted: () => void;
}

export default function PerformanceTestPanel({
  servers,
  onTestStarted,
  onTestCompleted,
}: PerformanceTestPanelProps) {
  const [url,           setUrl]           = useState('');
  const [vus,           setVus]           = useState(10);
  const [duration,      setDuration]      = useState(30);
  const [method,        setMethod]        = useState('GET');
  const [headersStr,    setHeadersStr]    = useState('');
  const [bodyStr,       setBodyStr]       = useState('');
  const [showAdvanced,  setShowAdvanced]  = useState(false);
  const [loading,       setLoading]       = useState(false);
  const [runningTestId, setRunningTestId] = useState<number | null>(null);
  const [progress,      setProgress]      = useState(0);
  const [statusMsg,     setStatusMsg]     = useState('');
  const [error,         setError]         = useState<string | null>(null);
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRef     = useRef<ReturnType<typeof setInterval> | null>(null);

  // Pre-fill URL from server list
  const handleServerPick = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const server = servers.find(s => s.id === Number(e.target.value));
    if (server) setUrl(server.url);
  };

  const stopPolling = () => {
    if (progressRef.current) clearInterval(progressRef.current);
    if (pollRef.current)     clearInterval(pollRef.current);
    progressRef.current = null;
    pollRef.current     = null;
  };

  useEffect(() => () => stopPolling(), []);

  const startProgress = (durationSec: number) => {
    setProgress(0);
    const step  = 100 / (durationSec * 4); // update every 250ms
    let elapsed = 0;
    progressRef.current = setInterval(() => {
      elapsed += step;
      setProgress(Math.min(elapsed, 95)); // cap at 95% until confirmed done
    }, 250);
  };

  const pollStatus = (testId: number) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/perf/tests/${testId}/status`);
        const { status, error_message } = res.data;
        if (status === 'completed') {
          stopPolling();
          setProgress(100);
          setStatusMsg('Test completed!');
          setTimeout(() => {
            setLoading(false);
            setRunningTestId(null);
            setProgress(0);
            setStatusMsg('');
            onTestCompleted();
          }, 800);
        } else if (status === 'failed') {
          stopPolling();
          setLoading(false);
          setRunningTestId(null);
          setProgress(0);
          setError(error_message || 'Test failed. Check if k6 is installed.');
        }
      } catch {
        // ignore transient poll errors
      }
    }, 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate headers JSON
    if (headersStr.trim()) {
      try { JSON.parse(headersStr); }
      catch { setError('Headers must be valid JSON (e.g. {"Authorization": "Bearer token"})'); return; }
    }

    setLoading(true);
    setStatusMsg('Launching k6 test...');

    try {
      const payload: Record<string, unknown> = {
        url,
        vus,
        duration_seconds: duration,
        method,
      };
      if (headersStr.trim()) payload.headers = headersStr.trim();
      if (bodyStr.trim())    payload.body    = bodyStr.trim();

      const res = await axios.post(`${API_URL}/perf/tests`, payload);
      const testId: number = res.data.test_id;
      setRunningTestId(testId);
      setStatusMsg(`Running: ${vus} VUs for ${duration}s…`);
      onTestStarted(testId);
      startProgress(duration);
      pollStatus(testId);
    } catch (err: any) {
      setLoading(false);
      setStatusMsg('');
      setError(err.response?.data?.error || 'Failed to start test. Is k6 installed?');
    }
  };

  const showBody = ['POST', 'PUT', 'PATCH'].includes(method);

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="px-6 py-5 border-b border-white/10 bg-gradient-to-r from-violet-500/10 to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-violet-500 to-purple-700 rounded-lg shadow-lg shadow-violet-500/30">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">New Performance Test</h3>
            <p className="text-xs text-slate-400 mt-0.5">Configure and launch a k6 load test</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-5">
        {/* Quick-fill from server list */}
        {servers.length > 0 && (
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Quick-fill from monitored server
            </label>
            <select
              id="perf-server-quickfill"
              onChange={handleServerPick}
              defaultValue=""
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white
                         focus:outline-none focus:ring-2 focus:ring-violet-500/50 cursor-pointer"
            >
              <option value="" className="bg-slate-900">— Select a server —</option>
              {servers.map(s => (
                <option key={s.id} value={s.id} className="bg-slate-900">{s.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* URL */}
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Target URL <span className="text-rose-400">*</span>
          </label>
          <input
            id="perf-url"
            type="text"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://api.example.com/endpoint"
            required
            disabled={loading}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                       placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50
                       disabled:opacity-50"
          />
        </div>

        {/* VUs + Duration + Method */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Virtual Users */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Virtual Users: <span className="text-violet-400 font-mono">{vus}</span>
            </label>
            <input
              id="perf-vus"
              type="range"
              min={1} max={50} step={1}
              value={vus}
              onChange={e => setVus(Number(e.target.value))}
              disabled={loading}
              className="w-full accent-violet-500 disabled:opacity-50"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>1</span><span>50</span>
            </div>
          </div>

          {/* Duration */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Duration
            </label>
            <div className="flex gap-1">
              {DURATION_OPTIONS.map(d => (
                <button
                  key={d.value}
                  type="button"
                  id={`perf-dur-${d.value}`}
                  onClick={() => setDuration(d.value)}
                  disabled={loading}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all duration-150
                    disabled:opacity-50
                    ${duration === d.value
                      ? 'bg-violet-600 text-white shadow-md shadow-violet-500/30'
                      : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white border border-white/10'
                    }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {/* Method */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              HTTP Method
            </label>
            <select
              id="perf-method"
              value={method}
              onChange={e => setMethod(e.target.value)}
              disabled={loading}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                         focus:outline-none focus:ring-2 focus:ring-violet-500/50 disabled:opacity-50"
            >
              {['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'].map(m => (
                <option key={m} value={m} className="bg-slate-900">{m}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Advanced options toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(v => !v)}
          className="text-xs font-semibold text-slate-400 hover:text-violet-400 transition-colors flex items-center gap-1"
        >
          <span>{showAdvanced ? '▾' : '▸'}</span>
          Advanced options (headers{showBody ? ', body' : ''})
        </button>

        {showAdvanced && (
          <div className="space-y-3 pl-3 border-l-2 border-violet-500/30">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Request Headers (JSON)
              </label>
              <textarea
                id="perf-headers"
                value={headersStr}
                onChange={e => setHeadersStr(e.target.value)}
                disabled={loading}
                rows={2}
                placeholder={'{"Authorization": "Bearer token", "Content-Type": "application/json"}'}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white
                           font-mono placeholder-slate-600 focus:outline-none focus:ring-2
                           focus:ring-violet-500/50 resize-none disabled:opacity-50"
              />
            </div>
            {showBody && (
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Request Body
                </label>
                <textarea
                  id="perf-body"
                  value={bodyStr}
                  onChange={e => setBodyStr(e.target.value)}
                  disabled={loading}
                  rows={3}
                  placeholder='{"key": "value"}'
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white
                             font-mono placeholder-slate-600 focus:outline-none focus:ring-2
                             focus:ring-violet-500/50 resize-none disabled:opacity-50"
                />
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400 flex items-start gap-2">
            <span className="text-lg leading-none">⚠</span>
            <span>{error}</span>
          </div>
        )}

        {/* Progress bar (running state) */}
        {loading && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400 font-medium animate-pulse">{statusMsg}</span>
              <span className="text-violet-400 font-mono">{Math.round(progress)}%</span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/10">
              <div
                className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            {runningTestId && (
              <p className="text-xs text-slate-500 font-mono">Test ID: #{runningTestId}</p>
            )}
          </div>
        )}

        {/* Submit */}
        <button
          id="perf-run-btn"
          type="submit"
          disabled={loading || !url}
          className={`w-full py-3 rounded-xl font-bold text-sm transition-all duration-200 flex items-center justify-center gap-2
            ${loading || !url
              ? 'bg-white/5 text-slate-500 cursor-not-allowed border border-white/10'
              : 'bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 hover:scale-[1.01] active:scale-[0.99]'
            }`}
        >
          {loading ? (
            <>
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Running k6 test…
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Run Performance Test
            </>
          )}
        </button>
      </form>
    </div>
  );
}
