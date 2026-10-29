import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import SideBySideConditionViewer from "../components/SideBySideConditionViewer";
import {
  QrCode,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Camera,
  Layers,
  Sparkles,
  CheckCircle2,
  XCircle,
  Plus,
  RefreshCw,
  ArrowRight,
  Info,
  Check,
  X,
  Upload,
} from "lucide-react";

export default function SessionCheckinCheckout() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [booking, setBooking] = useState(null);
  const [equipment, setEquipment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Form State: Pre or Post Checklist
  const [condition, setCondition] = useState("GOOD");
  const [notes, setNotes] = useState("");
  const [checklist, setChecklist] = useState({});
  const [uploadedPhotos, setUploadedPhotos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Extension State
  const [extending, setExtending] = useState(false);
  const [extraHours, setExtraHours] = useState(1);

  const fetchSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/bookings/${id}`);
      setBooking(res.data);
      if (res.data.equipment_id) {
        const eqRes = await api.get(`/equipment/${res.data.equipment_id}`);
        setEquipment(eqRes.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load booking session.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) {
      navigate("/login");
      return;
    }
    fetchSession();
  }, [id, user]);

  // Set default checklist items according to state
  useEffect(() => {
    if (!booking) return;
    if (booking.status === "APPROVED") {
      setChecklist({
        power_and_cables_intact: true,
        workspace_clean_and_clear: true,
        tooling_and_nozzle_undamaged: true,
        safety_shields_operational: true,
        calibration_verified: true,
      });
    } else if (booking.status === "IN_PROGRESS") {
      setChecklist({
        machine_powered_down_safely: true,
        debris_and_waste_cleared: true,
        tooling_returned_to_rack: true,
        consumables_logged: true,
        workpiece_removed: true,
      });
    }
  }, [booking?.status]);

  const handleCheckboxChange = (key) => {
    setChecklist((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await api.post("/bookings/upload-photo", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadedPhotos((prev) => [...prev, res.data.filename]);
    } catch (err) {
      alert(err.response?.data?.detail || "Photo upload failed.");
    } finally {
      setUploading(false);
    }
  };

  // Check-In Handler
  const handleCheckIn = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post(`/bookings/${id}/qr-checkin`, {
        condition,
        checklist,
        notes,
        photos: uploadedPhotos,
      });
      setActionSuccess("Check-in verified! Machine is activated for your session.");
      setUploadedPhotos([]);
      setNotes("");
      fetchSession();
    } catch (err) {
      alert(err.response?.data?.detail || "Check-in failed.");
    } finally {
      setSubmitting(false);
    }
  };

  // Return & Checkout Handler
  const handleCheckOut = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api.post(`/bookings/${id}/qr-checkout`, {
        condition,
        checklist,
        notes,
        photos: uploadedPhotos,
      });
      setActionSuccess(
        `Session completed successfully! Handover report filed with advisory photo-diff.${
          res.data.is_late ? ` Note: Return was ${res.data.overdue_minutes} min late.` : ""
        }`
      );
      setUploadedPhotos([]);
      setNotes("");
      fetchSession();
    } catch (err) {
      alert(err.response?.data?.detail || "Checkout failed.");
    } finally {
      setSubmitting(false);
    }
  };

  // Extension Handler
  const handleExtend = async (hours) => {
    setExtending(true);
    try {
      await api.post(`/bookings/${id}/extend`, { extra_hours: hours });
      setActionSuccess(`Session extended by ${hours} hour(s)!`);
      fetchSession();
    } catch (err) {
      alert(err.response?.data?.detail || "Extension failed. A slot conflict may exist.");
    } finally {
      setExtending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-brand-600 animate-spin mx-auto mb-2" />
          <p className="text-xs text-gray-500 font-semibold">Verifying QR identity & session schedule...</p>
        </div>
      </div>
    );
  }

  if (error || !booking) {
    return (
      <div className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="max-w-md mx-auto bg-white rounded-3xl border border-gray-200 p-8 text-center shadow-sm">
          <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
          <h2 className="text-lg font-black text-gray-900">Session Error</h2>
          <p className="text-xs text-gray-500 mt-1 mb-6">{error || "Booking not found."}</p>
          <Link
            to="/dashboard"
            className="inline-block bg-brand-600 text-white px-5 py-2.5 rounded-xl font-bold text-xs"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const isCompleted = booking.status === "COMPLETED";
  const isInProgress = booking.status === "IN_PROGRESS";
  const isApproved = booking.status === "APPROVED";

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-6 font-medium">
          <Link to="/dashboard" className="hover:text-brand-600">Dashboard</Link>
          <span>/</span>
          <span className="text-gray-900 font-bold">Booking #{booking.id} Session Handover</span>
        </div>

        {/* Header Card */}
        <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-8 shadow-2xs mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-100">
            <div>
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded-xl bg-brand-50 text-brand-600">
                  <QrCode className="w-5 h-5" />
                </span>
                <h1 className="text-2xl font-black text-gray-900 tracking-tight">
                  {equipment?.name || `Equipment #${booking.equipment_id}`}
                </h1>
              </div>
              <p className="text-xs text-gray-500 mt-1 pl-9">
                Booking #{booking.id} · Scheduled: {new Date(booking.slot_start).toLocaleString()} to{" "}
                {new Date(booking.slot_end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <span
                className={`text-xs font-black px-3.5 py-1.5 rounded-full uppercase tracking-wider border ${
                  isCompleted
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : isInProgress
                    ? "bg-indigo-50 text-indigo-800 border-indigo-200 animate-pulse"
                    : "bg-amber-50 text-amber-800 border-amber-200"
                }`}
              >
                ● {booking.status}
              </span>
            </div>
          </div>

          {/* Action Success Toast */}
          {actionSuccess && (
            <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-between text-xs text-emerald-800 font-bold">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>{actionSuccess}</span>
              </div>
              <button onClick={() => setActionSuccess(null)} className="text-emerald-700 hover:text-emerald-900 text-xs">
                Dismiss
              </button>
            </div>
          )}

          {/* ── STEP 1: PRE-SESSION CHECK-IN (APPROVED) ────────────────────────── */}
          {isApproved && (
            <div className="mt-8 space-y-6">
              <div className="p-4 bg-indigo-50/60 border border-indigo-100 rounded-2xl">
                <h3 className="font-bold text-sm text-indigo-950 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-600" />
                  QR Check-In: Pre-Flight Before-Condition Checklist
                </h3>
                <p className="text-xs text-indigo-800 mt-0.5">
                  Confirm the current condition of the machine before powering on. Photos and checklist records protect you against prior damage liability.
                </p>
              </div>

              <form onSubmit={handleCheckIn} className="space-y-6">
                {/* Checklist checkboxes */}
                <div className="bg-gray-50 p-5 rounded-2xl border border-gray-200 space-y-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-gray-500 block">
                    1. Inspection Checklist
                  </span>
                  {Object.entries(checklist).map(([key, val]) => (
                    <label key={key} className="flex items-center gap-3 cursor-pointer text-xs font-medium text-gray-800">
                      <input
                        type="checkbox"
                        checked={val}
                        onChange={() => handleCheckboxChange(key)}
                        className="rounded border-gray-300 text-brand-600 focus:ring-brand-500 w-4 h-4"
                      />
                      <span className="capitalize">{key.replace(/_/g, " ")}</span>
                    </label>
                  ))}
                </div>

                {/* Overall Condition Selector */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                      2. Initial Overall Condition
                    </label>
                    <select
                      value={condition}
                      onChange={(e) => setCondition(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-300 rounded-xl p-2.5 text-xs font-bold text-gray-800 focus:ring-2 focus:ring-brand-500"
                    >
                      <option value="GOOD">GOOD — Pristine & Ready</option>
                      <option value="FAIR">FAIR — Minor wear, functional</option>
                      <option value="DAMAGED">DAMAGED — Pre-existing defect</option>
                      <option value="BROKEN">BROKEN — Unsafe / inoperable</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                      3. Attach Condition Photos (Optional)
                    </label>
                    <div className="flex items-center gap-2">
                      <label className="cursor-pointer bg-white border border-gray-300 hover:bg-gray-50 px-4 py-2.5 rounded-xl text-xs font-bold text-gray-700 flex items-center gap-2 shadow-2xs">
                        <Upload className="w-3.5 h-3.5 text-brand-600" />
                        {uploading ? "Encrypting & Storing..." : "Upload Photo"}
                        <input
                          type="file"
                          accept="image/*"
                          onChange={handleFileUpload}
                          disabled={uploading}
                          className="hidden"
                        />
                      </label>
                      <span className="text-xs text-gray-400">
                        {uploadedPhotos.length} photo(s) uploaded
                      </span>
                    </div>
                  </div>
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                    4. Check-In Observation Notes (Optional)
                  </label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Bed leveled; slight scratches on acrylic guard noted."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-300 rounded-xl p-3 text-xs focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-brand-600 hover:bg-brand-700 text-white font-black py-3.5 rounded-2xl text-xs tracking-wider uppercase transition shadow-md shadow-brand-500/20"
                >
                  {submitting ? "Verifying Check-In..." : "Confirm Check-In & Start Session"}
                </button>
              </form>
            </div>
          )}

          {/* ── STEP 2: ACTIVE SESSION & RETURN HANDOVER (IN_PROGRESS) ─────────── */}
          {isInProgress && (
            <div className="mt-8 space-y-8">
              {/* Session Control Banner */}
              <div className="p-5 bg-gradient-to-r from-gray-900 to-indigo-950 text-white rounded-3xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                    <span className="text-xs uppercase font-extrabold tracking-wider text-emerald-400">
                      Machine Active
                    </span>
                  </div>
                  <h3 className="text-lg font-black text-white mt-1">
                    Session In Progress
                  </h3>
                  <p className="text-xs text-gray-300 mt-0.5">
                    Return deadline: {new Date(booking.slot_end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>

                {/* Extension Controls */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-medium hidden sm:inline">Extend:</span>
                  <button
                    onClick={() => handleExtend(1)}
                    disabled={extending}
                    className="bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition"
                  >
                    +1 Hour
                  </button>
                  <button
                    onClick={() => handleExtend(2)}
                    disabled={extending}
                    className="bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition"
                  >
                    +2 Hours
                  </button>
                </div>
              </div>

              {/* Return Form */}
              <div className="space-y-6">
                <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl">
                  <h3 className="font-bold text-sm text-gray-900 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-brand-600" />
                    QR Return: Post-Session After-Condition Report
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Inspect the machine, tidy your bench, and upload an after photo for automated advisory photo-diff comparison.
                  </p>
                </div>

                <form onSubmit={handleCheckOut} className="space-y-6">
                  {/* Checklist checkboxes */}
                  <div className="bg-gray-50 p-5 rounded-2xl border border-gray-200 space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-gray-500 block">
                      1. Handover Checklist
                    </span>
                    {Object.entries(checklist).map(([key, val]) => (
                      <label key={key} className="flex items-center gap-3 cursor-pointer text-xs font-medium text-gray-800">
                        <input
                          type="checkbox"
                          checked={val}
                          onChange={() => handleCheckboxChange(key)}
                          className="rounded border-gray-300 text-brand-600 focus:ring-brand-500 w-4 h-4"
                        />
                        <span className="capitalize">{key.replace(/_/g, " ")}</span>
                      </label>
                    ))}
                  </div>

                  {/* Return Condition & Photos */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                        2. Final Handover Condition
                      </label>
                      <select
                        value={condition}
                        onChange={(e) => setCondition(e.target.value)}
                        className="w-full bg-gray-50 border border-gray-300 rounded-xl p-2.5 text-xs font-bold text-gray-800 focus:ring-2 focus:ring-brand-500"
                      >
                        <option value="GOOD">GOOD — Cleaned & Nominal</option>
                        <option value="FAIR">FAIR — Minor residue, cleaned</option>
                        <option value="DAMAGED">DAMAGED — Incident / wear noted</option>
                        <option value="BROKEN">BROKEN — Requires maintenance</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                        3. Return Photo (Triggers Advisory Photo-Diff)
                      </label>
                      <div className="flex items-center gap-2">
                        <label className="cursor-pointer bg-white border border-gray-300 hover:bg-gray-50 px-4 py-2.5 rounded-xl text-xs font-bold text-gray-700 flex items-center gap-2 shadow-2xs">
                          <Upload className="w-3.5 h-3.5 text-brand-600" />
                          {uploading ? "Encrypting & Storing..." : "Upload After Photo"}
                          <input
                            type="file"
                            accept="image/*"
                            onChange={handleFileUpload}
                            disabled={uploading}
                            className="hidden"
                          />
                        </label>
                        <span className="text-xs text-gray-400">
                          {uploadedPhotos.length} photo(s) uploaded
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Notes */}
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                      4. Handover Notes (Optional)
                    </label>
                    <textarea
                      rows={2}
                      placeholder="e.g. Work piece completed; 50g PLA filament consumed; bench wiped down."
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-300 rounded-xl p-3 text-xs focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-black py-3.5 rounded-2xl text-xs tracking-wider uppercase transition shadow-md shadow-emerald-500/20"
                  >
                    {submitting ? "Processing Handover & Diff..." : "Complete Handover & Return Equipment"}
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* ── STEP 3: COMPLETED SESSION (SIDE BY SIDE VIEWER) ────────────────── */}
          {isCompleted && (
            <div className="mt-8 space-y-6">
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-between">
                <div>
                  <h3 className="font-extrabold text-sm text-emerald-950 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Session Completed & Verified
                  </h3>
                  <p className="text-xs text-emerald-800 mt-0.5">
                    {booking.credits_charged} credits deducted. Immutable condition records and advisory visual diff are permanently archived in the audit ledger.
                  </p>
                </div>
              </div>

              {/* Embed Side-by-Side Component */}
              <SideBySideConditionViewer bookingId={booking.id} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
