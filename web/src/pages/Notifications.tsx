import { useState, useEffect, useCallback } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, LoadingState } from "../components/FeedbackStates";
import { Info, ShieldAlert, Trash2, X, Bell } from "lucide-react";
import { apiService } from "../services/api";
import { syncWebSocket } from "../services/websocket";

interface NotificationItem {
  id: number;
  category: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

export default function Notifications() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiService.getNotifications();
      setNotifications(data || []);
    } catch (err) {
      console.error("Failed to load notifications:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();

    const unsubCreated = syncWebSocket.subscribe("notification.created", (notif) => {
      if (notif && notif.id) {
        setNotifications((prev) => {
          if (prev.some((n) => n.id === notif.id)) return prev;
          return [notif, ...prev];
        });
      }
    });

    const unsubRead = syncWebSocket.subscribe("notification.read", (readData) => {
      if (readData) {
        if (readData.cleared_all) {
          setNotifications([]);
        } else if (readData.all) {
          setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
        } else if (readData.id) {
          setNotifications((prev) =>
            prev.map((n) => (n.id === readData.id ? { ...n, is_read: true } : n))
          );
        } else if (readData.deleted_id) {
          setNotifications((prev) => prev.filter((n) => n.id !== readData.deleted_id));
        }
      }
    });

    const unsubReconnect = syncWebSocket.onReconnect(() => {
      fetchNotifications();
    });

    return () => {
      unsubCreated();
      unsubRead();
      unsubReconnect();
    };
  }, [fetchNotifications]);

  const handleClearAll = async () => {
    if (notifications.length === 0) return;
    setClearing(true);
    try {
      await apiService.clearNotifications();
      setNotifications([]);
    } catch (err) {
      console.error("Failed to clear notifications:", err);
    } finally {
      setClearing(false);
    }
  };

  const handleMarkAsRead = async (id: number) => {
    try {
      await apiService.markNotificationAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      await apiService.deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      console.error("Failed to delete notification:", err);
      // Optimistically remove
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }
  };

  const formatTimestamp = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch {
      return "Recent";
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        description="Stay updated with security alerts, system updates, and scanning quotas."
        action={
          notifications.length > 0 ? (
            <button
              onClick={handleClearAll}
              disabled={clearing}
              className="flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 transition disabled:opacity-50"
            >
              <Trash2 size={16} />
              {clearing ? "Clearing..." : "Clear All"}
            </button>
          ) : undefined
        }
      />

      {loading ? (
        <LoadingState message="Loading notifications..." />
      ) : notifications.length === 0 ? (
        <EmptyState
          icon={<Bell size={28} className="text-violet-400" />}
          title="All caught up"
          description="You have no unread notifications or security alerts at this time."
        />
      ) : (
        <div className="space-y-4">
          {notifications.map((notif) => {
            const isAlert = notif.category === "security" || notif.category === "billing";
            return (
              <div
                key={notif.id}
                className={`flex items-start gap-4 rounded-2xl border p-5 bg-white/[0.01] transition group ${
                  isAlert ? "border-amber-500/20" : "border-white/10"
                }`}
              >
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                    isAlert
                      ? "bg-amber-500/10 text-amber-400"
                      : "bg-violet-600/10 text-violet-400"
                  }`}
                >
                  {isAlert ? <ShieldAlert size={18} /> : <Info size={18} />}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                    <div className="flex items-center gap-2">
                      {!notif.is_read && (
                        <span className="h-2 w-2 rounded-full bg-violet-400 shrink-0" title="Unread" />
                      )}
                      <h4 className={`font-semibold text-sm sm:text-base ${notif.is_read ? "text-slate-300" : "text-white"}`}>
                        {notif.title}
                      </h4>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 shrink-0">{formatTimestamp(notif.created_at)}</span>
                      {!notif.is_read && (
                        <button
                          onClick={() => handleMarkAsRead(notif.id)}
                          className="text-xs text-violet-400 hover:text-violet-300 px-2 py-0.5 rounded border border-violet-500/20 hover:bg-violet-500/10 transition"
                          title="Mark as read"
                        >
                          Mark read
                        </button>
                      )}
                      <button
                        onClick={() => handleDismiss(notif.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 transition"
                        title="Dismiss notification"
                        aria-label="Dismiss notification"
                      >
                        <X size={15} />
                      </button>
                    </div>
                  </div>
                  <p className="mt-1 text-sm text-slate-400 leading-relaxed">{notif.body}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
