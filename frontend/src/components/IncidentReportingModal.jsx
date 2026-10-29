import React, { useState } from "react";
import api from "../api/client";
import {
  AlertTriangle,
  X,
  ShieldAlert,
  Upload,
  CheckCircle2,
} from "lucide-react";

export default function IncidentReportingModal({ bookingId, equipmentName, isOpen, onClose, onSuccess }) {
  const [incidentType, setIncidentType] = useState("DAMAGE");
  const [severity, setSeverity] = useState("MEDIUM");
  const [description, setDescription] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!description.trim()) {
      alert("Please provide a description of the incident.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/incidents", {
        booking_id: bookingId,
        incident_type: incidentType,
        severity,
        description: description.trim(),
        evidence_json: evidenceUrl ? [evidenceUrl.trim()] : [],
      });
      alert("Incident filed. It has been routed to lab managers for investigation and resolution.");
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to file incident report.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-gray-200 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-black text-gray-900">File Incident Report</h3>
              <p className="text-[11px] text-gray-500">Booking #{bookingId} · {equipmentName || "Lab Equipment"}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                Incident Category
              </label>
              <select
                value={incidentType}
                onChange={(e) => setIncidentType(e.target.value)}
                className="w-full bg-gray-50 border border-gray-300 rounded-xl p-2.5 text-xs font-bold text-gray-800 focus:ring-2 focus:ring-brand-500"
              >
                <option value="DAMAGE">Physical Damage</option>
                <option value="DELAY">Equipment Delay / Lockout</option>
                <option value="DISPUTE">Booking / Priority Dispute</option>
                <option value="SAFETY">Safety Hazard / Interlock</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                Severity Level
              </label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full bg-gray-50 border border-gray-300 rounded-xl p-2.5 text-xs font-bold text-gray-800 focus:ring-2 focus:ring-brand-500"
              >
                <option value="LOW">LOW — Minor cosmetic/non-blocking</option>
                <option value="MEDIUM">MEDIUM — Operational impairment</option>
                <option value="HIGH">HIGH — Broken tooling / shutdown</option>
                <option value="CRITICAL">CRITICAL — Safety hazard / injury</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
              Description of What Happened <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              required
              placeholder="Detail the issue, physical symptoms, machine sounds, or cause of dispute..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-gray-50 border border-gray-300 rounded-xl p-3 text-xs focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
              Supporting Evidence / Photo Filename (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. cond_photo_abc.jpg or photo upload key"
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              className="w-full bg-gray-50 border border-gray-300 rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 font-bold rounded-xl text-xs hover:bg-gray-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-xs transition shadow-sm"
            >
              {submitting ? "Submitting..." : "Submit Incident Report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

