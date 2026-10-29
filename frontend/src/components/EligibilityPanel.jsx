import React from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, XCircle, AlertCircle, ShieldAlert, ArrowRight } from "lucide-react";

export default function EligibilityPanel({
  equipment,
  eligibility,
  loading,
  error,
  user,
}) {
  if (!user) {
    return (
      <div className="bg-gradient-to-br from-brand-50 to-indigo-50/50 border border-brand-100 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-gray-900 text-lg flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-brand-600" />
          Am I eligible to book?
        </h3>
        <p className="text-gray-600 text-sm mt-2 leading-relaxed">
          Sign in or create an account to instantly check your equipment qualifications,
          credits, and disciplinary standing.
        </p>
        <div className="mt-4 flex gap-3">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-xl text-sm font-semibold transition shadow-sm shadow-brand-500/20"
          >
            Sign in to check <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-2xl p-6 animate-pulse space-y-4">
        <div className="h-5 bg-gray-200 rounded w-1/3"></div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-100 rounded w-3/4"></div>
          <div className="h-4 bg-gray-100 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error || !eligibility) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-sm text-amber-800">
        <p className="font-semibold flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600" />
          Could not verify eligibility automatically
        </p>
        <p className="mt-1 text-xs">{error || "Please refresh or contact the lab manager."}</p>
      </div>
    );
  }

  const { is_eligible, criteria, user_balance, required_credits, deposit_credits } = eligibility;

  return (
    <div
      className={`border rounded-2xl p-6 transition shadow-sm ${
        is_eligible
          ? "bg-emerald-50/50 border-emerald-200"
          : "bg-rose-50/40 border-rose-200"
      }`}
    >
      <div className="flex items-center justify-between pb-4 border-b border-gray-200/60">
        <div className="flex items-center gap-2.5">
          {is_eligible ? (
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center">
              <XCircle className="w-5 h-5" />
            </div>
          )}
          <div>
            <h3 className="font-bold text-gray-900 text-base">
              {is_eligible ? "You are eligible to book" : "Not yet eligible to book"}
            </h3>
            <p className="text-xs text-gray-500">
              Verified against your certifications and account standing
            </p>
          </div>
        </div>
        <span
          className={`text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
            is_eligible
              ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
              : "bg-rose-100 text-rose-800 border border-rose-300"
          }`}
        >
          {is_eligible ? "Eligible" : "Blocked"}
        </span>
      </div>

      {/* Criteria Breakdown */}
      <div className="mt-4 space-y-3">
        {criteria.map((c, idx) => (
          <div key={idx} className="flex items-start gap-3 text-sm">
            {c.met ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p
                className={`font-semibold text-xs uppercase tracking-wide ${
                  c.met ? "text-gray-700" : "text-rose-900"
                }`}
              >
                {c.criterion}
              </p>
              <p className="text-xs text-gray-600 mt-0.5">{c.details}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Credits Breakdown Footer */}
      <div className="mt-5 pt-4 border-t border-gray-200/60 flex items-center justify-between text-xs text-gray-600">
        <div>
          <span>Your spendable: </span>
          <strong className="text-gray-900 font-bold">{user_balance} credits</strong>
        </div>
        <div>
          <span>Required upfront: </span>
          <strong className="text-gray-900 font-bold">
            {required_credits + deposit_credits} credits
          </strong>{" "}
          <span className="text-gray-500">({required_credits}/hr + {deposit_credits} deposit)</span>
        </div>
      </div>
    </div>
  );
}

