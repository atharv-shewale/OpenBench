import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import {
  Plus,
  Layers,
  Edit3,
  Trash2,
  QrCode,
  MapPin,
  AlertCircle,
  Coins,
  CheckCircle2,
} from "lucide-react";

export default function OwnerResourceList() {
  const { user } = useAuthStore();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedQr, setSelectedQr] = useState(null);

  const fetchResources = async () => {
    setLoading(true);
    try {
      const res = await api.get("/equipment?available_only=false");
      setItems(res.data);
    } catch (err) {
      setError("Failed to fetch equipment inventory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResources();
  }, []);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to remove "${name}" from OpenBench?`)) return;
    try {
      await api.delete(`/equipment/${id}`);
      setItems(items.filter((item) => item.id !== id));
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to delete equipment.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-black text-gray-900 tracking-tight">
              Lab Resource Inventory
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Manage listed machines, equipment rules, credit pricing, and view QR passes.
            </p>
          </div>

          <Link
            to="/owner/resources/new"
            className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white font-bold px-5 py-2.5 rounded-xl text-sm transition shadow-sm shadow-brand-500/20"
          >
            <Plus className="w-4 h-4" /> Add New Resource
          </Link>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="space-y-4 animate-pulse">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-24 bg-white rounded-2xl border border-gray-200"></div>
            ))}
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && items.length === 0 && (
          <div className="bg-white rounded-3xl border border-gray-200 p-12 text-center shadow-sm">
            <Layers className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-gray-800">No resources listed yet</h3>
            <p className="text-gray-500 text-xs mt-1 max-w-sm mx-auto">
              Start sharing idle equipment in your labs to generate credits and provide
              access to local entrepreneurs and students.
            </p>
            <Link
              to="/owner/resources/new"
              className="mt-5 inline-flex items-center gap-2 bg-brand-600 text-white font-semibold px-4 py-2 rounded-xl text-xs"
            >
              <Plus className="w-4 h-4" /> List First Machine
            </Link>
          </div>
        )}

        {/* Table / List */}
        {!loading && !error && items.length > 0 && (
          <div className="bg-white rounded-3xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-600">
                <thead className="bg-gray-50/80 text-[11px] uppercase tracking-wider font-extrabold text-gray-400 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-4">Resource</th>
                    <th className="px-6 py-4">Lab / Location</th>
                    <th className="px-6 py-4">Rate & Deposit</th>
                    <th className="px-6 py-4">Required Certifications</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {items.map((eq) => (
                    <tr key={eq.id} className="hover:bg-gray-50/60 transition">
                      <td className="px-6 py-4">
                        <div className="font-bold text-gray-900">{eq.name}</div>
                        <div className="text-xs text-gray-400 uppercase tracking-wide mt-0.5">
                          {eq.type}
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <div className="text-xs font-semibold text-gray-800">
                          {eq.institution || eq.lab_name}
                        </div>
                        <div className="text-xs text-gray-400">
                          {eq.location || eq.city || "Main Lab Bay"}
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <div className="font-extrabold text-gray-900 flex items-center gap-1">
                          <Coins className="w-3.5 h-3.5 text-brand-600" />
                          {eq.credit_per_hour} cr/hr
                        </div>
                        {eq.deposit_credits > 0 && (
                          <div className="text-[11px] text-gray-400">
                            {eq.deposit_credits} cr deposit
                          </div>
                        )}
                      </td>

                      <td className="px-6 py-4">
                        {eq.required_credentials && eq.required_credentials.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {eq.required_credentials.map((c, i) => (
                              <span
                                key={i}
                                className="text-[10px] bg-amber-50 text-amber-800 border border-amber-200/80 px-2 py-0.5 rounded font-mono"
                              >
                                {c}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-gray-400">None required</span>
                        )}
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${
                            eq.status === "available"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-rose-50 text-rose-700 border border-rose-200"
                          }`}
                        >
                          {eq.status}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setSelectedQr(eq)}
                            title="Generate QR Tag"
                            className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition"
                          >
                            <QrCode className="w-4 h-4" />
                          </button>
                          <Link
                            to={`/owner/resources/${eq.id}/edit`}
                            title="Edit Resource"
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                          >
                            <Edit3 className="w-4 h-4" />
                          </Link>
                          <button
                            onClick={() => handleDelete(eq.id, eq.name)}
                            title="Delete Resource"
                            className="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* QR Modal */}
        {selectedQr && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-sm w-full p-6 text-center space-y-4 shadow-xl border border-gray-200">
              <h3 className="font-bold text-gray-900 text-lg">{selectedQr.name}</h3>
              <p className="text-xs text-gray-500">
                Print and affix this QR tag to the equipment for direct booker check-in.
              </p>
              <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100 flex justify-center">
                <img
                  src={`/api/equipment/${selectedQr.id}/qr`}
                  alt="QR"
                  className="w-48 h-48 rounded-lg shadow-2xs"
                />
              </div>
              <p className="text-[11px] font-mono text-gray-400">
                openbench://equipment/{selectedQr.id}
              </p>
              <button
                onClick={() => setSelectedQr(null)}
                className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold rounded-xl text-xs transition"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

