interface Server {
  id: number;
  name: string;
  url: string;
  email: string;
  last_status: string;
  last_check_time: string;
  uptime_24h: number;
}

interface ServerTableProps {
  servers: Server[];
  onDelete: (serverId: number) => void;
  onViewHistory: (server: Server) => void;
}

export default function ServerTable({ servers, onDelete, onViewHistory }: ServerTableProps) {
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

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    try {
      return new Date(timestamp + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'Invalid';
    }
  };

  if (servers.length === 0) {
    return (
      <div className="p-16 text-center">
        <div className="text-6xl mb-4 opacity-50">📭</div>
        <p className="text-slate-300 text-lg mb-2 font-semibold">No servers configured yet</p>
        <p className="text-slate-400 text-sm">Add your first server using the form above to get started</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-white/5 border-b border-white/10 sticky top-0">
          <tr>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Name</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Status</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Response</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Last Check</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Uptime (24h)</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Email</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {servers.map((server) => (
            <tr key={server.id} className="hover:bg-white/5 transition-colors duration-200 border-white/5">
              <td className="px-6 py-4">
                <div>
                  <p className="font-semibold text-white text-sm">{server.name}</p>
                  <a
                    href={server.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors truncate block mt-1"
                  >
                    {server.url}
                  </a>
                </div>
              </td>
              <td className="px-6 py-4">
                <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${getStatusBadgeColor(server.last_status)}`}>
                  <span className={`w-2 h-2 rounded-full ${getStatusDotColor(server.last_status)} animate-pulse`}></span>
                  {server.last_status}
                </span>
              </td>
              <td className="px-6 py-4 text-sm text-slate-400">
                {server.uptime_24h !== null ? '-' : 'N/A'}
              </td>
              <td className="px-6 py-4 text-sm text-slate-400 font-mono">
                {formatTime(server.last_check_time)}
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex-1 w-24">
                    <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          server.uptime_24h >= 99
                            ? 'bg-gradient-to-r from-emerald-400 to-emerald-500 shadow-lg shadow-emerald-400/50'
                            : server.uptime_24h >= 95
                            ? 'bg-gradient-to-r from-amber-400 to-amber-500 shadow-lg shadow-amber-400/50'
                            : 'bg-gradient-to-r from-red-400 to-red-500 shadow-lg shadow-red-400/50'
                        }`}
                        style={{ width: `${Math.min(server.uptime_24h, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-white font-mono w-12 text-right">{server.uptime_24h.toFixed(1)}%</span>
                </div>
              </td>
              <td className="px-6 py-4 text-sm text-slate-400">
                {server.email}
              </td>
              <td className="px-6 py-4">
                <div className="flex gap-2 items-center">
                  <button
                    onClick={() => onViewHistory(server)}
                    className="px-3 py-2 text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 rounded-lg hover:bg-cyan-500/30 transition-all duration-200 hover:border-cyan-400 whitespace-nowrap"
                  >
                    History
                  </button>
                  <button
                    onClick={() => onDelete(server.id)}
                    className="px-3 py-2 text-xs font-semibold bg-red-500/20 text-red-300 border border-red-400/50 rounded-lg hover:bg-red-500/30 transition-all duration-200 hover:border-red-400"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
