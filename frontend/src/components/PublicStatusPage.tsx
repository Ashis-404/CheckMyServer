import { useEffect, useState } from 'react';
import { ArrowLeft, CheckCircle2, AlertTriangle, XCircle, Clock, Activity } from 'lucide-react';
import axios from 'axios';

interface PublicStatusProps {
  slug: string;
  onBack: () => void;
}

interface PublicStatusData {
  name: string;
  status: string;
  last_check_time: string;
  uptime_30d: number | null;
  active_incident: any | null;
  latency_trend: { hour: string; avg_rt: number; checks: number }[];
}

export default function PublicStatusPage({ slug, onBack }: PublicStatusProps) {
  const [data, setData] = useState<PublicStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:5000/api'}/public/status/${slug}`);
        setData(res.data);
      } catch (err: any) {
        setError(err.response?.data?.error || 'Failed to load status');
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
    // Refresh every 60s
    const interval = setInterval(fetchStatus, 60000);
    return () => clearInterval(interval);
  }, [slug]);

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950 flex flex-col items-center justify-center">
        <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 font-medium">Loading status...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <AlertTriangle className="w-16 h-16 text-slate-600 mb-4" />
        <h1 className="text-2xl font-bold text-slate-200 mb-2">Status Page Not Found</h1>
        <p className="text-slate-400 mb-8 max-w-md">{error || 'This public status page does not exist or is not set to public.'}</p>
        <button onClick={onBack} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Return to Dashboard
        </button>
      </div>
    );
  }

  const isUp = data.status === 'UP';
  const isWarn = data.status === 'WARNING';
  
  const statusColor = isUp ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 
                     isWarn ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' : 
                     'text-red-400 bg-red-500/10 border-red-500/20';
                     
  const StatusIcon = isUp ? CheckCircle2 : isWarn ? AlertTriangle : XCircle;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 py-8 md:py-16">
        <button onClick={onBack} className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-12">
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <header className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">{data.name}</h1>
          <p className="text-slate-400 text-lg">System Status Report</p>
        </header>

        {/* Big Status Banner */}
        <div className={`p-8 md:p-12 rounded-3xl border flex flex-col items-center justify-center text-center mb-12 transition-colors ${statusColor}`}>
          <StatusIcon className="w-20 h-20 mb-6" />
          <h2 className="text-4xl font-bold mb-2">
            {isUp ? 'All Systems Operational' : isWarn ? 'Degraded Performance' : 'Major Outage'}
          </h2>
          <p className="opacity-80 text-lg">
            Last checked: {new Date(data.last_check_time + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>

        {/* Active Incident */}
        {data.active_incident && (
          <div className="bg-red-950/30 border border-red-500/30 rounded-2xl p-6 mb-12">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-red-500/20 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-red-100 mb-2">Active Incident</h3>
                <p className="text-red-200/80 mb-4">{data.active_incident.reason}</p>
                <div className="text-sm text-red-300/60 font-mono">
                  Started: {new Date(data.active_incident.started_at + 'Z').toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 flex items-center gap-6">
            <div className="p-4 bg-emerald-500/10 rounded-2xl text-emerald-400">
              <Activity className="w-8 h-8" />
            </div>
            <div>
              <p className="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-1">30-Day Uptime</p>
              <div className="text-4xl font-bold text-white">
                {data.uptime_30d ? `${data.uptime_30d}%` : 'N/A'}
              </div>
            </div>
          </div>
          
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 flex items-center gap-6">
            <div className="p-4 bg-blue-500/10 rounded-2xl text-blue-400">
              <Clock className="w-8 h-8" />
            </div>
            <div>
              <p className="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-1">Average Latency (24h)</p>
              <div className="text-4xl font-bold text-white">
                {data.latency_trend.length > 0 
                  ? `${(data.latency_trend.reduce((acc, curr) => acc + curr.avg_rt, 0) / data.latency_trend.length).toFixed(2)}s` 
                  : 'N/A'}
              </div>
            </div>
          </div>
        </div>

        <footer className="text-center text-slate-500 text-sm">
          Powered by CheckMyServer
        </footer>
      </div>
    </div>
  );
}
