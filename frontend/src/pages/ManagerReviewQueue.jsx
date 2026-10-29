import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import WhyThisOutcomeCard from "../components/WhyThisOutcomeCard";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  User,
  Building,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Layers,
  Sparkles,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  Filter,
  Check,
  X,
  ListOrdered,
} from "lucide-react";

export default function ManagerReviewQueue() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Filters
  const [selectedLab, setSelectedLab] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  // Modals & Active Actions
  const [rejectItem, setRejectItem] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectSubmitting, setRejectSubmitting] = useState(false);

  const [approveItem, setApproveItem] = useState(null);
  const [approveNote, setApproveNote] = useState("");
  const [isOverride, setIsOverride] = useState(false);
  const [approveSubmitting, setApproveSubmitting] = useState(false);

  const [waitlistSubmitting, setWaitlistSubmitting] = useState(null);

  // Toggled breakdown cards per booking id
  const [expandedDetails, setExpandedDetails] = useState({});

  const isOwner = user && (user.role === "owner" || user.role === "admin");

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/bookings/review-queue");
      setItems(res.data);
    } catch (err) {
      if (err.response?.status === 403) {
        setError("Access Denied: Lab Manager or Lab Owner role required.");
      } else {
        setError(err.response?.data?.detail || "Failed to load review queue.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && !["owner", "manager", "admin"].includes(user.role)) {
      navigate("/dashboard");
      return;
    }
    fetchQueue();
  }, [user]);

  const toggleDetails = (id) => {
    setExpandedDetails((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  // Distinct Labs for filtering
  const distinctLabs = Array.from(
    new Set(items.map((i) => JSON.stringify({ id: i.lab_id, name: i.lab_name })))
  ).map((s) => JSON.parse(s));

  const filteredItems = items.filter((item) => {
    if (selectedLab !== "all" && item.lab_id !== parseInt(selectedLab)) {
      return false;
    }
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchUser = item.user_name?.toLowerCase().includes(q);
      const matchOrg = item.user_organisation?.toLowerCase().includes(q);
      const matchEquip = item.equipment_name?.toLowerCase().includes(q);
      const matchLab = item.lab_name?.toLowerCase().includes(q);
      const matchId = String(item.booking.id).includes(q);
      if (!matchUser && !matchOrg && !matchEquip && !matchLab && !matchId) {
        return false;
      }
    }
    return true;
  });

  // Action: Approve
  const handleConfirmApprove = async () => {
    if (!approveItem) return;
    setApproveSubmitting(true);
    try {
      await api.post(`/bookings/${approveItem.booking.id}/approve`, {
        note: approveNote || (isOverride ? "Approved via Owner Override" : "Approved by Manager"),
        override: isOverride,
        decision_reason: {
          approved_by_role: user.role,
          override_applied: isOverride,
          timestamp: new Date().toISOString(),
        },
      });
      setActionSuccess(
        `Booking #${approveItem.booking.id} (${approveItem.user_name}) was successfully approved.`
      );
      setApproveItem(null);
      setApproveNote("");
      setIsOverride(false);
      fetchQueue();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to approve booking.");
    } finally {
      setApproveSubmitting(false);
    }
  };

  // Action: Reject (mandatory reason)
  const handleConfirmReject = async () => {
    if (!rejectItem) return;
    if (!rejectReason.trim()) {
      alert("A specific rejection reason is required for reviewable transparency.");
      return;
    }
    setRejectSubmitting(true);
    try {
      await api.post(`/bookings/${rejectItem.booking.id}/reject`, {
        note: rejectReason.trim(),
        decision_reason: {
          rejected_by_role: user.role,
          reason: rejectReason.trim(),
          timestamp: new Date().toISOString(),
        },
      });
      setActionSuccess(`Booking #${rejectItem.booking.id} was rejected.`);
      setRejectItem(null);
      setRejectReason("");
      fetchQueue();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to reject booking.");
    } finally {
      setRejectSubmitting(false);
    }
  };

  // Action: Move to Waitlist
  const handleMoveToWaitlist = async (item) => {
    if (
      !window.confirm(
        `Move Booking #${item.booking.id} for "${item.user_name}" to the ranked waitlist? Held credits will be unlocked until a spot opens.`
      )
    ) {
      return;
    }
    setWaitlistSubmitting(item.booking.id);
    try {
      const res = await api.post(`/bookings/${item.booking.id}/move-to-waitlist`);
      setActionSuccess(
        `Booking #${item.booking.id} moved to waitlist queue with priority score ${res.data.ranking_score?.toFixed(
          1
        )}.`
      );
      fetchQueue();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to move booking to waitlist.");
    } finally {
      setWaitlistSubmitting(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-black text-gray-900 tracking-tight">
                Manager Review Queue
              </h1>
              <span className="bg-brand-50 text-brand-700 border border-brand-200 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                {items.length} Pending
              </span>
            </div>
            <p className="text-gray-500 text-sm mt-1">
              Review session requests with automated eligibility scores, usage history, and priority allocations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchQueue}
              className="inline-flex items-center gap-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-bold px-4 py-2 rounded-xl text-sm transition shadow-2xs"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link
              to="/owner/resources"
              className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white font-bold px-4 py-2 rounded-xl text-sm transition shadow-sm shadow-brand-500/20"
            >
              <Layers className="w-4 h-4" /> Lab Inventory
            </Link>
          </div>
        </div>

        {/* Action alert banner */}
        {actionSuccess && (
          <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-between text-emerald-800 text-sm font-medium">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <span>{actionSuccess}</span>
            </div>
            <button
              onClick={() => setActionSuccess(null)}
              className="text-emerald-700 hover:text-emerald-900 text-xs font-bold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Filter & Search Bar */}
        <div className="bg-white border border-gray-200 rounded-2xl p-4 mb-6 shadow-2xs flex flex-col sm:flex-row gap-4 items-center justify-between">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search user, machine, lab, or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-xs font-semibold text-gray-600">Lab:</span>
            <select
              value={selectedLab}
              onChange={(e) => setSelectedLab(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded-xl text-xs py-2 px-3 text-gray-700 font-medium focus:ring-2 focus:ring-brand-500"
            >
              <option value="all">All Labs ({items.length})</option>
              {distinctLabs.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Content Area */}
        {loading && items.length === 0 ? (
          <div className="bg-white rounded-3xl border border-gray-200 p-12 text-center">
            <RefreshCw className="w-8 h-8 text-brand-500 animate-spin mx-auto mb-3" />
            <p className="text-gray-600 font-medium text-sm">Evaluating queue and verifying eligibility...</p>
          </div>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center text-rose-700 text-sm">
            <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
            <p className="font-bold">{error}</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="bg-white rounded-3xl border border-gray-200 p-12 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-gray-900">Review Queue is Clear!</h3>
            <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1">
              There are no pending booking requests requiring manager confirmation across your managed labs.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {filteredItems.map((item) => {
              const b = item.booking;
              const isEligible = item.eligibility_evaluation?.is_eligible;
              const isExpanded = !!expandedDetails[b.id];
              const score = item.waitlist_score_breakdown?.total_ranking_score ?? 0;

              return (
                <div
                  key={b.id}
                  className="bg-white rounded-3xl border border-gray-200 overflow-hidden shadow-2xs hover:border-gray-300 transition"
                >
                  {/* Top Header Card */}
                  <div className="p-6 border-b border-gray-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2.5">
                        <span className="font-black text-gray-900 text-base">
                          Booking #{b.id}
                        </span>
                        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-700">
                          {item.equipment_name}
                        </span>
                        <span className="text-xs font-medium text-gray-500">
                          in <strong className="text-gray-700">{item.lab_name}</strong>
                        </span>

                        {item.is_prime_slot && (
                          <span className="bg-amber-100 text-amber-800 text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1">
                            <Sparkles className="w-3 h-3" /> Prime Peak Slot
                          </span>
                        )}

                        {b.priority_tier && (
                          <span className="bg-indigo-50 text-indigo-700 border border-indigo-200 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
                            {b.priority_tier} Tier
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 pt-1">
                        <span className="flex items-center gap-1 font-medium text-gray-700">
                          <Clock className="w-3.5 h-3.5 text-gray-400" />
                          {new Date(b.slot_start).toLocaleDateString()} ·{" "}
                          {new Date(b.slot_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} -{" "}
                          {new Date(b.slot_end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                        <span>•</span>
                        <span>
                          Credits Required:{" "}
                          <strong className="text-amber-700 font-bold">{b.credit_cost} cr</strong>
                        </span>
                        {b.group_name && (
                          <>
                            <span>•</span>
                            <span>
                              Cohort: <strong className="text-gray-700">{b.group_name}</strong>
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Eligibility & Score Badges */}
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold ${
                          isEligible
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-rose-50 text-rose-700 border-rose-200"
                        }`}
                      >
                        {isEligible ? (
                          <>
                            <ShieldCheck className="w-4 h-4 text-emerald-600" />
                            <span>Eligible</span>
                          </>
                        ) : (
                          <>
                            <ShieldAlert className="w-4 h-4 text-rose-600" />
                            <span>Ineligible ({item.eligibility_evaluation?.reasons_failed?.length || 1})</span>
                          </>
                        )}
                      </div>

                      <div className="bg-indigo-50 border border-indigo-100 text-indigo-700 px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5">
                        <ListOrdered className="w-4 h-4 text-indigo-600" />
                        <span>Score: {score.toFixed(1)}</span>
                      </div>
                    </div>
                  </div>

                  {/* User Profile & History Row */}
                  <div className="p-6 bg-gray-50/60 grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
                    {/* Booker Identity */}
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block">
                        Booker Profile
                      </span>
                      <div className="font-bold text-gray-900 text-sm flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-400" />
                        {item.user_name}
                      </div>
                      <p className="text-gray-500">{item.user_email}</p>
                      <p className="text-gray-600 font-medium">
                        {item.user_organisation || "Individual Student / Maker"}
                      </p>
                    </div>

                    {/* Booker History */}
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block">
                        Past Session History
                      </span>
                      <div className="grid grid-cols-2 gap-2 text-gray-700">
                        <div>
                          <span className="text-gray-400 block text-[11px]">Completed:</span>
                          <span className="font-bold text-gray-900">
                            {item.user_history?.total_completed_sessions ?? 0} sessions
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[11px]">Recent 7-Day:</span>
                          <span className="font-bold text-gray-900">
                            {item.user_history?.recent_weekly_hours ?? 0} hrs
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[11px]">No-shows:</span>
                          <span
                            className={`font-bold ${
                              (item.user_history?.total_no_shows ?? 0) > 0 ? "text-rose-600" : "text-gray-900"
                            }`}
                          >
                            {item.user_history?.total_no_shows ?? 0}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[11px]">Active Strikes:</span>
                          <span
                            className={`font-bold ${
                              (item.user_history?.strike_count ?? 0) > 0 ? "text-amber-600" : "text-gray-900"
                            }`}
                          >
                            {item.user_history?.strike_count ?? 0} strikes
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Booking Purpose & Supervisor */}
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block">
                        Stated Purpose
                      </span>
                      <p className="text-gray-700 italic bg-white p-2.5 rounded-xl border border-gray-200/80 leading-relaxed">
                        "{b.purpose || "General fabrication and research testing."}"
                      </p>
                      {b.has_supervisor_signoff && (
                        <p className="text-[11px] text-emerald-700 font-semibold flex items-center gap-1 pt-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          Supervisor Signoff: {b.supervisor_name || "Verified Faculty"}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Expandable Criteria & Score Breakdown */}
                  {isExpanded && (
                    <div className="p-6 border-t border-gray-100 bg-white space-y-6">
                      {/* Eligibility Criteria Breakdown */}
                      <div>
                        <h4 className="font-bold text-xs uppercase tracking-wider text-gray-500 mb-3 flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4 text-brand-600" />
                          Automated Eligibility Evaluation
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                          {item.eligibility_evaluation?.criteria?.map((crit, idx) => (
                            <div
                              key={idx}
                              className={`p-3 rounded-2xl border ${
                                crit.passed
                                  ? "bg-emerald-50/50 border-emerald-200/80 text-emerald-900"
                                  : "bg-rose-50/50 border-rose-200/80 text-rose-900"
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-bold text-xs capitalize">
                                  {crit.rule.replace(/_/g, " ")}
                                </span>
                                {crit.passed ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600 stroke-[3]" />
                                ) : (
                                  <X className="w-3.5 h-3.5 text-rose-600 stroke-[3]" />
                                )}
                              </div>
                              <p className="text-[11px] opacity-80 leading-snug">
                                {crit.reason}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Waitlist Allocation Score Explainer */}
                      {item.waitlist_score_breakdown && (
                        <div>
                          <h4 className="font-bold text-xs uppercase tracking-wider text-gray-500 mb-3 flex items-center gap-2">
                            <ListOrdered className="w-4 h-4 text-indigo-600" />
                            Allocation & Ranking Score Breakdown
                          </h4>
                          <WhyThisOutcomeCard
                            breakdown={item.waitlist_score_breakdown}
                            rankingScore={score}
                          />
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions Footer */}
                  <div className="p-4 bg-gray-50 border-t border-gray-100 flex flex-wrap items-center justify-between gap-3">
                    <button
                      onClick={() => toggleDetails(b.id)}
                      className="text-xs font-bold text-gray-600 hover:text-gray-900 flex items-center gap-1 transition"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="w-4 h-4" /> Hide Full Assessment
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-4 h-4" /> View Full Assessment & Scores
                        </>
                      )}
                    </button>

                    <div className="flex flex-wrap items-center gap-2">
                      {/* Move to Waitlist */}
                      <button
                        onClick={() => handleMoveToWaitlist(item)}
                        disabled={waitlistSubmitting === b.id}
                        className="bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-50 font-bold px-3.5 py-2 rounded-xl text-xs transition shadow-2xs"
                      >
                        {waitlistSubmitting === b.id ? "Moving..." : "Move to Waitlist"}
                      </button>

                      {/* Reject */}
                      <button
                        onClick={() => {
                          setRejectItem(item);
                          setRejectReason(
                            !isEligible && item.eligibility_evaluation?.reasons_failed?.length
                              ? item.eligibility_evaluation.reasons_failed.join("; ")
                              : ""
                          );
                        }}
                        className="bg-white border border-rose-200 text-rose-700 hover:bg-rose-50 font-bold px-3.5 py-2 rounded-xl text-xs transition shadow-2xs"
                      >
                        Reject...
                      </button>

                      {/* Approve */}
                      <button
                        onClick={() => {
                          setApproveItem(item);
                          setIsOverride(!isEligible && isOwner);
                          setApproveNote("");
                        }}
                        className="bg-brand-600 hover:bg-brand-700 text-white font-bold px-5 py-2 rounded-xl text-xs transition shadow-sm shadow-brand-500/20"
                      >
                        Approve Booking
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ── Approve Modal ─────────────────────────────────────────────────── */}
        {approveItem && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-xl border border-gray-200 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <h3 className="text-lg font-black text-gray-900">
                  Confirm Approval · Booking #{approveItem.booking.id}
                </h3>
                <button
                  onClick={() => setApproveItem(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="text-xs text-gray-600 space-y-2">
                <p>
                  You are approving access for{" "}
                  <strong className="text-gray-900">{approveItem.user_name}</strong> on machine{" "}
                  <strong className="text-gray-900">{approveItem.equipment_name}</strong>.
                </p>
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
                  <div className="font-semibold text-gray-700">Slot Scheduled:</div>
                  <div>
                    {new Date(approveItem.booking.slot_start).toLocaleString()} to{" "}
                    {new Date(approveItem.booking.slot_end).toLocaleTimeString()}
                  </div>
                  <div className="text-amber-700 font-bold mt-1">
                    Hold: {approveItem.booking.credit_cost} credits
                  </div>
                </div>

                {!approveItem.eligibility_evaluation?.is_eligible && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 space-y-1">
                    <div className="font-bold flex items-center gap-1 text-amber-800">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      Notice: Automated Eligibility Engine Failed
                    </div>
                    <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                      {approveItem.eligibility_evaluation?.reasons_failed?.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Owner Override Toggle */}
                {isOwner && (
                  <label className="flex items-start gap-3 p-3 bg-indigo-50 border border-indigo-200 rounded-xl cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isOverride}
                      onChange={(e) => setIsOverride(e.target.checked)}
                      className="mt-0.5 rounded border-indigo-300 text-brand-600 focus:ring-brand-500"
                    />
                    <div>
                      <span className="font-bold text-indigo-900 block">
                        Lab Owner Override
                      </span>
                      <span className="text-[11px] text-indigo-700 leading-tight block">
                        As a verified lab owner or admin, you may bypass automated eligibility or schedule conflicts. This action is permanently stamped in the append-only audit trail.
                      </span>
                    </div>
                  </label>
                )}

                <div>
                  <label className="block font-bold text-gray-700 text-xs mb-1">
                    Approval Note / Instructions (Optional):
                  </label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Please wear eye protection; safety officer Sharma will supervise."
                    value={approveNote}
                    onChange={(e) => setApproveNote(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-300 rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setApproveItem(null)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 font-bold rounded-xl text-xs hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmApprove}
                  disabled={approveSubmitting}
                  className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-xl text-xs transition shadow-sm"
                >
                  {approveSubmitting ? "Approving..." : isOverride ? "Approve with Override" : "Confirm Approval"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Reject Modal (Mandatory Reason) ───────────────────────────────── */}
        {rejectItem && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-xl border border-gray-200 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <h3 className="text-lg font-black text-gray-900 flex items-center gap-2">
                  <XCircle className="w-5 h-5 text-rose-600" />
                  Reject Request · Booking #{rejectItem.booking.id}
                </h3>
                <button
                  onClick={() => setRejectItem(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="text-xs text-gray-600 space-y-3">
                <p>
                  Per OpenBench transparency non-negotiables, all rejections require a clear human reason that will be delivered to the booker and permanently logged in the audit ledger.
                </p>

                <div>
                  <label className="block font-bold text-gray-700 text-xs mb-1">
                    Mandatory Rejection Reason: <span className="text-rose-600">*</span>
                  </label>
                  <textarea
                    rows={3}
                    required
                    placeholder="e.g. Missing required laser cutter safety certification; scheduled machine maintenance on Friday."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-300 rounded-xl p-3 text-xs focus:ring-2 focus:ring-rose-500 focus:bg-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setRejectItem(null)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 font-bold rounded-xl text-xs hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmReject}
                  disabled={rejectSubmitting || !rejectReason.trim()}
                  className="px-5 py-2 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition shadow-sm"
                >
                  {rejectSubmitting ? "Rejecting..." : "Confirm Rejection"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

