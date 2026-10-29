import React, { useState, useEffect } from "react";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import {
  Clock,
  FastForward,
  RotateCcw,
  Sparkles,
  ChevronUp,
  ChevronDown,
  Calendar,
} from "lucide-react";

export default function DemoClockControl() {
  const { user } = useAuthStore();
  const [clock, setClock] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchClock = async () => {
    try {
      const res = await api.get("/admin/clock");
      setClock(res.data);
    } catch (err) {
      // ignore if user lacks permission or not logged in
    }
  };

  useEffect(() => {
    if (user && ["admin", "manager", "owner"].includes(user.role)) {
      fetchClock();
      const interval = setInterval(fetchClock, 15000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const handleAdvance = async (seconds, label) => {
    setLoading(true);
    try {
      const res = await api.post("/admin/clock/advance", { seconds });
      setClock(res.data);
      // Trigger event or brief reload so current view refreshes time-based state
      window.dispatchEvent(new CustomEvent("openbench:clock-advanced", { detail: res.data }));
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to advance demo clock.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      const res = await api.post("/admin/clock/reset");
      setClock(res.data);
      window.dispatchEvent(new CustomEvent("openbench:clock-advanced", { detail: res.data }));
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to reset demo clock.");
    } finally {
      setLoading(false);
    }
  };

  if (!user || !["admin", "manager", "owner"].includes(user.role) || !clock) {
    return null;
  }

  const offsetHours = (clock.offset_seconds / 3600).toFixed(1);
  const isShifted = clock.offset_seconds !== 0;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="bg-slate-900 text-white rounded-2xl shadow-2xl border border-slate-700/80 overflow-hidden backdrop-blur-md">
        {/* Minimized Pill */}
        <div
          onClick={() => setExpanded(!expanded)}
          className="px-4 py-2.5 flex items-center gap-3 cursor-pointer hover:bg-slate-800 transition"
        >
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
              <Clock className="w-4 h-4" />
            </span>
            <div className="text-left">
              <div className="flex items-center gap-2">
                <span className="text-xs font-black tracking-tight text-white">
                  Demo Clock
                </span>
                {isShifted && (
                  <span className="text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.2 rounded">
                    +{offsetHours}h
                  </span>
                )}
              </div>
              <p className="text-[10px] text-slate-400 font-mono">
                {new Date(clock.app_now).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })} UTC
              </p>
            </div>
          </div>

          <button className="text-slate-400 hover:text-white ml-2">
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>

        {/* Expanded Controls for Judges & Admins */}
        {expanded && (
          <div className="p-4 border-t border-slate-800 space-y-3 bg-slate-950/70 w-72">
            <div className="text-[11px] text-slate-300 leading-snug">
              Fast-forward demo clock to test auto-releases, grace periods, overdue returns, and reminders.
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleAdvance(3600, "1 Hour")}
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition shadow-sm"
              >
                <FastForward className="w-3.5 h-3.5" /> +1 Hour
              </button>

              <button
                onClick={() => handleAdvance(86400, "1 Day")}
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition shadow-sm"
              >
                <Calendar className="w-3.5 h-3.5" /> +1 Day
              </button>
            </div>

            {isShifted && (
              <button
                onClick={handleReset}
                disabled={loading}
                className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs py-2 rounded-xl flex items-center justify-center gap-1.5 transition border border-slate-700"
              >
                <RotateCcw className="w-3.5 h-3.5 text-amber-400" /> Reset to Real UTC
              </button>
            )}

            <div className="pt-1 text-[10px] text-slate-400 text-center font-mono">
              Real UTC: {new Date(clock.real_utc).toLocaleTimeString()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

