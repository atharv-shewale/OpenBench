import React, { useState, useEffect } from "react";
import api from "../api/client";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  Camera,
  Layers,
  Sparkles,
  Info,
  Check,
  X,
  RefreshCw,
  Eye,
  Maximize2,
} from "lucide-react";

export default function SideBySideConditionViewer({ bookingId, initialData }) {
  const [data, setData] = useState(initialData || null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);

  const fetchComparison = async () => {
    if (!bookingId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/bookings/${bookingId}/condition-comparison`);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load condition comparison report.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData && bookingId) {
      fetchComparison();
    }
  }, [bookingId, initialData]);

  if (loading) {
    return (
      <div className="p-8 text-center bg-gray-50 rounded-3xl border border-gray-200">
        <RefreshCw className="w-6 h-6 text-brand-600 animate-spin mx-auto mb-2" />
        <p className="text-xs text-gray-500 font-medium">Loading condition records & signed photo assets...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-xs">
        <AlertTriangle className="w-5 h-5 text-rose-500 mb-1" />
        <p className="font-bold">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const pre = data.pre_report;
  const post = data.post_report;
  const diff = data.diff_result;

  const getConditionBadge = (cond) => {
    switch (cond) {
      case "GOOD":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">GOOD</span>;
      case "FAIR":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">FAIR</span>;
      case "DAMAGED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">DAMAGED</span>;
      case "BROKEN":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-200 text-red-900 border border-red-300">BROKEN</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-gray-100 text-gray-700">UNREPORTED</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Late Return Alert Banner */}
      {data.is_late && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900">
            <span className="font-bold text-amber-800 block text-sm">
              Overdue Return Recorded ({data.overdue_minutes} minutes late)
            </span>
            <p className="mt-0.5 text-amber-700 leading-relaxed">
              Scheduled slot ended at {new Date(data.slot_end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}.
              Per OpenBench governance non-negotiables, an overtime penalty proposal has been staged for human manager confirmation. No automated deduction is applied.
            </p>
          </div>
        </div>
      )}

      {/* Flagged for owner banner */}
      {data.flagged_for_owner && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center justify-between">
          <div className="flex items-center gap-2 text-rose-800 text-xs font-bold">
            <ShieldAlert className="w-5 h-5 text-rose-600" />
            <span>Flagged for Owner Inspection: Condition degradation or optical anomaly detected.</span>
          </div>
          <span className="bg-rose-100 text-rose-700 text-[10px] font-black uppercase px-2 py-0.5 rounded-full">
            Review Needed
          </span>
        </div>
      )}

      {/* Side-by-Side Condition Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* PRE-SESSION CONDITION (CHECK-IN) */}
        <div className="bg-white rounded-3xl border border-gray-200 overflow-hidden shadow-2xs">
          <div className="p-4 bg-gradient-to-r from-gray-50 to-emerald-50/20 border-b border-gray-100 flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-gray-400 block">
                Session Start Check
              </span>
              <h4 className="font-black text-gray-900 text-sm">Before-Condition Report (PRE)</h4>
            </div>
            {pre && getConditionBadge(pre.condition)}
          </div>

          <div className="p-5 space-y-4">
            {pre ? (
              <>
                <div className="text-xs text-gray-500 flex items-center justify-between">
                  <span>Checked in: {new Date(pre.created_at).toLocaleString()}</span>
                </div>

                {/* Checklist */}
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">
                    Pre-Flight Checklist Items
                  </span>
                  <div className="space-y-1.5 bg-gray-50 p-3 rounded-2xl border border-gray-100">
                    {Object.entries(pre.checklist_json || {}).length === 0 ? (
                      <p className="text-xs text-gray-400 italic">No checklist items recorded.</p>
                    ) : (
                      Object.entries(pre.checklist_json).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between text-xs">
                          <span className="text-gray-700 font-medium capitalize">
                            {key.replace(/_/g, " ")}
                          </span>
                          {val ? (
                            <span className="flex items-center gap-1 text-emerald-600 font-bold text-[11px]">
                              <Check className="w-3.5 h-3.5 stroke-[3]" /> Passed
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-rose-500 font-bold text-[11px]">
                              <X className="w-3.5 h-3.5 stroke-[3]" /> Flagged
                            </span>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Notes */}
                {pre.notes && (
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
                      Check-In Notes
                    </span>
                    <p className="text-xs text-gray-700 bg-gray-50 p-3 rounded-2xl border border-gray-100 italic">
                      "{pre.notes}"
                    </p>
                  </div>
                )}

                {/* Photos */}
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2 flex items-center gap-1">
                    <Camera className="w-3.5 h-3.5" /> Condition Photo Assets (Signed URLs)
                  </span>
                  {pre.signed_photo_urls && pre.signed_photo_urls.length > 0 ? (
                    <div className="grid grid-cols-2 gap-3">
                      {pre.signed_photo_urls.map((url, i) => (
                        <div
                          key={i}
                          onClick={() => setSelectedPhoto(url)}
                          className="relative group rounded-2xl overflow-hidden border border-gray-200 cursor-pointer bg-gray-100 aspect-video flex items-center justify-center shadow-2xs hover:border-brand-500 transition"
                        >
                          <img
                            src={url}
                            alt={`Pre-condition ${i}`}
                            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                          />
                          <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white text-xs font-bold gap-1">
                            <Maximize2 className="w-4 h-4" /> View Full
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-50 border border-dashed border-gray-200 rounded-2xl text-center text-xs text-gray-400">
                      No photos attached to pre-flight report.
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-xs text-gray-400">
                Awaiting check-in condition report.
              </div>
            )}
          </div>
        </div>

        {/* POST-SESSION CONDITION (RETURN) */}
        <div className="bg-white rounded-3xl border border-gray-200 overflow-hidden shadow-2xs">
          <div className="p-4 bg-gradient-to-r from-gray-50 to-indigo-50/20 border-b border-gray-100 flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-gray-400 block">
                Session Return Check
              </span>
              <h4 className="font-black text-gray-900 text-sm">After-Condition Report (POST)</h4>
            </div>
            {post && getConditionBadge(post.condition)}
          </div>

          <div className="p-5 space-y-4">
            {post ? (
              <>
                <div className="text-xs text-gray-500 flex items-center justify-between">
                  <span>Checked out: {new Date(post.created_at).toLocaleString()}</span>
                </div>

                {/* Checklist */}
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">
                    Return Handover Checklist Items
                  </span>
                  <div className="space-y-1.5 bg-gray-50 p-3 rounded-2xl border border-gray-100">
                    {Object.entries(post.checklist_json || {}).length === 0 ? (
                      <p className="text-xs text-gray-400 italic">No checklist items recorded.</p>
                    ) : (
                      Object.entries(post.checklist_json).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between text-xs">
                          <span className="text-gray-700 font-medium capitalize">
                            {key.replace(/_/g, " ")}
                          </span>
                          {val ? (
                            <span className="flex items-center gap-1 text-emerald-600 font-bold text-[11px]">
                              <Check className="w-3.5 h-3.5 stroke-[3]" /> Passed
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-rose-500 font-bold text-[11px]">
                              <X className="w-3.5 h-3.5 stroke-[3]" /> Flagged
                            </span>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Notes */}
                {post.notes && (
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
                      Return Notes
                    </span>
                    <p className="text-xs text-gray-700 bg-gray-50 p-3 rounded-2xl border border-gray-100 italic">
                      "{post.notes}"
                    </p>
                  </div>
                )}

                {/* Photos */}
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2 flex items-center gap-1">
                    <Camera className="w-3.5 h-3.5" /> Condition Photo Assets (Signed URLs)
                  </span>
                  {post.signed_photo_urls && post.signed_photo_urls.length > 0 ? (
                    <div className="grid grid-cols-2 gap-3">
                      {post.signed_photo_urls.map((url, i) => (
                        <div
                          key={i}
                          onClick={() => setSelectedPhoto(url)}
                          className="relative group rounded-2xl overflow-hidden border border-gray-200 cursor-pointer bg-gray-100 aspect-video flex items-center justify-center shadow-2xs hover:border-brand-500 transition"
                        >
                          <img
                            src={url}
                            alt={`Post-condition ${i}`}
                            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                          />
                          <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white text-xs font-bold gap-1">
                            <Maximize2 className="w-4 h-4" /> View Full
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-50 border border-dashed border-gray-200 rounded-2xl text-center text-xs text-gray-400">
                      No photos attached to return report.
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-xs text-gray-400">
                Session currently in progress or awaiting return handover.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── ADVISORY PHOTO-DIFF PANEL (PILLOW) ─────────────────────────────────── */}
      {diff && (
        <div className="bg-white rounded-3xl border border-gray-200 overflow-hidden shadow-sm">
          {/* Header Banner */}
          <div className="p-5 bg-gradient-to-r from-slate-900 to-indigo-950 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center text-indigo-300">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-extrabold text-sm tracking-tight text-white">
                    Advisory Photo-Diff Comparison
                  </h4>
                  <span className="bg-amber-400/20 text-amber-300 border border-amber-400/40 text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full">
                    {data.advisory_banner}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-0.5">
                  Automated computer vision comparison highlighting changed regions between pre- and post-session photos.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className={`px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 ${
                diff.is_significant
                  ? "bg-rose-500/20 border-rose-500/40 text-rose-200"
                  : "bg-emerald-500/20 border-emerald-500/40 text-emerald-200"
              }`}>
                <span>Variance: {diff.change_percentage}%</span>
              </div>
            </div>
          </div>

          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {/* Visual Diff Image */}
            {data.signed_diff_photo_url ? (
              <div
                onClick={() => setSelectedPhoto(data.signed_diff_photo_url)}
                className="relative group rounded-2xl overflow-hidden border border-gray-200 shadow-sm cursor-pointer aspect-video bg-black flex items-center justify-center"
              >
                <img
                  src={data.signed_diff_photo_url}
                  alt="Advisory Visual Diff"
                  className="w-full h-full object-contain group-hover:scale-102 transition"
                />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white text-xs font-bold gap-1.5">
                  <Maximize2 className="w-4 h-4" /> Expand Advisory Visual Diff
                </div>
              </div>
            ) : (
              <div className="p-8 bg-gray-50 border border-gray-200 rounded-2xl text-center text-xs text-gray-500">
                Visual diff asset unavailable or not generated.
              </div>
            )}

            {/* Explanation & Human Governance Notice */}
            <div className="space-y-4 text-xs">
              <div className="p-4 bg-indigo-50/50 border border-indigo-100 rounded-2xl space-y-2">
                <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-700 block">
                  Analysis Summary
                </span>
                <p className="text-gray-800 font-medium leading-relaxed">
                  {diff.summary}
                </p>
              </div>

              <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl space-y-2">
                <div className="flex items-center gap-1.5 font-bold text-gray-800">
                  <Info className="w-4 h-4 text-brand-600" />
                  <span>Human Oversight Protocol:</span>
                </div>
                <p className="text-gray-600 leading-relaxed text-[11px]">
                  Red highlights on the diff view represent detected structural or pixel shifts between check-in and checkout.
                  In accordance with OpenBench Non-Negotiable #3, <strong>all automated findings are strictly advisory</strong>. No penalties or strikes are issued without a human lab manager reviewing and confirming the condition report.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Image Lightbox Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-4"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="relative max-w-4xl w-full max-h-[90vh] flex flex-col items-center">
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute -top-10 right-0 text-white hover:text-gray-300 font-bold text-sm flex items-center gap-1"
            >
              <X className="w-5 h-5" /> Close
            </button>
            <img
              src={selectedPhoto}
              alt="Enlarged Condition Asset"
              className="max-h-[85vh] w-auto rounded-2xl object-contain border border-white/20 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </div>
  );
}
