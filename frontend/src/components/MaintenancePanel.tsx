import React, { useState, useEffect } from 'react';
import { Calendar, Clock, Plus, Trash2, Server, CheckCircle2, AlertCircle } from 'lucide-react';

interface MaintenanceWindow {
  id: number;
  title: string;
  description: string;
  target_server_ids: string;
  start_time: string;
  end_time: string;
  status: 'Scheduled' | 'Active' | 'Completed';
}

interface ServerData {
  id: number;
  name: string;
}

export const MaintenancePanel: React.FC = () => {
  const [windows, setWindows] = useState<MaintenanceWindow[]>([]);
  const [servers, setServers] = useState<ServerData[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [targetId, setTargetId] = useState('all');
  const [startStr, setStartStr] = useState('');
  const [endStr, setEndStr] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      const [wRes, sRes] = await Promise.all([
        fetch('http://localhost:5000/api/maintenance'),
        fetch('http://localhost:5000/api/servers')
      ]);
      if (wRes.ok) setWindows(await wRes.json());
      if (sRes.ok) setServers(await sRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      // Ensure times are converted to ISO UTC for backend
      const startIso = new Date(startStr).toISOString();
      const endIso = new Date(endStr).toISOString();

      const res = await fetch('http://localhost:5000/api/maintenance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description: desc,
          target_server_ids: targetId,
          start_time: startIso,
          end_time: endIso
        })
      });
      if (res.ok) {
        setTitle('');
        setDesc('');
        setStartStr('');
        setEndStr('');
        fetchData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000/api'}/maintenance/${id}`, { method: 'DELETE' });
      if (res.ok) fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Active':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center gap-1"><AlertCircle className="w-3 h-3"/> Active</span>;
      case 'Scheduled':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center gap-1"><Calendar className="w-3 h-3"/> Scheduled</span>;
      case 'Completed':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1"><CheckCircle2 className="w-3 h-3"/> Completed</span>;
      default:
        return null;
    }
  };

  const formatTime = (iso: string) => new Date(iso).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
      {/* Creation Panel */}
      <div className="lg:col-span-1 space-y-6">
        <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/50 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-purple-500/20 rounded-lg border border-purple-500/30 text-purple-400">
              <Calendar className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-semibold text-slate-100">Schedule Maintenance</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Title</label>
              <input required type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Database Upgrade"
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-purple-500 transition-colors" />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
              <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="Details..." rows={2}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-purple-500 transition-colors" />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Target Servers</label>
              <select value={targetId} onChange={e => setTargetId(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-purple-500 transition-colors appearance-none">
                <option value="all">All Servers (Global Maintenance)</option>
                {servers.map(s => <option key={s.id} value={s.id.toString()}>{s.name}</option>)}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Start Time</label>
                <input required type="datetime-local" value={startStr} onChange={e => setStartStr(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-purple-500 transition-colors [color-scheme:dark]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">End Time</label>
                <input required type="datetime-local" value={endStr} onChange={e => setEndStr(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-purple-500 transition-colors [color-scheme:dark]" />
              </div>
            </div>

            <button type="submit" disabled={submitting}
              className="w-full mt-4 flex items-center justify-center gap-2 bg-purple-500 hover:bg-purple-600 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50">
              {submitting ? <Clock className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
              {submitting ? 'Scheduling...' : 'Schedule Window'}
            </button>
          </form>
        </div>
      </div>

      {/* List Panel */}
      <div className="lg:col-span-2">
        <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/50 rounded-2xl overflow-hidden flex flex-col h-full min-h-[400px]">
          <div className="p-6 border-b border-slate-700/50 flex justify-between items-center">
            <h2 className="text-xl font-semibold text-slate-100">Maintenance Windows</h2>
            <div className="text-sm text-slate-400">Total: {windows.length}</div>
          </div>
          
          <div className="p-6 flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex justify-center items-center h-full text-slate-400">Loading windows...</div>
            ) : windows.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
                <Calendar className="w-12 h-12 opacity-20" />
                <p>No maintenance scheduled</p>
              </div>
            ) : (
              <div className="space-y-4">
                {windows.map(w => (
                  <div key={w.id} className="p-4 rounded-xl border border-slate-700/50 bg-slate-800/80 hover:bg-slate-700/50 transition-colors group">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-slate-200 text-lg">{w.title}</h3>
                        {getStatusBadge(w.status)}
                      </div>
                      <button onClick={() => handleDelete(w.id)} className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    
                    {w.description && <p className="text-slate-400 text-sm mb-4">{w.description}</p>}
                    
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mt-3 pt-3 border-t border-slate-700/50">
                      <div className="flex items-center gap-2 text-slate-300">
                        <Server className="w-4 h-4 text-slate-500" />
                        <span>{w.target_server_ids === 'all' ? 'All Servers' : servers.find(s => s.id.toString() === w.target_server_ids)?.name || `ID: ${w.target_server_ids}`}</span>
                      </div>
                      <div className="flex flex-col text-slate-300">
                        <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Start</span>
                        {formatTime(w.start_time)}
                      </div>
                      <div className="flex flex-col text-slate-300">
                        <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">End</span>
                        {formatTime(w.end_time)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
