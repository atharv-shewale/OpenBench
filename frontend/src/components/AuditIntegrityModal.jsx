import React, { useState } from "react";
import api from "../api/client";
import {
  ShieldCheck,
  ShieldAlert,
  Download,
  RotateCw,
  CheckCircle2,
  XCircle,
  X,
  Database,
  Lock,
} from "lucide-react";

export default function AuditIntegrityModal({ isOpen, onClose }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);

  const handleVerify = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/audit/verify");
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Audit verification check failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleExportFullLedger = async () => {
    setExporting(true);
    try {
      const res = await api.get("/audit/export.csv", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `openbench_full_audit_ledger_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("Failed to export audit ledger as CSV.");
    } finally {
      setExporting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-gray-200 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-black text-gray-900">Audit Ledger Cryptographic Verification</h3>
              <p className="text-[11px] text-gray-500">SHA-256 Hash-Chained Append-Only Ledger</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 font-bold"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Info */}
        <p className="text-xs text-gray-600 leading-relaxed">
          OpenBench enforces an append-only ledger where every state transition, booking approval, condition report, and signal pulse is linked cryptographically to the previous entry hash from genesis.
        </p>

        {/* Verification Trigger & Results */}
        {!result && !loading && (
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-6 text-center space-y-3">
            <Database className="w-8 h-8 text-indigo-500 mx-auto" />
            <h4 className="text-sm font-bold text-gray-900">Verify Hash Chain Integrity</h4>
            <p className="text-xs text-gray-500 max-w-xs mx-auto">
              Walk every entry from Genesis Block (0x00...00) to current Head to detect tampering or broken linkages.
            </p>
            <button
              onClick={handleVerify}
              className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-sm transition"
            >
              Verify Audit Integrity Now
            </button>
          </div>
        )}

        {loading && (
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-8 text-center space-y-2">
            <RotateCw className="w-7 h-7 text-brand-600 animate-spin mx-auto" />
            <p className="text-xs font-bold text-gray-700">Walking hash chain blocks...</p>
          </div>
        )}

        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-2xl text-xs flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <div
              className={`p-4 rounded-2xl border flex items-center justify-between ${
                result.chain_valid
                  ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                  : "bg-rose-50 border-rose-200 text-rose-900"
              }`}
            >
              <div className="flex items-center gap-2.5">
                {result.chain_valid ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-600" />
                )}
                <div>
                  <h4 className="text-xs font-black uppercase tracking-wider">
                    {result.chain_valid ? "Hash Chain Intact & Verified" : "Chain Integrity Compromised"}
                  </h4>
                  <p className="text-xs mt-0.5">
                    {result.chain_valid
                      ? `All ${result.total_entries} blocks verified from Genesis to Head.`
                      : `Corrupted linkage detected at block ID #${result.broken_at_id}.`}
                  </p>
                </div>
              </div>
            </div>

            {/* Block Stats */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl">
                <span className="text-[10px] uppercase font-bold text-gray-400 block">Total Ledger Entries</span>
                <span className="text-lg font-black text-gray-900">{result.total_entries}</span>
              </div>

              <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl">
                <span className="text-[10px] uppercase font-bold text-gray-400 block">Genesis → Head Block</span>
                <span className="text-sm font-bold text-gray-900">
                  #{result.first_entry_id || 0} → #{result.last_entry_id || 0}
                </span>
              </div>
            </div>

            {result.head_hash && (
              <div className="p-3 bg-slate-900 text-slate-200 rounded-xl font-mono text-[10px] space-y-1">
                <span className="text-slate-400 block">Current Head Hash:</span>
                <div className="break-all text-emerald-400 font-bold">{result.head_hash}</div>
              </div>
            )}
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <button
            onClick={handleExportFullLedger}
            disabled={exporting}
            className="inline-flex items-center gap-1.5 px-3 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 font-bold text-xs rounded-xl shadow-2xs transition"
          >
            <Download className="w-3.5 h-3.5 text-gray-500" />
            {exporting ? "Exporting CSV..." : "Export Full Ledger (CSV)"}
          </button>

          <button
            onClick={onClose}
            className="px-5 py-2 bg-gray-900 hover:bg-black text-white font-bold text-xs rounded-xl transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

