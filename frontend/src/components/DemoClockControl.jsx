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
  AlertTriangle,
} from "lucide-react";

export default function DemoClockControl() {
  const { user } = useAuthStore();
  const [clock, setClock] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [confirmAdvance, setConfirmAdvance] = useState(null);

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
          <div className="p-4 border-t border-slate-800 space-y-3 bg-slate-950/70 w-80">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-200 leading-snug">
              ⚠️ <strong>Warning:</strong> Advancing the demo clock accelerates simulated time for all users, triggering auto-releases of unverified bookings past the 20-minute grace period and staging strike proposals. Real UTC is not modified.
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setConfirmAdvance({ seconds: 3600, label: "+1 Hour" })}
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition shadow-sm"
              >
                <FastForward className="w-3.5 h-3.5" /> +1 Hour
              </button>

              <button
                onClick={() => setConfirmAdvance({ seconds: 86400, label: "+1 Day" })}
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

      {/* Confirmation Dialog for Advancing Clock */}
      {confirmAdvance && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs text-gray-900">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-indigo-200 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-2xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                <FastForward className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-black text-gray-900">
                  Advance Demo Clock ({confirmAdvance.label})
                </h3>
                <p className="text-xs text-gray-600 leading-relaxed">
                  Fast-forwarding simulated time accelerates booking lifecycles.
                </p>
              </div>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 leading-snug">
              ⚠️ <strong>Notice:</strong> This will execute an immediate on-demand ghost-booking sweep, automatically releasing slots without check-in or telemetry after the 20-minute grace window.
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setConfirmAdvance(null)}
                disabled={loading}
                className="px-4 py-2 text-xs font-bold text-gray-600 hover:text-gray-800 rounded-xl hover:bg-gray-100 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  const s = confirmAdvance.seconds;
                  const l = confirmAdvance.label;
                  setConfirmAdvance(null);
                  handleAdvance(s, l);
                }}
                disabled={loading}
                className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition inline-flex items-center gap-1.5"
              >
                <FastForward className="w-3.5 h-3.5" /> Confirm Advance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

