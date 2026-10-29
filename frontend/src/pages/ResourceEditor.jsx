import React, { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "../api/client";
import {
  ArrowLeft,
  Building2,
  Save,
  Plus,
  Trash2,
  Clock,
  ShieldAlert,
  Coins,
} from "lucide-react";

export default function ResourceEditor() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [labs, setLabs] = useState([]);
  const [loading, setLoading] = useState(isEdit);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    lab_id: "",
    name: "",
    type: "fabrication",
    description: "",
    credit_per_hour: 15,
    max_booking_hours: 4,
    status: "available",
    location: "",
    access_conditions: "",
    deposit_credits: 0,
    required_credentials_str: "",
    rules_json_str: '{\n  "safety_gear": "Mandatory safety glasses",\n  "clean_up_minutes": 10\n}',
    availability_windows: [
      { day_of_week: 0, start_time: "09:00", end_time: "17:00" },
      { day_of_week: 1, start_time: "09:00", end_time: "17:00" },
      { day_of_week: 2, start_time: "09:00", end_time: "17:00" },
      { day_of_week: 3, start_time: "09:00", end_time: "17:00" },
      { day_of_week: 4, start_time: "09:00", end_time: "17:00" },
    ],
  });

  useEffect(() => {
    // Fetch labs to populate lab_id dropdown
    api.get("/labs").then((r) => {
      setLabs(r.data);
      if (!isEdit && r.data.length > 0) {
        setForm((prev) => ({ ...prev, lab_id: r.data[0].id }));
      }
    }).catch(() => {});

    if (isEdit) {
      api.get(`/equipment/${id}`).then((r) => {
        const d = r.data;
        setForm({
          lab_id: d.lab_id,
          name: d.name,
          type: d.type,
          description: d.description || "",
          credit_per_hour: d.credit_per_hour,
          max_booking_hours: d.max_booking_hours,
          status: d.status,
          location: d.location || "",
          access_conditions: d.access_conditions || "",
          deposit_credits: d.deposit_credits || 0,
          required_credentials_str: (d.required_credentials || []).join(", "),
          rules_json_str: d.rules ? JSON.stringify(d.rules, null, 2) : "{}",
          availability_windows: d.availability_windows || [],
        });
      }).catch((err) => {
        alert("Failed to load resource data.");
      }).finally(() => {
        setLoading(false);
      });
    }
  }, [id, isEdit]);

  const handleWindowChange = (index, field, value) => {
    const updated = [...form.availability_windows];
    updated[index][field] = field === "day_of_week" ? Number(value) : value;
    setForm({ ...form, availability_windows: updated });
  };

  const addWindow = () => {
    setForm({
      ...form,
      availability_windows: [
        ...form.availability_windows,
        { day_of_week: 0, start_time: "09:00", end_time: "17:00" },
      ],
    });
  };

  const removeWindow = (index) => {
    setForm({
      ...form,
      availability_windows: form.availability_windows.filter((_, i) => i !== index),
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    let parsedRules = null;
    try {
      if (form.rules_json_str.trim()) {
        parsedRules = JSON.parse(form.rules_json_str);
      }
    } catch {
      alert("Invalid JSON format for machine usage rules.");
      setSubmitting(false);
      return;
    }

    const credsList = form.required_credentials_str
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = {
      lab_id: Number(form.lab_id),
      name: form.name,
      type: form.type,
      description: form.description,
      credit_per_hour: Number(form.credit_per_hour),
      max_booking_hours: Number(form.max_booking_hours),
      status: form.status,
      location: form.location,
      access_conditions: form.access_conditions,
      deposit_credits: Number(form.deposit_credits),
      required_credentials: credsList,
      rules: parsedRules,
      availability_windows: form.availability_windows,
    };

    try {
      if (isEdit) {
        await api.patch(`/equipment/${id}`, payload);
        alert("Resource updated successfully!");
      } else {
        await api.post("/equipment", payload);
        alert("Resource listed successfully!");
      }
      navigate("/owner/resources");
    } catch (err) {
      alert(err.response?.data?.detail || "Operation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const days = [
    { id: 0, name: "Monday" },
    { id: 1, name: "Tuesday" },
    { id: 2, name: "Wednesday" },
    { id: 3, name: "Thursday" },
    { id: 4, name: "Friday" },
    { id: 5, name: "Saturday" },
    { id: 6, name: "Sunday" },
  ];

  if (loading) {
    return <div className="max-w-4xl mx-auto p-12 text-center text-gray-400">Loading form...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <Link
          to="/owner/resources"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-gray-500 hover:text-brand-600 mb-6 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Inventory
        </Link>

        <div className="bg-white rounded-3xl border border-gray-200 p-8 shadow-sm">
          <h1 className="text-2xl font-black text-gray-900 mb-1">
            {isEdit ? "Edit Lab Resource" : "List New Equipment or Space"}
          </h1>
          <p className="text-gray-500 text-xs mb-8">
            Configure access rules, hourly credits, deposit, and weekly booking schedules.
          </p>

          <form onSubmit={handleSubmit} className="space-y-6 text-sm">
            {/* Lab selection & Name */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Host Lab
                </label>
                <select
                  required
                  value={form.lab_id}
                  onChange={(e) => setForm({ ...form, lab_id: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
                >
                  {labs.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.name} ({l.city})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Resource Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 5-Axis CNC Milling Center"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
                />
              </div>
            </div>

            {/* Category & Status */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Category
                </label>
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
                >
                  <option value="fabrication">Fabrication & Machining</option>
                  <option value="testing">Testing & Metrology</option>
                  <option value="space">Bench / Specialized Space</option>
                  <option value="other">Other / Support Equipment</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Bench / Room Location
                </label>
                <input
                  type="text"
                  placeholder="e.g. Ground Floor, Room 104"
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Operating Status
                </label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
                >
                  <option value="available">Available</option>
                  <option value="maintenance">Under Maintenance</option>
                  <option value="retired">Retired / Inactive</option>
                </select>
              </div>
            </div>

            {/* Pricing & Limits */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-2xl border border-gray-100">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Credits / Hour
                </label>
                <input
                  type="number"
                  min={1}
                  required
                  value={form.credit_per_hour}
                  onChange={(e) => setForm({ ...form, credit_per_hour: e.target.value })}
                  className="w-full bg-white border border-gray-300 rounded-xl px-3.5 py-2 text-xs focus:ring-2 focus:ring-brand-500 font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Deposit (Credits)
                </label>
                <input
                  type="number"
                  min={0}
                  value={form.deposit_credits}
                  onChange={(e) => setForm({ ...form, deposit_credits: e.target.value })}
                  className="w-full bg-white border border-gray-300 rounded-xl px-3.5 py-2 text-xs focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Max Booking Hours
                </label>
                <input
                  type="number"
                  min={1}
                  max={24}
                  required
                  value={form.max_booking_hours}
                  onChange={(e) => setForm({ ...form, max_booking_hours: e.target.value })}
                  className="w-full bg-white border border-gray-300 rounded-xl px-3.5 py-2 text-xs focus:ring-2 focus:ring-brand-500"
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                Description & Technical Specifications
              </label>
              <textarea
                rows={3}
                placeholder="Include capacity, tolerances, compatible materials, or work envelope..."
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full bg-gray-50 border border-gray-300 rounded-xl p-3 text-xs focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {/* Access conditions & Required Credentials */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Access & Safety Conditions
                </label>
                <input
                  type="text"
                  placeholder="e.g. Safety goggles, closed shoes, lab staff present"
                  value={form.access_conditions}
                  onChange={(e) => setForm({ ...form, access_conditions: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Required Certifications (comma separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. CNC_OPERATOR_ADVANCED, LASER_SAFETY_L1"
                  value={form.required_credentials_str}
                  onChange={(e) => setForm({ ...form, required_credentials_str: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-brand-500 font-mono"
                />
              </div>
            </div>

            {/* Usage rules JSON */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">
                Machine Rules & Checklist (JSON Object)
              </label>
              <textarea
                rows={4}
                value={form.rules_json_str}
                onChange={(e) => setForm({ ...form, rules_json_str: e.target.value })}
                className="w-full font-mono bg-gray-50 border border-gray-300 rounded-xl p-3 text-xs focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {/* Weekly Availability Windows */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-brand-600" /> Weekly Availability Windows
                </label>
                <button
                  type="button"
                  onClick={addWindow}
                  className="inline-flex items-center gap-1 text-xs font-bold text-brand-600 hover:text-brand-700 bg-brand-50 px-2.5 py-1 rounded-lg"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Window
                </button>
              </div>

              <div className="space-y-2">
                {form.availability_windows.map((win, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 bg-gray-50 p-2.5 rounded-xl border border-gray-200"
                  >
                    <select
                      value={win.day_of_week}
                      onChange={(e) => handleWindowChange(idx, "day_of_week", e.target.value)}
                      className="bg-white border border-gray-300 rounded-lg px-2.5 py-1.5 text-xs font-medium"
                    >
                      {days.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>

                    <div className="flex items-center gap-1.5 text-xs">
                      <input
                        type="time"
                        value={win.start_time}
                        onChange={(e) => handleWindowChange(idx, "start_time", e.target.value)}
                        className="bg-white border border-gray-300 rounded-lg px-2 py-1 text-xs"
                      />
                      <span className="text-gray-400">to</span>
                      <input
                        type="time"
                        value={win.end_time}
                        onChange={(e) => handleWindowChange(idx, "end_time", e.target.value)}
                        className="bg-white border border-gray-300 rounded-lg px-2 py-1 text-xs"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => removeWindow(idx)}
                      className="ml-auto text-gray-400 hover:text-rose-600 p-1 rounded-md"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Action buttons */}
            <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
              <Link
                to="/owner/resources"
                className="px-5 py-2.5 rounded-xl border border-gray-300 font-semibold text-xs text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold px-6 py-2.5 rounded-xl text-xs transition shadow-sm shadow-brand-500/20"
              >
                <Save className="w-4 h-4" />
                {submitting ? "Saving..." : isEdit ? "Update Resource" : "Create Resource"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

