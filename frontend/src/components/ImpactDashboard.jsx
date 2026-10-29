import React, { useState, useEffect } from "react";
import api from "../api/client";
import { useLanguage } from "../store/language";
import {
  TrendingUp,
  Clock,
  Coins,
  ShieldCheck,
  Building,
  Users,
  AlertCircle,
  Zap,
} from "lucide-react";

export default function ImpactDashboard() {
  const { t } = useLanguage();
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/analytics/impact")
      .then((res) => setImpact(res.data))
      .catch((err) => console.error("Failed to load impact metrics", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 text-center text-xs text-gray-400 bg-white rounded-3xl border border-gray-100">
        Loading impact benchmarks...
      </div>
    );
  }

  if (!impact) return null;

  return (
    <section
      aria-labelledby="impact-heading"
      className="bg-gradient-to-br from-white via-indigo-50/20 to-brand-50/30 rounded-3xl border border-indigo-100 p-6 sm:p-8 shadow-xs space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-indigo-100/70">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-brand-50 text-brand-600">
              <TrendingUp className="w-5 h-5" />
            </span>
            <h2 id="impact-heading" className="text-xl font-black text-gray-900 tracking-tight">
              {t("impactTitle")}
            </h2>
          </div>
          <p className="text-xs text-gray-500 mt-1 pl-9">
            {t("impactSubtitle")}
          </p>
        </div>

        <span className="self-start sm:self-auto text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-full bg-amber-50 text-amber-900 border border-amber-200">
          {t("estimateNotice")}
        </span>
      </div>

      {/* 3 Main Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Idle Hours Unlocked */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-2xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
              {t("idleHoursUnlocked")}
            </span>
            <span className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
              <Clock className="w-4 h-4" />
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-gray-900">
              {impact.idle_hours_unlocked}
            </span>
            <span className="text-xs font-bold text-blue-600">hours</span>
          </div>
          <p className="text-[11px] text-gray-500">
            Across mechanical testing, PCB routing, 3D printing & laser machining.
          </p>
        </div>

        {/* Card 2: Equipment Value Utilised */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-2xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
              {t("equipmentValue")}
            </span>
            <span className="p-1.5 rounded-lg bg-purple-50 text-purple-600">
              <Building className="w-4 h-4" />
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-purple-700">
              ₹{impact.equipment_value_utilised_cr}
            </span>
            <span className="text-xs font-bold text-purple-600">Crores</span>
          </div>
          <p className="text-[11px] text-gray-500">
            Capital asset valuation of high-precision college laboratory instruments.
          </p>
        </div>

        {/* Card 3: Estimated Cost Saved */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-2xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
              {t("estimatedSavings")}
            </span>
            <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
              <Coins className="w-4 h-4" />
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-emerald-700">
              ₹{impact.estimated_cost_saved_lakhs}
            </span>
            <span className="text-xs font-bold text-emerald-600">Lakhs</span>
          </div>
          <p className="text-[11px] text-gray-500">
            Saved by students & local micro-enterprises vs commercial NABL tariffs.
          </p>
        </div>
      </div>

      {/* Benchmark Disclaimer Callout */}
      <div className="p-3.5 bg-white/80 border border-indigo-100 rounded-2xl flex items-start gap-2.5 text-xs text-gray-600">
        <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="text-gray-900">Benchmark Methodology: </strong>
          {t("estimateDisclaimer")}
        </p>
      </div>
    </section>
  );
}

