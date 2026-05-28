interface SSLStatus {
  status: string;
  days_remaining: number | null;
  issuer: string | null;
}

interface Incident {
  id: number;
  started_at: string;
  reason: string;
  severity: string;
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
  active_incident?: Incident | null;
  is_maintenance?: boolean;
  ssl_status?: SSLStatus | null;
  is_public?: number;
  public_slug?: string;
}

interface ServerTableProps {
  servers: Server[];
  onDelete: (serverId: number) => void;
  onViewHistory: (server: Server) => void;
  onViewStatus?: (server: Server) => void;
  onTogglePublic?: (server: Server) => void;
}

export default function ServerTable({ servers, onDelete, onViewHistory, onViewStatus, onTogglePublic }: ServerTableProps) {

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

  const getSeverityBadge = (severity: string | null | undefined) => {
    if (!severity || severity === 'healthy') return null;
    if (severity === 'critical') return 'bg-red-500/15 text-red-300 border border-red-500/30';
    if (severity === 'warning')  return 'bg-amber-500/15 text-amber-300 border border-amber-500/30';
    return null;
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    try {
      return new Date(timestamp + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return 'Invalid'; }
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
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">SSL</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Issue</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Response</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Last Check</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Uptime (24h)</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {servers.map((server) => {
            const severityBadge = getSeverityBadge(server.last_severity);
            const hasIncident   = server.active_incident != null;

            return (
              <tr
                key={server.id}
                id={`server-row-${server.id}`}
                className={`hover:bg-white/5 transition-colors duration-200 ${
                  hasIncident ? 'bg-red-950/20' : ''
                }`}
              >
                {/* Name */}
                <td className="px-6 py-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-white text-sm">{server.name}</p>
                      {hasIncident && !server.is_maintenance && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                          INCIDENT
                        </span>
                      )}
                      {server.is_maintenance && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">
                          MAINTENANCE
                        </span>
                      )}
                    </div>
                    <a href={server.url} target="_blank" rel="noreferrer"
                      className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors truncate block mt-1 max-w-[180px]">
                      {server.url}
                    </a>
                  </div>
                </td>

                {/* Status */}
                <td className="px-6 py-4">
                  {server.is_maintenance ? (
                    <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-400/50">
                      <span className="w-2 h-2 rounded-full bg-purple-400 shadow-lg shadow-purple-400/50 animate-pulse" />
                      MAINTENANCE
                    </span>
                  ) : (
                    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${getStatusBadgeColor(server.last_status)}`}>
                      <span className={`w-2 h-2 rounded-full ${getStatusDotColor(server.last_status)} animate-pulse`} />
                      {server.last_status || 'PENDING'}
                    </span>
                  )}
                </td>

                {/* SSL Status */}
                <td className="px-6 py-4">
                  {server.ssl_status ? (
                    <div className="flex flex-col">
                      <span className={`inline-flex w-fit items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        server.ssl_status.status === 'Valid' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        server.ssl_status.status === 'Expiring Soon' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}>
                        {server.ssl_status.status}
                      </span>
                      {server.ssl_status.days_remaining != null && (
                        <span className="text-[10px] text-slate-500 mt-1 whitespace-nowrap">
                          {server.ssl_status.days_remaining} days left
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-slate-600 text-xs">—</span>
                  )}
                </td>

                {/* Issue (classified error) */}
                <td className="px-6 py-4">
                  {server.last_error_category && server.last_error_category !== 'Healthy' ? (
                    <div>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                        severityBadge ?? 'bg-slate-500/15 text-slate-300 border border-slate-500/30'
                      }`}>
                        {server.last_error_category}
                      </span>
                    </div>
                  ) : (
                    <span className="text-emerald-400/60 text-xs font-medium">Healthy</span>
                  )}
                </td>

                {/* Response time */}
                <td className="px-6 py-4 text-sm text-slate-400 font-mono">
                  {server.last_response_time != null
                    ? (
                      <span className={
                        server.last_response_time > 3 ? 'text-amber-400' :
                        server.last_response_time > 1 ? 'text-yellow-400/80' :
                        'text-slate-300'
                      }>
                        {server.last_response_time.toFixed(3)}s
                      </span>
                    )
                    : <span className="text-slate-600">N/A</span>
                  }
                </td>

                {/* Last check */}
                <td className="px-6 py-4 text-sm text-slate-400 font-mono">
                  {formatTime(server.last_check_time)}
                </td>

                {/* Uptime bar */}
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 w-20">
                      <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all duration-500 ${
                            server.uptime_24h >= 99
                              ? 'bg-gradient-to-r from-emerald-400 to-emerald-500 shadow-lg shadow-emerald-400/50'
                              : server.uptime_24h >= 95
                              ? 'bg-gradient-to-r from-amber-400 to-amber-500 shadow-lg shadow-amber-400/50'
                              : 'bg-gradient-to-r from-red-400 to-red-500 shadow-lg shadow-red-400/50'
                          }`}
                          style={{ width: `${Math.min(server.uptime_24h, 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className={`text-sm font-bold font-mono w-14 text-right ${
                      server.uptime_24h >= 99 ? 'text-emerald-400' :
                      server.uptime_24h >= 95 ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {server.uptime_24h.toFixed(1)}%
                    </span>
                  </div>
                </td>

                {/* Actions */}
                <td className="px-6 py-4">
                  <div className="flex gap-2 items-center flex-wrap">
                    <button
                      id={`btn-history-${server.id}`}
                      onClick={() => onViewHistory(server)}
                      className="px-3 py-1.5 text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-400/50
                                 rounded-lg hover:bg-cyan-500/30 transition-all duration-200 hover:border-cyan-400 whitespace-nowrap"
                    >
                      History
                    </button>
                    {onViewStatus && server.is_public === 1 && (
                      <button
                        id={`btn-status-${server.id}`}
                        onClick={() => onViewStatus(server)}
                        className="px-3 py-1.5 text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-400/50
                                   rounded-lg hover:bg-indigo-500/30 transition-all duration-200 hover:border-indigo-400 whitespace-nowrap"
                      >
                        Public Page
                      </button>
                    )}
                    {onTogglePublic && (
                      <button
                        id={`btn-toggle-public-${server.id}`}
                        onClick={() => onTogglePublic(server)}
                        className={`px-3 py-1.5 text-xs font-semibold border rounded-lg transition-all duration-200 whitespace-nowrap ${
                          server.is_public === 1 
                            ? 'bg-amber-500/20 text-amber-300 border-amber-400/50 hover:bg-amber-500/30 hover:border-amber-400' 
                            : 'bg-slate-500/20 text-slate-300 border-slate-400/50 hover:bg-slate-500/30 hover:border-slate-400'
                        }`}
                      >
                        {server.is_public === 1 ? 'Disable Public' : 'Enable Public'}
                      </button>
                    )}
                    <button
                      id={`btn-delete-${server.id}`}
                      onClick={() => onDelete(server.id)}
                      className="px-3 py-1.5 text-xs font-semibold bg-red-500/20 text-red-300 border border-red-400/50
                                 rounded-lg hover:bg-red-500/30 transition-all duration-200 hover:border-red-400"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
