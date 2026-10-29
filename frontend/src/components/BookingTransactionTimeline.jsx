import React, { useState, useEffect } from "react";
import api from "../api/client";
import {
  Clock,
  User,
  ShieldCheck,
  Download,
  Link as LinkIcon,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Zap,
  Activity,
  FileText,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function BookingTransactionTimeline({ bookingId }) {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedHashes, setExpandedHashes] = useState({});

  const fetchTimeline = async () => {
    if (!bookingId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/bookings/${bookingId}/timeline`);
      setTimeline(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load transaction timeline.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, [bookingId]);

  const toggleHash = (id) => {
    setExpandedHashes((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleExportCSV = async () => {
    try {
      const res = await api.get(`/bookings/${bookingId}/timeline/export.csv`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `booking_${bookingId}_timeline.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("Failed to export transaction timeline as CSV.");
    }
  };

  if (loading) {
    return (
      <div className="p-6 bg-white rounded-2xl border border-gray-200 text-center text-xs text-gray-500">
        Loading cryptographic transaction timeline...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-700">
        {error}
      </div>
    );
  }

  if (!timeline || timeline.items.length === 0) {
    return (
      <div className="p-6 bg-white rounded-2xl border border-gray-200 text-center text-xs text-gray-400">
        No recorded lifecycle audit events for this booking yet.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-3xl border border-gray-200 p-6 shadow-2xs space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <LinkIcon className="w-4 h-4" />
            </span>
            <h3 className="text-base font-black text-gray-900 tracking-tight">
              Shared Transaction Timeline
            </h3>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              Hash-Chained Audit Ledger
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Immutable, append-only log of every decision and transition visible to both booker and lab managers.
          </p>
        </div>

        <button
          onClick={handleExportCSV}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-gray-300 hover:bg-gray-50 text-gray-700 font-bold text-xs shadow-2xs transition"
        >
          <Download className="w-3.5 h-3.5 text-gray-500" />
          Export Timeline (CSV)
        </button>
      </div>

      {/* Timeline Stream */}
      <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-indigo-100">
        {timeline.items.map((item, idx) => {
          const isExpanded = expandedHashes[item.id];
          const isSystem = item.actor_role === "system";

          return (
            <div key={item.id} className="relative group">
              {/* Stepper Dot */}
              <div className="absolute -left-6 top-1.5 w-5 h-5 rounded-full bg-white border-2 border-indigo-600 flex items-center justify-center text-[10px] font-bold text-indigo-700 shadow-2xs">
                {idx + 1}
              </div>

              {/* Event Card */}
              <div className="bg-gray-50/80 hover:bg-gray-50 border border-gray-200/90 rounded-2xl p-4 space-y-2 transition">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-xs text-gray-900 tracking-tight">
                      {item.action.replace(/_/g, " ")}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        item.actor_role === "admin"
                          ? "bg-purple-100 text-purple-800"
                          : item.actor_role === "owner"
                          ? "bg-amber-100 text-amber-800"
                          : item.actor_role === "manager"
                          ? "bg-blue-100 text-blue-800"
                          : item.actor_role === "user"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {item.actor_role}
                    </span>
                  </div>

                  <span className="text-[11px] text-gray-400 font-mono flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(item.timestamp).toLocaleString()}
                  </span>
                </div>

                {/* Actor & Reason */}
                <div className="text-xs text-gray-600 flex items-center gap-2">
                  <span className="font-semibold text-gray-700 flex items-center gap-1">
                    <User className="w-3 h-3 text-gray-400" />
                    {item.actor_name}
                  </span>
                </div>

                {item.rationale && (
                  <div className="p-2.5 bg-white border border-gray-200/80 rounded-xl text-xs text-gray-700 font-medium">
                    <span className="font-bold text-gray-900 block text-[10px] uppercase tracking-wider mb-0.5">
                      Reason / Rationale
                    </span>
                    "{item.rationale}"
                  </div>
                )}

                {/* Cryptographic Hash Verification Pill */}
                <div className="pt-1">
                  <button
                    onClick={() => toggleHash(item.id)}
                    className="text-[11px] text-indigo-600 hover:text-indigo-800 font-mono flex items-center gap-1 font-semibold"
                  >
                    <span>Audit Block #{item.id}</span>
                    <span className="text-gray-400">·</span>
                    <span className="truncate max-w-[140px] text-gray-500">
                      {item.hash.substring(0, 16)}...
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
                    )}
                  </button>

                  {isExpanded && (
                    <div className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-xl font-mono text-[10px] space-y-1.5 shadow-inner">
                      <div>
                        <span className="text-slate-400">Previous Hash (H_prev):</span>
                        <div className="break-all text-amber-300 font-bold">{item.prev_hash}</div>
                      </div>
                      <div>
                        <span className="text-slate-400">Entry Hash (SHA-256):</span>
                        <div className="break-all text-emerald-400 font-bold">{item.hash}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

