import { useEffect, useState } from 'react';
import axios from 'axios';
import AddServerForm from './components/AddServerForm';
import ServerTable from './components/ServerTable';
import Toast from './components/Toast';
import HistoryModal from './components/HistoryModal';

interface SystemStatus {
  status: string;
  total_servers: number;
  down_servers: number;
  warning_servers: number;
}

interface Server {
  id: number;
  name: string;
  url: string;
  email: string;
  last_status: string;
  last_check_time: string;
  uptime_24h: number;
}

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface HistoryItem {
  timestamp: string;
  status: string;
  response_time: number;
  http_status_code: number | null;
}

const API_URL = 'http://localhost:5000/api';

function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [selectedServerForHistory, setSelectedServerForHistory] = useState<Server | null>(null);
  const [historyData, setHistoryData] = useState<HistoryItem[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statusRes, serversRes] = await Promise.all([
        axios.get(`${API_URL}/status`),
        axios.get(`${API_URL}/servers`)
      ]);
      setStatus(statusRes.data);
      setServers(serversRes.data);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error(err);
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
      const errorMessage = err.response?.data?.error || 'Failed to add server';
      addToast(errorMessage, 'error');
    }
  };

  const handleDeleteServer = async (serverId: number) => {
    if (!window.confirm('Are you sure you want to delete this server?')) {
      return;
    }
    try {
      await axios.delete(`${API_URL}/servers/${serverId}`);
      addToast('Server deleted successfully', 'success');
      await fetchData();
    } catch (err: any) {
      addToast('Failed to delete server', 'error');
    }
  };

  const handleViewHistory = async (server: Server) => {
    try {
      const response = await axios.get(`${API_URL}/history/${server.id}`);
      setSelectedServerForHistory(server);
      setHistoryData(response.data.history);
    } catch (err: any) {
      addToast('Failed to load history', 'error');
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    if (status.includes('Operational')) return 'bg-gradient-to-br from-emerald-50 to-emerald-100 text-emerald-900 border-emerald-300 shadow-md';
    if (status.includes('Outage')) return 'bg-gradient-to-br from-red-50 to-red-100 text-red-900 border-red-300 shadow-md';
    if (status.includes('Warning') || status.includes('Degraded')) return 'bg-gradient-to-br from-amber-50 to-amber-100 text-amber-900 border-amber-300 shadow-md';
    return 'bg-gradient-to-br from-gray-50 to-gray-100 text-gray-900 border-gray-300 shadow-md';
  };

  const getStatusIcon = (status: string) => {
    if (status.includes('Operational')) return '✓';
    if (status.includes('Outage')) return '✕';
    if (status.includes('Warning') || status.includes('Degraded')) return '⚠';
    return '?';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-12">
          <div className="flex items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-4 mb-3">
                <div className="p-3 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl shadow-lg">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-4xl font-bold text-white tracking-tight">Statify</h1>
                  <p className="text-slate-400 mt-1 text-sm font-medium">Real-time infrastructure surveillance</p>
                </div>
              </div>
            </div>
            <div className="text-right bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 text-white">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Updated</div>
              <div className="text-2xl font-bold mt-1 font-mono">{lastUpdated.toLocaleTimeString()}</div>
            </div>
          </div>
        </header>

        {/* Overall Status Card */}
        {status && (
          <div className={`rounded-2xl border-2 p-8 mb-10 transition-all duration-300 ${getStatusColor(status.status)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className={`text-6xl font-bold opacity-20`}>
                  {getStatusIcon(status.status)}
                </div>
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wider opacity-75 mb-1">System Status</p>
                  <h2 className="text-4xl font-bold">{status.status}</h2>
                  <p className="text-sm mt-3 opacity-80 font-medium">
                    <span className="font-semibold">{status.total_servers}</span> services • 
                    <span className="ml-1 font-semibold">{status.down_servers}</span> down 
                    {status.warning_servers > 0 && <>• <span className="font-semibold">{status.warning_servers}</span> warning</>}
                  </p>
                </div>
              </div>
              <div className="text-right">
                {status.down_servers === 0 && status.warning_servers === 0 ? (
                  <div className="text-7xl animate-pulse">✓</div>
                ) : status.down_servers > 0 ? (
                  <div className="text-7xl animate-pulse">✕</div>
                ) : (
                  <div className="text-7xl animate-pulse">⚠</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Add Server Section */}
        <div className="bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20 p-8 mb-10 shadow-2xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-gradient-to-br from-green-400 to-emerald-600 rounded-lg">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white">Add New Server</h2>
          </div>
          <AddServerForm onSubmit={handleAddServer} />
        </div>

        {/* Servers Table Section */}
        <div className="bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20 overflow-hidden shadow-2xl">
          <div className="px-8 py-6 border-b border-white/10 bg-gradient-to-r from-white/10 to-transparent flex justify-between items-center">
            <div className="flex items-center gap-3">
              <svg className="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2V3m-6 0a2 2 0 00-2 2v2a2 2 0 104 0V5a2 2 0 00-2-2zm6 0a2 2 0 00-2 2v2a2 2 0 104 0V5a2 2 0 00-2-2z" />
              </svg>
              <h3 className="text-xl font-bold text-white">Monitored Services</h3>
            </div>
            {loading && (
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></span>
                <span className="text-xs text-slate-300 font-medium">Refreshing...</span>
              </div>
            )}
          </div>
          <ServerTable 
            servers={servers} 
            onDelete={handleDeleteServer}
            onViewHistory={handleViewHistory}
          />
        </div>

        {/* Toast Notifications */}
        <div className="fixed bottom-6 right-6 space-y-3 max-w-sm z-50">
          {toasts.map(toast => (
            <Toast key={toast.id} message={toast.message} type={toast.type} />
          ))}
        </div>

        {/* History Modal */}
        {selectedServerForHistory && (
          <HistoryModal 
            server={selectedServerForHistory}
            history={historyData}
            onClose={() => {
              setSelectedServerForHistory(null);
              setHistoryData([]);
            }}
          />
        )}
      </div>
    </div>
  );
}

export default App;