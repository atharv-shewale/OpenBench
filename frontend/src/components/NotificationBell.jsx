import React, { useState, useEffect, useRef } from "react";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import {
  Bell,
  CheckCircle2,
  XCircle,
  Clock,
  ListOrdered,
  AlertTriangle,
  AlertOctagon,
  Info,
  CheckCheck,
  X,
} from "lucide-react";

export default function NotificationBell() {
  const { user } = useAuthStore();
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  const fetchNotifications = async () => {
    if (!user) return;
    try {
      const res = await api.get("/notifications");
      setNotifications(res.data);
    } catch (err) {
      // silently ignore polling failure
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 20000); // 20s poll
    return () => clearInterval(interval);
  }, [user]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleMarkAsRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      setLoading(true);
      await api.post("/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getNotifIcon = (type) => {
    switch (type) {
      case "APPROVAL":
        return <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />;
      case "REJECTION":
        return <XCircle className="w-4 h-4 text-rose-600 shrink-0" />;
      case "WAITLIST_MOVE":
        return <ListOrdered className="w-4 h-4 text-indigo-600 shrink-0" />;
      case "EXTENSION":
        return <Clock className="w-4 h-4 text-blue-600 shrink-0" />;
      case "REMINDER":
        return <Bell className="w-4 h-4 text-purple-600 shrink-0" />;
      case "OVERDUE_RETURN":
        return <AlertOctagon className="w-4 h-4 text-red-600 shrink-0" />;
      case "CANCELLATION":
        return <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />;
      default:
        return <Info className="w-4 h-4 text-gray-500 shrink-0" />;
    }
  };

  if (!user) return null;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-xl text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition"
        title="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-600 text-[10px] font-black text-white ring-2 ring-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white shadow-xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-sm text-gray-900">Notifications</span>
              {unreadCount > 0 && (
                <span className="bg-rose-100 text-rose-700 text-[11px] font-bold px-2 py-0.5 rounded-full">
                  {unreadCount} new
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                disabled={loading}
                className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-100">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500">
                <Bell className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                No notifications yet.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && handleMarkAsRead(n.id)}
                  className={`p-3.5 transition flex gap-3 cursor-pointer ${
                    n.is_read ? "bg-white hover:bg-gray-50" : "bg-brand-50/40 hover:bg-brand-50/70"
                  }`}
                >
                  <div className="mt-0.5">{getNotifIcon(n.notif_type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className={`text-xs ${n.is_read ? "font-bold text-gray-800" : "font-extrabold text-gray-900"}`}>
                        {n.title}
                      </p>
                      <span className="text-[10px] text-gray-400 whitespace-nowrap">
                        {new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">
                      {n.message}
                    </p>
                  </div>
                  {!n.is_read && (
                    <span className="w-2 h-2 rounded-full bg-brand-600 self-center shrink-0" />
                  )}
                </div>
              ))
            )}
          </div>

          {/* Footer note */}
          <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 text-[10px] text-gray-400 text-center">
            Synced with in-app event bus & email dispatch
          </div>
        </div>
      )}
    </div>
  );
}
