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
}

interface HistoryModalProps {
  server: Server;
  history: HistoryItem[];
  onClose: () => void;
}

export default function HistoryModal({ server, history, onClose }: HistoryModalProps) {
  const getStatusBadgeColor = (status: string) => {
    if (status === 'UP') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50';
    if (status === 'DOWN') return 'bg-red-500/20 text-red-300 border border-red-400/50';
    if (status === 'WARNING') return 'bg-amber-500/20 text-amber-300 border border-amber-400/50';
    return 'bg-slate-500/20 text-slate-300 border border-slate-400/50';
  };

  const getStatusDotColor = (status: string) => {
    if (status === 'UP') return 'bg-emerald-400 shadow-lg shadow-emerald-400/50';
    if (status === 'DOWN') return 'bg-red-400 shadow-lg shadow-red-400/50';
    if (status === 'WARNING') return 'bg-amber-400 shadow-lg shadow-amber-400/50';
    return 'bg-slate-400';
  };

  const formatTime = (timestamp: string) => {
    if (!timestamp) return 'Never';
    try {
      // Convert SQLite format (YYYY-MM-DD HH:MM:SS) to ISO format (YYYY-MM-DDTHH:MM:SSZ)
      const isoTimestamp = timestamp.replace(' ', 'T') + 'Z';
      return new Date(isoTimestamp).toLocaleString([], {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-300">
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col animate-in scale-in-95 duration-300 border border-white/10">
        {/* Header */}
        <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 px-8 py-6 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-lg">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">{server.name} — Monitoring History</h3>
              <p className="text-xs text-slate-400 mt-1 font-mono">{server.url}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-2xl transition-colors p-1 hover:bg-white/10 rounded-lg"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {history.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center py-12">
                <div className="text-5xl mb-3 opacity-30">📭</div>
                <p className="text-slate-400 font-medium">No monitoring history available</p>
              </div>
            </div>
          ) : (
            <div className="overflow-y-auto flex-1">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-800 border-b border-white/10 z-20">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Response Time</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">HTTP Code</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {history.map((item, idx) => (
                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3 text-slate-300 font-mono text-xs">{formatTime(item.timestamp)}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-xs font-semibold ${getStatusBadgeColor(item.status)}`}>
                          <span className={`w-2 h-2 rounded-full ${getStatusDotColor(item.status)} animate-pulse`}></span>
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 font-mono">
                        {item.response_time !== null ? `${item.response_time.toFixed(3)}s` : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 font-mono font-semibold">
                        {item.http_status_code || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-white/5 border-t border-white/10 px-8 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg font-semibold text-sm transition-all duration-200 shadow-lg shadow-cyan-500/20"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
