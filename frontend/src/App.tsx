import { useEffect, useState } from 'react';
import axios from 'axios';
import AddServerForm from './components/AddServerForm';
import ServerTable from './components/ServerTable';
import Toast from './components/Toast';
import HistoryModal from './components/HistoryModal';
import IncidentTimeline from './components/IncidentTimeline';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import PublicStatusPage from './components/PublicStatusPage';
import PerformanceDashboard from './components/PerformanceDashboard';

interface SystemStatus {
  status: string;
  total_servers: number;
  down_servers: number;
  warning_servers: number;
  active_incidents?: number;
}

interface Server {
  id: number;
  name: string;
  url: string;
  email: string;
  last_status: string;
  last_check_time: string;
  uptime_24h: number;
  last_response_time?: number | null;
  last_error_category?: string | null;
  last_severity?: string | null;
  active_incident?: any | null;
}

interface ToastMsg {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface HistoryItem {
  timestamp: string;
  status: string;
  response_time: number;
  http_status_code: number | null;
  error_category?: string | null;
  severity?: string | null;
}

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
  severity: string;
  status: 'active' | 'resolved';
}

type Tab = 'dashboard' | 'incidents' | 'analytics' | 'performance';

const API_URL = 'http://localhost:5000/api';

function App() {
  const [status,       setStatus]       = useState<SystemStatus | null>(null);
  const [servers,      setServers]      = useState<Server[]>([]);
  const [incidents,    setIncidents]    = useState<Incident[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [toasts,       setToasts]       = useState<ToastMsg[]>([]);
  const [activeTab,    setActiveTab]    = useState<Tab>('dashboard');
  const [selectedServerForHistory, setSelectedServerForHistory] = useState<Server | null>(null);
  const [historyData,  setHistoryData]  = useState<HistoryItem[]>([]);
  const [lastUpdated,  setLastUpdated]  = useState<Date>(new Date());
  const [statusSlug,   setStatusSlug]   = useState<string | null>(null);
  const [latestPerfTestId, setLatestPerfTestId] = useState<number | null>(null);

  // Derived stats
  const totalCount   = servers.length;
  const outagesCount = servers.filter(s => s.last_status === 'DOWN').length;
  const activeIncidentCount = incidents.filter(i => i.status === 'active').length;
  const operationalPct = totalCount > 0
    ? (((totalCount - outagesCount) / totalCount) * 100).toFixed(1)
    : '100.0';

  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4500);
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statusRes, serversRes, incidentsRes] = await Promise.all([
        axios.get(`${API_URL}/status`),
        axios.get(`${API_URL}/servers`),
        axios.get(`${API_URL}/incidents`),
      ]);
      setStatus(statusRes.data);
      setServers(serversRes.data);
      setIncidents(incidentsRes.data);
      setLastUpdated(new Date());
    } catch {
      addToast('Failed to connect to the monitoring API.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleAddServer = async (formData: { name: string; url: string; email: string }) => {
    try {
      await axios.post(`${API_URL}/servers`, formData);
      addToast('Server added successfully! 🎉', 'success');
      await fetchData();
    } catch (err: any) {
      addToast(err.response?.data?.error || 'Failed to add server', 'error');
    }
  };

  const handleDeleteServer = async (serverId: number) => {
    if (!window.confirm('Are you sure you want to delete this server?')) return;
    try {
      await axios.delete(`${API_URL}/servers/${serverId}`);
      addToast('Server deleted successfully', 'success');
      await fetchData();
    } catch {
      addToast('Failed to delete server', 'error');
    }
  };

  const handleViewHistory = async (server: Server) => {
    try {
      const res = await axios.get(`${API_URL}/history/${server.id}`);
      setSelectedServerForHistory(server);
      setHistoryData(res.data.history);
    } catch {
      addToast('Failed to load history', 'error');
    }
  };

  const handleViewStatus = (server: Server) => {
    const slug = server.name.toLowerCase().replace(/\s+/g, '-').replace(/_/g, '-');
    setStatusSlug(slug);
  };

  useEffect(() => {
    fetchData();

    const eventSource = new EventSource(`${API_URL}/events/stream`);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'connected') return;

        if (payload.type === 'server_update') {
          const updatedServer = payload.data;
          if (updatedServer.latest_check) {
            updatedServer.last_response_time  = updatedServer.latest_check.response_time;
            updatedServer.last_error_category = updatedServer.latest_check.error_category;
            updatedServer.last_severity       = updatedServer.latest_check.severity;
          }
          setServers(prev => {
            const exists = prev.some(s => s.id === updatedServer.id);
            if (!exists) return [...prev, updatedServer];
            return prev.map(s => s.id === updatedServer.id ? { ...s, ...updatedServer } : s);
          });
          setLastUpdated(new Date());
        }

        else if (payload.type === 'status_update') {
          setStatus(payload.data);
          setLastUpdated(new Date());
        }

        else if (payload.type === 'incident_created') {
          const { incident } = payload.data;
          if (incident) {
            setIncidents(prev => {
              const exists = prev.some(i => i.id === incident.id);
              if (exists) return prev;
              return [incident, ...prev];
            });
            addToast(`🚨 Incident: ${incident.server_name} — ${incident.error_category ?? incident.reason}`, 'error');
          }
        }

        else if (payload.type === 'incident_resolved') {
          const { incident, downtime_duration } = payload.data;
          if (incident) {
            setIncidents(prev =>
              prev.map(i => i.id === incident.id ? { ...i, ...incident } : i)
            );
            addToast(`Recovered: ${incident.server_name} (downtime: ${downtime_duration})`, 'success');
          }
        }

        else if (payload.type === 'perf_test_completed') {
          const { test_id, status, metrics } = payload.data ?? {};
          setLatestPerfTestId(test_id ?? null);
          if (status === 'completed' && metrics) {
            const wl = metrics.warning_level;
            const icon = wl === 'critical' ? '' : wl === 'warning' ? '' : wl === 'degraded' ? '' : '';
            addToast(`${icon} Load test #${test_id} completed — avg ${metrics.avg_latency_ms?.toFixed(1) ?? '?'}ms`, 'info');
          } else if (status === 'failed') {
            addToast(`Load test #${test_id} failed`, 'error');
          }
        }

      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    eventSource.onerror = () => {
      console.error('SSE connection error — will reconnect automatically.');
    };

    return () => eventSource.close();
  }, []);

  const getStatusColor = (s: string) => {
    if (s.includes('Operational')) return 'bg-gradient-to-br from-emerald-950 to-emerald-900/40 text-emerald-100 border-emerald-700';
    if (s.includes('Outage'))      return 'bg-gradient-to-br from-red-950 to-red-900/40 text-red-100 border-red-700';
    if (s.includes('Warning') || s.includes('Degraded')) return 'bg-gradient-to-br from-amber-950 to-amber-900/40 text-amber-100 border-amber-700';
    return 'bg-gradient-to-br from-slate-800 to-slate-900 text-slate-100 border-slate-600';
  };

  const getStatusIcon = (s: string) => {
    if (s.includes('Operational')) return '✓';
    if (s.includes('Outage'))      return '✕';
    if (s.includes('Warning') || s.includes('Degraded')) return '⚠';
    return '?';
  };

  const TABS: { id: Tab; label: string; badge?: number }[] = [
    { id: 'dashboard',   label: 'Dashboard' },
    { id: 'incidents',   label: 'Incidents', badge: activeIncidentCount > 0 ? activeIncidentCount : undefined },
    { id: 'analytics',  label: 'Analytics' },
    { id: 'performance', label: 'Performance ⚡' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 py-10 px-4 sm:px-6 lg:px-8">
      {/* Public status page overlay */}
      {statusSlug && (
        <PublicStatusPage slug={statusSlug} onBack={() => setStatusSlug(null)} />
      )}

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-10">
          <div className="flex items-center justify-between gap-6 flex-wrap">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl shadow-lg shadow-blue-500/20">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-4xl font-bold text-white tracking-tight">Statify</h1>
                <p className="text-slate-400 mt-0.5 text-sm font-medium">Real-time infrastructure observability platform</p>
              </div>
            </div>
            <div className="text-right bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live · Last Updated</div>
              <div className="text-2xl font-bold mt-1 font-mono text-white">{lastUpdated.toLocaleTimeString()}</div>
            </div>
          </div>
        </header>

        {/* Status banner */}
        {status && (
          <div className={`rounded-2xl border-2 p-6 mb-8 transition-all duration-300 ${getStatusColor(status.status)}`}>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-5">
                <div className="text-5xl font-bold opacity-15">{getStatusIcon(status.status)}</div>
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wider opacity-70 mb-0.5">System Status</p>
                  <h2 className="text-3xl font-bold">{status.status}</h2>
                  <p className="text-sm mt-1.5 opacity-70 font-medium">
                    <span className="font-bold">{status.total_servers}</span> services ·&nbsp;
                    <span className="font-bold">{status.down_servers}</span> down
                    {status.warning_servers > 0 && <> · <span className="font-bold">{status.warning_servers}</span> warning</>}
                    {(status.active_incidents ?? activeIncidentCount) > 0 && (
                      <> · <span className="font-bold text-red-300">{status.active_incidents ?? activeIncidentCount}</span> active incident{(status.active_incidents ?? activeIncidentCount) !== 1 ? 's' : ''}</>
                    )}
                  </p>
                </div>
              </div>
              <div className="text-6xl animate-pulse opacity-80">{getStatusIcon(status.status)}</div>
            </div>
          </div>
        )}

        {/* Metric widgets */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total Services',   value: totalCount,              color: 'text-white',       icon: '🖥️',  bg: 'from-indigo-500 to-purple-600' },
            { label: 'Operational',      value: totalCount - outagesCount, color: 'text-emerald-400', icon: '✅',  bg: 'from-emerald-500 to-teal-600' },
            { label: 'Active Outages',   value: outagesCount,            color: 'text-rose-500',    icon: '🔴',  bg: 'from-rose-500 to-red-600' },
            { label: 'Global SLA',       value: `${operationalPct}%`,    color: 'text-amber-400',   icon: '⚡',  bg: 'from-amber-500 to-orange-600' },
          ].map(({ label, value, color, icon, bg }) => (
            <div key={label} className="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-5 shadow-xl flex items-center gap-4">
              <div className={`p-3 bg-gradient-to-br ${bg} rounded-xl text-white shadow-md text-xl flex-shrink-0`}>{icon}</div>
              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</div>
                <div className={`text-3xl font-extrabold ${color} mt-0.5 font-mono`}>{value}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-white/5 rounded-xl p-1 border border-white/10 mb-8 w-fit">
          {TABS.map(tab => (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-white/15 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {tab.label}
              {tab.badge !== undefined && (
                <span className="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold bg-red-500 text-white">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            {/* Add server */}
            <div className="bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20 p-7 shadow-2xl">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-gradient-to-br from-green-400 to-emerald-600 rounded-lg">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-white">Add New Server</h2>
              </div>
              <AddServerForm onSubmit={handleAddServer} />
            </div>

            {/* Servers table */}
            <div className="bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20 overflow-hidden shadow-2xl">
              <div className="px-7 py-5 border-b border-white/10 bg-gradient-to-r from-white/10 to-transparent flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 3v2m6-2v2M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2V3m-6 0a2 2 0 00-2 2v2a2 2 0 104 0V5a2 2 0 00-2-2zm6 0a2 2 0 00-2 2v2a2 2 0 104 0V5a2 2 0 00-2-2z" />
                  </svg>
                  <h3 className="text-lg font-bold text-white">Monitored Services</h3>
                </div>
                {loading && (
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
                    <span className="text-xs text-slate-300 font-medium">Refreshing...</span>
                  </div>
                )}
              </div>
              <ServerTable
                servers={servers}
                onDelete={handleDeleteServer}
                onViewHistory={handleViewHistory}
                onViewStatus={handleViewStatus}
              />
            </div>
          </div>
        )}

        {activeTab === 'incidents' && (
          <IncidentTimeline incidents={incidents} />
        )}

        {activeTab === 'analytics' && (
          <AnalyticsDashboard servers={servers} />
        )}

        {activeTab === 'performance' && (
          <PerformanceDashboard
            servers={servers}
            latestCompletedTestId={latestPerfTestId}
          />
        )}
      </div>

      {/* Toast notifications */}
      <div className="fixed bottom-6 right-6 space-y-3 max-w-sm z-50">
        {toasts.map(toast => (
          <Toast key={toast.id} message={toast.message} type={toast.type} />
        ))}
      </div>

      {/* History modal */}
      {selectedServerForHistory && (
        <HistoryModal
          server={selectedServerForHistory}
          history={historyData}
          onClose={() => { setSelectedServerForHistory(null); setHistoryData([]); }}
        />
      )}
    </div>
  );
}

export default App;