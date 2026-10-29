import React from "react";
import { HelpCircle, Award, Clock, Activity, AlertOctagon, Sparkles } from "lucide-react";

export default function WhyThisOutcomeCard({ breakdown, rankingScore }) {
  if (!breakdown || Object.keys(breakdown).length === 0) {
    return null;
  }

  const {
    purpose_priority_score,
    first_time_user_score,
    inverse_recent_usage_score,
    waiting_time_score,
    no_show_penalty,
    explanation_summary,
    factors,
  } = breakdown;

  return (
    <div className="bg-gradient-to-br from-indigo-50/70 via-white to-blue-50/50 border border-indigo-100/90 rounded-2xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-indigo-100/70">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-100 text-indigo-700">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-extrabold text-gray-900 text-sm">
              Why this outcome?
            </h4>
            <p className="text-[11px] text-gray-500">
              Deterministic allocation & waitlist priority score breakdown
            </p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block">
            Priority Score
          </span>
          <span className="text-lg font-black text-indigo-700">
            {rankingScore !== undefined ? Number(rankingScore).toFixed(1) : Number(breakdown.total_score || 0).toFixed(1)}
          </span>
        </div>
      </div>

      {/* Summary Narrative */}
      {explanation_summary && (
        <p className="text-xs text-gray-700 leading-relaxed bg-white/80 p-3 rounded-xl border border-indigo-50">
          {explanation_summary}
        </p>
      )}

      {/* Factor Breakdown Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
        {/* Factor 1: Purpose Tier */}
        <div className="bg-white p-2.5 rounded-xl border border-gray-100 flex items-start gap-2">
          <Award className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" />
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-400 block">
              Tier Priority
            </span>
            <span className="font-bold text-gray-800">
              +{purpose_priority_score || 0} pts
            </span>
            <span className="text-[10px] text-gray-500 block">
              ({factors?.priority_tier || "Standard"})
            </span>
          </div>
        </div>

        {/* Factor 2: First-time user */}
        <div className="bg-white p-2.5 rounded-xl border border-gray-100 flex items-start gap-2">
          <Sparkles className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-400 block">
              First-Time User
            </span>
            <span className="font-bold text-gray-800">
              +{first_time_user_score || 0} pts
            </span>
            <span className="text-[10px] text-gray-500 block">
              {first_time_user_score > 0 ? "Welcome boost" : "Repeat user"}
            </span>
          </div>
        </div>

        {/* Factor 3: Inverse recent usage */}
        <div className="bg-white p-2.5 rounded-xl border border-gray-100 flex items-start gap-2">
          <Activity className="w-3.5 h-3.5 text-blue-600 mt-0.5 shrink-0" />
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-400 block">
              Fair Usage Sharing
            </span>
            <span className="font-bold text-gray-800">
              +{inverse_recent_usage_score || 0} pts
            </span>
            <span className="text-[10px] text-gray-500 block">
              ({factors?.recent_hours_used || 0}h used this week)
            </span>
          </div>
        </div>

        {/* Factor 4: Waiting time */}
        <div className="bg-white p-2.5 rounded-xl border border-gray-100 flex items-start gap-2">
          <Clock className="w-3.5 h-3.5 text-amber-600 mt-0.5 shrink-0" />
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-400 block">
              Anti-Starvation Bonus
            </span>
            <span className="font-bold text-gray-800">
              +{waiting_time_score || 0} pts
            </span>
            <span className="text-[10px] text-gray-500 block">
              ({factors?.hours_waited || 0}h in queue)
            </span>
          </div>
        </div>

        {/* Factor 5: Strike / No-show deduction */}
        <div className="bg-white p-2.5 rounded-xl border border-gray-100 flex items-start gap-2">
          <AlertOctagon className="w-3.5 h-3.5 text-rose-600 mt-0.5 shrink-0" />
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-400 block">
              No-Show Deduction
            </span>
            <span className={`font-bold ${no_show_penalty > 0 ? "text-rose-600" : "text-gray-800"}`}>
              -{no_show_penalty || 0} pts
            </span>
            <span className="text-[10px] text-gray-500 block">
              ({factors?.strike_count || 0} strikes on record)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

