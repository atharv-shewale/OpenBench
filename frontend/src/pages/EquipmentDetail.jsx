import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import EligibilityPanel from "../components/EligibilityPanel";
import {
  MapPin,
  Clock,
  ShieldCheck,
  QrCode,
  FileText,
  AlertTriangle,
  Calendar,
  ArrowLeft,
  Coins,
  CheckCircle2,
  Building2,
  Sparkles,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";

export default function EquipmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [equipment, setEquipment] = useState(null);
  const [eligibility, setEligibility] = useState(null);
  const [loading, setLoading] = useState(true);
  const [elLoading, setElLoading] = useState(false);
  const [error, setError] = useState(null);
  const [elError, setElError] = useState(null);
  const [showQrModal, setShowQrModal] = useState(false);

  // Booking form state
  const [bookingDate, setBookingDate] = useState("");
  const [bookingHours, setBookingHours] = useState(2);
  const [bookingPurpose, setBookingPurpose] = useState("");
  const [priorityTier, setPriorityTier] = useState("STANDARD");
  const [groupName, setGroupName] = useState("");
  const [hasSupervisorSignoff, setHasSupervisorSignoff] = useState(false);
  const [supervisorName, setSupervisorName] = useState("");

  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState(null);
  const [bookingFailure, setBookingFailure] = useState(null);

  const fetchEquipment = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/equipment/${id}`);
      setEquipment(data);
    } catch (err) {
      setError("Resource not found or currently unavailable.");
    } finally {
      setLoading(false);
    }
  };

  const checkEligibility = async () => {
    if (!user) return;
    setElLoading(true);
    setElError(null);
    try {
      const { data } = await api.get(`/equipment/${id}/eligibility`);
      setEligibility(data);
    } catch (err) {
      setElError(err.response?.data?.detail || "Could not check eligibility.");
    } finally {
      setElLoading(false);
    }
  };

  useEffect(() => {
    fetchEquipment();
  }, [id]);

  useEffect(() => {
    if (equipment && user) {
      checkEligibility();
    }
  }, [equipment, user]);

  const handleBookingSubmit = async (e) => {
    e.preventDefault();
    if (!user) {
      navigate("/login");
      return;
    }
    if (!bookingDate) {
      alert("Please choose a date & time for your slot.");
      return;
    }

    setBookingSubmitting(true);
    setBookingFailure(null);
    try {
      const start = new Date(bookingDate);
      const end = new Date(start.getTime() + bookingHours * 60 * 60 * 1000);

      const res = await api.post("/bookings", {
        equipment_id: equipment.id,
        slot_start: start.toISOString(),
        slot_end: end.toISOString(),
        purpose: bookingPurpose,
        priority_tier: priorityTier,
        group_name: groupName,
        has_supervisor_signoff: hasSupervisorSignoff,
        supervisor_name: supervisorName,
      });

      setBookingSuccess(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "object" && detail !== null) {
        setBookingFailure(detail);
      } else {
        setBookingFailure({
          message: detail || "Booking could not be processed.",
          counterfactuals: [],
        });
      }
    } finally {
      setBookingSubmitting(false);
    }
  };

  const applyCounterfactual = (suggestion) => {
    if (suggestion.suggested_slot_start) {
      // Convert to local datetime-local input string: YYYY-MM-DDTHH:MM
      const d = new Date(suggestion.suggested_slot_start);
      const pad = (n) => String(n).padStart(2, "0");
      const localStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
      setBookingDate(localStr);
    }
    if (suggestion.action === "shorten_duration" && suggestion.suggested_slot_start && suggestion.suggested_slot_end) {
      const s = new Date(suggestion.suggested_slot_start);
      const e = new Date(suggestion.suggested_slot_end);
      const hrs = Math.max(1, Math.round((e - s) / 3600000));
      setBookingHours(hrs);
    }
    if (suggestion.action === "request_supervisor_signoff") {
      setHasSupervisorSignoff(true);
      if (!supervisorName) setSupervisorName("Faculty Lab Sponsor");
    }
    setBookingFailure(null);
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 animate-pulse space-y-6">
        <div className="h-6 bg-gray-200 rounded w-1/4"></div>
        <div className="h-10 bg-gray-200 rounded w-1/2"></div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 h-96 bg-gray-200 rounded-2xl"></div>
          <div className="h-96 bg-gray-200 rounded-2xl"></div>
        </div>
      </div>
    );
  }

  if (error || !equipment) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">{error || "Equipment not found"}</h2>
        <Link
          to="/equipment"
          className="mt-6 inline-flex items-center gap-2 text-brand-600 font-semibold hover:underline"
        >
          <ArrowLeft className="w-4 h-4" /> Back to equipment discovery
        </Link>
      </div>
    );
  }

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Navigation Breadcrumb */}
        <div className="mb-6 flex items-center justify-between">
          <Link
            to="/equipment"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-gray-500 hover:text-brand-600 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Discovery
          </Link>

          <button
            onClick={() => setShowQrModal(true)}
            className="inline-flex items-center gap-1.5 bg-white border border-gray-300 hover:border-brand-500 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-gray-700 transition shadow-2xs"
          >
            <QrCode className="w-4 h-4 text-brand-600" /> Show Equipment QR Code
          </button>
        </div>

        {/* Title & Metadata */}
        <div className="bg-white rounded-3xl border border-gray-200 p-8 shadow-sm mb-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-100">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs uppercase font-extrabold tracking-wider text-brand-600 bg-brand-50 border border-brand-100 px-3 py-1 rounded-full">
                  {equipment.type}
                </span>
                <span
                  className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider ${equipment.status === "available"
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-rose-50 text-rose-700 border border-rose-200"
                    }`}
                >
                  {equipment.status}
                </span>
              </div>
              <h1 className="text-3xl font-black text-gray-900 tracking-tight">
                {equipment.name}
              </h1>
              <p className="text-sm font-medium text-gray-500 flex items-center gap-1.5 mt-2">
                <Building2 className="w-4 h-4 text-gray-400" />
                {equipment.institution || equipment.lab_name}
                {equipment.city && ` · ${equipment.city}`}
                {equipment.location && (
                  <span className="text-gray-700 font-semibold">({equipment.location})</span>
                )}
              </p>
            </div>

            {/* Rate Box */}
            <div className="bg-brand-50/60 border border-brand-100 p-4 rounded-2xl flex items-center gap-4">
              <div>
                <p className="text-xs text-brand-600 font-bold uppercase tracking-wider">
                  Booking Rate
                </p>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="text-3xl font-black text-brand-700">
                    {equipment.credit_per_hour}
                  </span>
                  <span className="text-xs font-medium text-brand-600">credits/hr</span>
                </div>
              </div>
              {equipment.deposit_credits > 0 && (
                <div className="border-l border-brand-200 pl-4">
                  <p className="text-xs text-gray-500 font-bold uppercase tracking-wider">
                    Deposit
                  </p>
                  <p className="text-lg font-extrabold text-gray-700 mt-0.5">
                    {equipment.deposit_credits} cr
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Description & Operational Details Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 pt-8">
            <div className="lg:col-span-2 space-y-6">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-gray-400 mb-2">
                  Resource Overview
                </h3>
                <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-line">
                  {equipment.description || "No extensive description available."}
                </p>
              </div>

              {/* Access Conditions & Rules */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5 mb-2">
                    <ShieldCheck className="w-4 h-4 text-brand-600" /> Access Conditions
                  </h4>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    {equipment.access_conditions || "Standard lab visitor protocol applies."}
                  </p>
                </div>

                <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5 mb-2">
                    <Clock className="w-4 h-4 text-brand-600" /> Session Limit
                  </h4>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    Maximum booking duration: <strong>{equipment.max_booking_hours} hours</strong> per
                    slot.
                  </p>
                </div>
              </div>

              {/* Usage Rules JSON breakdown */}
              {equipment.rules && Object.keys(equipment.rules).length > 0 && (
                <div className="bg-white rounded-2xl p-5 border border-gray-200">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5 mb-3">
                    <FileText className="w-4 h-4 text-brand-600" /> Machine Operating Parameters & Checklist
                  </h4>
                  <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {Object.entries(equipment.rules).map(([key, val]) => (
                      <div key={key} className="bg-gray-50 p-2.5 rounded-xl border border-gray-100">
                        <dt className="text-gray-400 font-mono capitalize">
                          {key.replace(/_/g, " ")}:
                        </dt>
                        <dd className="font-semibold text-gray-800 mt-0.5">
                          {Array.isArray(val) ? val.join(", ") : String(val)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              {/* Availability Windows Schedule */}
              <div className="bg-white rounded-2xl p-5 border border-gray-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5 mb-3">
                  <Calendar className="w-4 h-4 text-brand-600" /> Weekly Availability Schedule
                </h4>
                {equipment.availability_windows && equipment.availability_windows.length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    {equipment.availability_windows.map((win, i) => (
                      <div
                        key={i}
                        className="bg-gray-50 border border-gray-100 p-2.5 rounded-xl text-center"
                      >
                        <span className="font-bold text-gray-900 block">
                          {days[win.day_of_week] || `Day ${win.day_of_week}`}
                        </span>
                        <span className="text-gray-500 text-[11px] mt-0.5 block">
                          {win.start_time} – {win.end_time}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">Standard college lab hours apply.</p>
                )}
              </div>
            </div>

            {/* Right Column: "Am I Eligible?" Panel + Booking Form */}
            <div className="space-y-6">
              {/* Am I Eligible Interactive Component */}
              <EligibilityPanel
                equipment={equipment}
                eligibility={eligibility}
                loading={elLoading}
                error={elError}
                user={user}
              />

              {/* Booking Request Box */}
              <div className="bg-white border border-gray-200 rounded-3xl p-6 shadow-sm">
                <h3 className="font-bold text-gray-900 text-lg mb-1">Request a Slot</h3>
                <p className="text-xs text-gray-500 mb-4">
                  Held credits are only deducted upon verified session checkout.
                </p>

                {/* Counterfactual Feedback Callout (When Rejected/Waitlisted) */}
                {bookingFailure && (
                  <div className="mb-5 bg-rose-50 border border-rose-200 rounded-2xl p-4 text-xs text-rose-900 space-y-3">
                    <div>
                      <p className="font-bold flex items-center gap-1.5 text-rose-800">
                        <AlertTriangle className="w-4 h-4 text-rose-600" /> Request Not Approved
                      </p>
                      <p className="mt-1 text-rose-700 leading-relaxed font-medium">
                        {bookingFailure.message}
                      </p>
                    </div>

                    {bookingFailure.counterfactuals && bookingFailure.counterfactuals.length > 0 && (
                      <div className="pt-2 border-t border-rose-200/80 space-y-2">
                        <p className="font-extrabold uppercase tracking-wider text-[10px] text-rose-700 flex items-center gap-1">
                          <Sparkles className="w-3.5 h-3.5 text-amber-600" /> Actionable Fixes ("You'd be approved if..."):
                        </p>
                        <div className="space-y-2">
                          {bookingFailure.counterfactuals.map((cf, idx) => (
                            <div
                              key={idx}
                              className="bg-white/90 border border-rose-200 p-2.5 rounded-xl flex items-start justify-between gap-2 shadow-2xs"
                            >
                              <div>
                                <p className="font-semibold text-gray-900">{cf.message}</p>
                                {cf.details && (
                                  <p className="text-[11px] text-gray-500 mt-0.5">{cf.details}</p>
                                )}
                              </div>
                              {(cf.suggested_slot_start || cf.action === "request_supervisor_signoff") && (
                                <button
                                  type="button"
                                  onClick={() => applyCounterfactual(cf)}
                                  className="shrink-0 bg-brand-50 hover:bg-brand-100 text-brand-700 px-2.5 py-1 rounded-lg font-bold text-[11px] border border-brand-200 transition"
                                >
                                  Apply Fix
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {bookingSuccess ? (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-emerald-800 text-sm">
                    <p className="font-bold flex items-center gap-1.5">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" /> Booking Submitted!
                    </p>
                    <p className="text-xs mt-1">
                      Booking #{bookingSuccess.id} created in <strong>PENDING</strong> status.{" "}
                      {bookingSuccess.credits_held} credits have been reserved.
                    </p>
                    <Link
                      to="/dashboard"
                      className="mt-3 block text-center text-xs font-bold text-emerald-700 bg-emerald-100 hover:bg-emerald-200 py-2 rounded-xl transition"
                    >
                      View on Dashboard
                    </Link>
                  </div>
                ) : (
                  <form onSubmit={handleBookingSubmit} className="space-y-4 text-sm">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                        Slot Date & Start Time
                      </label>
                      <input
                        type="datetime-local"
                        required
                        value={bookingDate}
                        onChange={(e) => setBookingDate(e.target.value)}
                        className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                          Duration
                        </label>
                        <select
                          value={bookingHours}
                          onChange={(e) => setBookingHours(Number(e.target.value))}
                          className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
                        >
                          {Array.from(
                            { length: equipment.max_booking_hours || 4 },
                            (_, idx) => idx + 1
                          ).map((h) => (
                            <option key={h} value={h}>
                              {h} hr{h > 1 ? "s" : ""} ({h * equipment.credit_per_hour + equipment.deposit_credits} cr)
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                          Priority Tier
                        </label>
                        <select
                          value={priorityTier}
                          onChange={(e) => setPriorityTier(e.target.value)}
                          className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
                        >
                          <option value="STANDARD">Standard</option>
                          <option value="PRIORITY">Priority</option>
                          <option value="RESEARCH">Research</option>
                          <option value="EMERGENCY">Emergency</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                        Group / Project Team (Optional)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Formula Student Suspension Subsystem"
                        value={groupName}
                        onChange={(e) => setGroupName(e.target.value)}
                        className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
                      />
                    </div>

                    {/* Supervisor Sign-Off toggle if required or advised */}
                    <div className="bg-gray-50 p-3 rounded-2xl border border-gray-200 space-y-2">
                      <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-semibold text-gray-800">
                        <input
                          type="checkbox"
                          checked={hasSupervisorSignoff}
                          onChange={(e) => setHasSupervisorSignoff(e.target.checked)}
                          className="rounded text-brand-600 focus:ring-brand-500 w-4 h-4"
                        />
                        <span>Supervisor / Faculty Sign-Off Endorsed</span>
                      </label>

                      {hasSupervisorSignoff && (
                        <input
                          type="text"
                          placeholder="Supervisor / Faculty Mentor Full Name"
                          value={supervisorName}
                          onChange={(e) => setSupervisorName(e.target.value)}
                          className="w-full bg-white border border-gray-300 rounded-xl px-3 py-1.5 text-xs focus:ring-2 focus:ring-brand-500"
                        />
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                        Purpose of Session
                      </label>
                      <textarea
                        rows={2}
                        placeholder="Detail materials, prototype goals, or test standards..."
                        value={bookingPurpose}
                        onChange={(e) => setBookingPurpose(e.target.value)}
                        className="w-full bg-gray-50 border border-gray-300 rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-brand-500 focus:bg-white"
                      />
                    </div>

                    <div className="pt-2">
                      <button
                        type="submit"
                        disabled={bookingSubmitting || equipment.status !== "available"}
                        className="w-full py-3 rounded-xl font-bold text-xs bg-brand-600 hover:bg-brand-700 text-white transition shadow-sm shadow-brand-500/20"
                      >
                        {bookingSubmitting
                          ? "Verifying Request..."
                          : user
                            ? `Submit Booking Request (${bookingHours * equipment.credit_per_hour + equipment.deposit_credits} cr)`
                            : "Sign in to Book"}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* QR Code Modal */}
        {showQrModal && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-sm w-full p-6 text-center space-y-4 shadow-xl border border-gray-200">
              <h3 className="font-bold text-gray-900 text-lg">Equipment QR Code</h3>
              <p className="text-xs text-gray-500">
                Scan on-site at the lab bench to check in or view specs.
              </p>
              <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100 flex justify-center">
                <img
                  src={`/api/equipment/${equipment.id}/qr`}
                  alt="Equipment QR Code"
                  className="w-48 h-48 rounded-lg shadow-2xs"
                />
              </div>
              <p className="text-[11px] font-mono text-gray-400">
                openbench://equipment/{equipment.id}
              </p>
              <button
                onClick={() => setShowQrModal(false)}
                className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold rounded-xl text-xs transition"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
