import React, { useState, useEffect } from 'react';
import { Bell, Check, X, AlertCircle, Info, ShieldAlert, Wrench } from 'lucide-react';

interface Notification {
  id: number;
  server_id: number | null;
  server_name: string | null;
  severity: 'Info' | 'Warning' | 'Critical' | 'Recovery' | 'Maintenance' | 'SSL';
  message: string;
  created_at: string;
  is_read: number;
}

const severityConfig = {
  Info: { color: 'text-blue-400', bg: 'bg-blue-400/10', icon: Info },
  Warning: { color: 'text-amber-400', bg: 'bg-amber-400/10', icon: AlertCircle },
  Critical: { color: 'text-red-400', bg: 'bg-red-400/10', icon: ShieldAlert },
  Recovery: { color: 'text-emerald-400', bg: 'bg-emerald-400/10', icon: Check },
  Maintenance: { color: 'text-purple-400', bg: 'bg-purple-400/10', icon: Wrench },
  SSL: { color: 'text-orange-400', bg: 'bg-orange-400/10', icon: ShieldAlert },
};

export const NotificationCenter: React.FC<{ unreadCount: number; refreshCount: () => void }> = ({ unreadCount, refreshCount }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:5000/api/notifications?limit=20');
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
      }
    } catch (err) {
      console.error('Failed to fetch notifications', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen]);

  const markAsRead = async (id: number) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000/api'}/notifications/${id}/read`, { method: 'PUT' });
      if (res.ok) {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: 1 } : n));
        refreshCount();
      }
    } catch (err) {
      console.error('Failed to mark read', err);
    }
  };

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:bg-slate-700/50 transition-colors"
      >
        <Bell className="w-5 h-5 text-slate-300" />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center text-[10px] font-bold text-white border-2 border-slate-900">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-slate-800/95 backdrop-blur-xl border border-slate-700/50 rounded-xl shadow-2xl z-50">
          <div className="sticky top-0 bg-slate-800/95 backdrop-blur-xl border-b border-slate-700/50 p-3 flex justify-between items-center z-10">
            <h3 className="font-semibold text-slate-200">Notifications</h3>
            <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-slate-700 rounded-lg">
              <X className="w-4 h-4 text-slate-400" />
            </button>
          </div>
          
          <div className="p-2 space-y-2">
            {loading ? (
              <div className="text-center py-4 text-sm text-slate-400">Loading...</div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-4 text-sm text-slate-400">No notifications</div>
            ) : (
              notifications.map((n) => {
                const config = severityConfig[n.severity] || severityConfig.Info;
                const Icon = config.icon;
                return (
                  <div 
                    key={n.id} 
                    className={`p-3 rounded-lg border text-sm transition-colors ${
                      n.is_read ? 'bg-slate-800/30 border-slate-700/30' : 'bg-slate-800/80 border-slate-600 shadow-sm'
                    }`}
                    onClick={() => !n.is_read && markAsRead(n.id)}
                    style={{ cursor: n.is_read ? 'default' : 'pointer' }}
                  >
                    <div className="flex gap-3">
                      <div className={`mt-0.5 p-1.5 rounded-full ${config.bg} shrink-0`}>
                        <Icon className={`w-4 h-4 ${config.color}`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start gap-2">
                          <span className={`font-medium ${n.is_read ? 'text-slate-400' : 'text-slate-200'}`}>
                            {n.server_name || 'System'}
                          </span>
                          <span className="text-[10px] text-slate-500 whitespace-nowrap">
                            {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className={`mt-1 text-xs leading-relaxed ${n.is_read ? 'text-slate-500' : 'text-slate-300'}`}>
                          {n.message}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
