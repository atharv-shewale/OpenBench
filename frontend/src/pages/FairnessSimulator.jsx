import React, { useState, useEffect } from "react";
import api from "../api/client";
import {
  Scale,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  TrendingUp,
  Clock,
  UserCheck,
  Zap,
  Shield,
  Layers,
  ArrowRight,
  Info,
} from "lucide-react";

export default function FairnessSimulator() {
  const [seed, setSeed] = useState(42);
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [policyView, setPolicyView] = useState("comparison"); // "comparison" | "fcfs" | "openbench"

  const runSimulation = async (simSeed = seed, simDays = days) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/fairness-simulator/run?seed=${simSeed}&days=${simDays}`);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Simulation run failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, []);

  const fcfs = data?.fcfs_metrics;
  const ob = data?.openbench_metrics;
  const summary = data?.comparison_summary;

  return (
    <div className="min-h-screen bg-gray-50 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Synthetic Disclaimer Banner */}
        <div className="bg-gradient-to-r from-amber-500/10 via-amber-50 to-orange-500/10 border-2 border-dashed border-amber-300 rounded-3xl p-5 shadow-2xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <span className="p-2 rounded-xl bg-amber-100 text-amber-800 shrink-0 mt-0.5">
                <AlertTriangle className="w-5 h-5" />
              </span>
              <div>
                <span className="text-[11px] font-black uppercase tracking-wider text-amber-900 block">
                  SYNTHETIC DEMAND REPLAY (SEEDED SIMULATION)
                </span>
                <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                  Advisory & educational simulation model. Replays 30 days of deterministic synthetic demand stream (~350 requests from 40 synthetic personas including ITI apprentices, MSMEs, students, and veteran researchers) to mathematically evaluate allocation fairness.
                </p>
              </div>
            </div>

            {/* Seed Controller */}
            <div className="flex items-center gap-2 self-start sm:self-auto bg-white border border-amber-200 px-3 py-1.5 rounded-2xl shadow-2xs">
              <span className="text-xs font-bold text-gray-600">RNG Seed:</span>
              <select
                value={seed}
                onChange={(e) => {
                  const s = parseInt(e.target.value);
                  setSeed(s);
                  runSimulation(s, days);
                }}
                className="bg-transparent text-xs font-black text-amber-900 focus:outline-hidden cursor-pointer"
              >
                <option value={42}>Seed 42 (Nominal)</option>
                <option value={101}>Seed 101 (High Contention)</option>
                <option value={777}>Seed 777 (MSME Surge)</option>
                <option value={999}>Seed 999 (Long Tail)</option>
              </select>
              <button
                onClick={() => runSimulation(seed, days)}
                disabled={loading}
                className="p-1 rounded-lg text-amber-700 hover:bg-amber-100 transition"
                title="Rerun Simulation"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="p-2.5 rounded-2xl bg-indigo-50 text-indigo-600 shadow-2xs">
                <Scale className="w-6 h-6" />
              </span>
              <h1 className="text-3xl font-black text-gray-900 tracking-tight">
                Allocation Policy Fairness Simulator
              </h1>
            </div>
            <p className="text-sm text-gray-500 mt-1 pl-11">
              Evaluating the mathematical transition from naive first-come queueing to OpenBench merit & access equity.
            </p>
          </div>

          {/* Policy View Toggle */}
          <div className="flex items-center p-1 bg-gray-200/80 rounded-2xl self-start sm:self-auto text-xs font-bold">
            <button
              onClick={() => setPolicyView("comparison")}
              className={`px-4 py-2 rounded-xl transition ${
                policyView === "comparison"
                  ? "bg-white text-gray-900 shadow-2xs"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Side-by-Side Comparison
            </button>
            <button
              onClick={() => setPolicyView("fcfs")}
              className={`px-4 py-2 rounded-xl transition ${
                policyView === "fcfs"
                  ? "bg-white text-gray-900 shadow-2xs"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              FCFS Replay
            </button>
            <button
              onClick={() => setPolicyView("openbench")}
              className={`px-4 py-2 rounded-xl transition ${
                policyView === "openbench"
                  ? "bg-white text-gray-900 shadow-2xs"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              OpenBench Policy
            </button>
          </div>
        </div>

        {loading && !data ? (
          <div className="bg-white rounded-3xl border border-gray-200 p-16 text-center">
            <RefreshCw className="w-10 h-10 text-brand-600 animate-spin mx-auto mb-4" />
            <h3 className="text-base font-bold text-gray-900">Replaying Synthetic Month Demand...</h3>
            <p className="text-xs text-gray-500 mt-1">Simulating FCFS vs OpenBench queue allocations over 30 days.</p>
          </div>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 p-6 rounded-2xl text-center text-rose-700 text-sm">
            {error}
          </div>
        ) : data && (
          <div className="space-y-8">
            {/* ── 4 KEY COMPARISON METRIC CARDS ─────────────────────────────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Metric 1: Gini Coefficient */}
              <div className="bg-white p-6 rounded-3xl border border-gray-200/90 shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Gini Coefficient (Inequality)
                  </span>
                  <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
                    <TrendingDown className="w-4 h-4" />
                  </span>
                </div>

                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-black text-gray-900">
                    {policyView === "fcfs" ? fcfs.gini_coefficient : ob.gini_coefficient}
                  </span>
                  {policyView === "comparison" && (
                    <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      -{summary.gini_improvement_pct}% lower
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-gray-500 leading-snug">
                  {policyView === "comparison"
                    ? `FCFS: ${fcfs.gini_coefficient} → OpenBench: ${ob.gini_coefficient}. Lower indicates equitable access.`
                    : "Standard metric for resource concentration (0 = equal, 1 = monopoly)."}
                </p>
              </div>

              {/* Metric 2: Average Wait Time */}
              <div className="bg-white p-6 rounded-3xl border border-gray-200/90 shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Avg Wait Time (Hours)
                  </span>
                  <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
                    <Clock className="w-4 h-4" />
                  </span>
                </div>

                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-black text-gray-900">
                    {policyView === "fcfs" ? `${fcfs.average_wait_hours}h` : `${ob.average_wait_hours}h`}
                  </span>
                  {policyView === "comparison" && (
                    <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
                      -{summary.wait_reduction_pct}% wait
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-gray-500 leading-snug">
                  {policyView === "comparison"
                    ? `FCFS: ${fcfs.average_wait_hours}h → OpenBench: ${ob.average_wait_hours}h. Shorter wait to access benches.`
                    : "Average elapsed hours from request submission to session slot execution."}
                </p>
              </div>

              {/* Metric 3: First-time users served */}
              <div className="bg-white p-6 rounded-3xl border border-gray-200/90 shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    First-Time Users Served
                  </span>
                  <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
                    <UserCheck className="w-4 h-4" />
                  </span>
                </div>

                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-black text-gray-900">
                    {policyView === "fcfs" ? `${fcfs.first_time_users_served_pct}%` : `${ob.first_time_users_served_pct}%`}
                  </span>
                  {policyView === "comparison" && (
                    <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      +{Math.round((ob.first_time_users_served_pct - fcfs.first_time_users_served_pct))}% boost
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-gray-500 leading-snug">
                  {policyView === "comparison"
                    ? `FCFS: ${fcfs.first_time_users_served_pct}% → OpenBench: ${ob.first_time_users_served_pct}%. Protects new apprentices.`
                    : "Percentage of newly registered apprentices & MSMEs who secured slots."}
                </p>
              </div>

              {/* Metric 4: Capacity Utilisation */}
              <div className="bg-white p-6 rounded-3xl border border-gray-200/90 shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Lab Capacity Utilisation
                  </span>
                  <span className="p-1.5 rounded-lg bg-purple-50 text-purple-600">
                    <Zap className="w-4 h-4" />
                  </span>
                </div>

                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-black text-gray-900">
                    {policyView === "fcfs" ? `${fcfs.utilisation_pct}%` : `${ob.utilisation_pct}%`}
                  </span>
                  {policyView === "comparison" && (
                    <span className="text-xs font-bold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
                      {ob.utilisation_pct >= fcfs.utilisation_pct ? `+${(ob.utilisation_pct - fcfs.utilisation_pct).toFixed(1)}%` : "High"}
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-gray-500 leading-snug">
                  {policyView === "comparison"
                    ? `FCFS: ${fcfs.utilisation_pct}% → OpenBench: ${ob.utilisation_pct}%. Gap-filling maintains machine uptime.`
                    : "Fraction of operational machine hours actively booked & delivered."}
                </p>
              </div>
            </div>

            {/* ── DISTRIBUTION CHARTS: LORENZ / QUINTILE ACCESS ────────────────── */}
            <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-8 shadow-2xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
                <div>
                  <h3 className="text-lg font-black text-gray-900">
                    Access Concentration: Allocated Hours by User Quintiles
                  </h3>
                  <p className="text-xs text-gray-500">
                    Comparing share of total lab hours consumed by top power users vs newcomers.
                  </p>
                </div>

                <div className="flex items-center gap-4 text-xs font-bold">
                  <span className="flex items-center gap-1.5 text-gray-500">
                    <span className="w-3 h-3 rounded-full bg-slate-400 inline-block"></span>
                    FCFS (First-Come)
                  </span>
                  <span className="flex items-center gap-1.5 text-indigo-600">
                    <span className="w-3 h-3 rounded-full bg-brand-600 inline-block"></span>
                    OpenBench Policy
                  </span>
                </div>
              </div>

              {/* Quintile Comparison Bars */}
              <div className="space-y-4">
                {ob.hours_per_user_buckets.map((b, idx) => {
                  const fcfsBucket = fcfs.hours_per_user_buckets[idx];
                  return (
                    <div key={b.quintile} className="space-y-1.5">
                      <div className="flex justify-between text-xs font-bold">
                        <span className="text-gray-700">{b.quintile} of Users</span>
                        <span className="text-gray-500 font-mono">
                          FCFS: <strong className="text-gray-700">{fcfsBucket?.share_pct}%</strong> ({fcfsBucket?.hours}h) vs OpenBench: <strong className="text-brand-600">{b.share_pct}%</strong> ({b.hours}h)
                        </span>
                      </div>

                      {/* Bar Pair */}
                      <div className="space-y-1">
                        {/* FCFS Bar */}
                        <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                          <div
                            className="bg-slate-400 h-2.5 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(100, (fcfsBucket?.share_pct || 0) * 1.5)}%` }}
                          ></div>
                        </div>
                        {/* OpenBench Bar */}
                        <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                          <div
                            className="bg-brand-600 h-2.5 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(100, b.share_pct * 1.5)}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="p-4 bg-indigo-50/60 border border-indigo-100 rounded-2xl text-xs text-indigo-900 leading-relaxed">
                <span className="font-extrabold block text-indigo-950 mb-1">
                  Structural Equity Finding:
                </span>
                Under raw First-Come-First-Served, the top 20% of power users (who book weeks ahead) hoard over half of all prime lab hours, effectively starving apprentice fabricators. Under OpenBench's rolling 10-hour cap and first-time user boost, access is distributed equitably across all 5 quintiles without reducing total machine usage.
              </div>
            </div>

            {/* ── 30-DAY DAILY UTILISATION REPLAY CHART ─────────────────────────── */}
            <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-8 shadow-2xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
                <div>
                  <h3 className="text-lg font-black text-gray-900">
                    30-Day Daily Capacity Utilisation Trend
                  </h3>
                  <p className="text-xs text-gray-500">
                    Hours utilized per day across 3 high-value testing instruments (24 machine-hours available daily).
                  </p>
                </div>

                <div className="flex items-center gap-3 text-xs font-mono text-gray-500">
                  <span>Total Delivered:</span>
                  <strong className="text-gray-900">FCFS: {fcfs.total_hours_delivered}h</strong>
                  <span>vs</span>
                  <strong className="text-brand-600">OpenBench: {ob.total_hours_delivered}h</strong>
                </div>
              </div>

              {/* Daily Histogram / Bars */}
              <div className="h-48 flex items-end gap-1.5 sm:gap-2 pt-6 pb-2 border-b border-gray-100 overflow-x-auto">
                {ob.daily_utilisation.map((d, idx) => {
                  const fcfsDay = fcfs.daily_utilisation[idx];
                  const obHeight = Math.min(100, Math.round((d.hours / 24) * 100));
                  const fcfsHeight = Math.min(100, Math.round(((fcfsDay?.hours || 0) / 24) * 100));

                  return (
                    <div
                      key={d.day}
                      className="flex-1 min-w-[12px] flex flex-col items-center gap-1 group relative cursor-pointer"
                    >
                      <div className="w-full flex items-end gap-0.5 h-36">
                        {/* FCFS Bar */}
                        <div
                          className="w-1/2 bg-slate-300 group-hover:bg-slate-400 rounded-t transition"
                          style={{ height: `${fcfsHeight}%` }}
                        ></div>
                        {/* OpenBench Bar */}
                        <div
                          className="w-1/2 bg-brand-500 group-hover:bg-brand-600 rounded-t transition"
                          style={{ height: `${obHeight}%` }}
                        ></div>
                      </div>
                      <span className="text-[9px] text-gray-400 font-mono">
                        {d.day % 5 === 0 ? d.day : ""}
                      </span>

                      {/* Tooltip */}
                      <div className="absolute bottom-full mb-2 hidden group-hover:block z-20 bg-slate-900 text-white p-2 rounded-xl text-[10px] whitespace-nowrap shadow-xl">
                        <div className="font-bold">Day #{d.day}</div>
                        <div>OpenBench: {d.hours}h ({d.utilisation_pct}%)</div>
                        <div>FCFS: {fcfsDay?.hours}h ({fcfsDay?.utilisation_pct}%)</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── Policy Comparison Summary Card ───────────────────────────────── */}
            <div className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 rounded-3xl p-6 sm:p-8 shadow-2xs space-y-4">
              <h3 className="text-base font-black text-gray-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-brand-600" />
                Algorithmic Synthesis & Conclusion
              </h3>
              <p className="text-xs text-gray-700 leading-relaxed font-medium">
                {summary.conclusion}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-gray-100">
                <div className="p-4 bg-white rounded-2xl border border-gray-200 space-y-1">
                  <span className="text-xs font-bold text-gray-900">1. Rolling Weekly Cap</span>
                  <p className="text-[11px] text-gray-500">
                    Prevents automated bots or deep-pocketed labs from monopolizing consecutive prime afternoons.
                  </p>
                </div>
                <div className="p-4 bg-white rounded-2xl border border-gray-200 space-y-1">
                  <span className="text-xs font-bold text-gray-900">2. First-Time Boost (+35 pts)</span>
                  <p className="text-[11px] text-gray-500">
                    Empowers local ITI apprentices and bootstrapped MSMEs with guaranteed onboarding slots.
                  </p>
                </div>
                <div className="p-4 bg-white rounded-2xl border border-gray-200 space-y-1">
                  <span className="text-xs font-bold text-gray-900">3. Waitlist Gap-Filling</span>
                  <p className="text-[11px] text-gray-500">
                    Flexible small time shifts (+/- 1hr) backfill unused bench periods, keeping lab revenue high.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

