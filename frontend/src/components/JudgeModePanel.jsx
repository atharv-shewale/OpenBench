import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import { useLanguage } from "../store/language";
import {
  Gavel,
  User,
  Shield,
  RotateCcw,
  CheckCircle2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Award,
  Layers,
  ArrowRight,
} from "lucide-react";

export default function JudgeModePanel() {
  const { setAuth, user } = useAuthStore();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [expanded, setExpanded] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState(null);
  const [loginLoading, setLoginLoading] = useState(null);
  const [completedSteps, setCompletedSteps] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("openbench_judge_steps") || "{}");
    } catch {
      return {};
    }
  });

  const toggleStep = (stepKey) => {
    setCompletedSteps((prev) => {
      const next = { ...prev, [stepKey]: !prev[stepKey] };
      localStorage.setItem("openbench_judge_steps", JSON.stringify(next));
      return next;
    });
  };

  const handleQuickLogin = async (roleKey) => {
    setLoginLoading(roleKey);
    try {
      const { data: tokens } = await api.post(`/auth/demo-login/${roleKey}`);
      const { data: me } = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });
      setAuth(me, tokens.access_token, tokens.refresh_token);
      setResetMessage(`Logged in as ${me.full_name} (${me.role.toUpperCase()})`);
      setTimeout(() => setResetMessage(null), 3000);
    } catch (err) {
      alert("Failed to quick-login with demo role.");
    } finally {
      setLoginLoading(null);
    }
  };

  const handleResetDemoData = async () => {
    if (!window.confirm("Reset OpenBench database back to pristine initial seed state?")) return;
    setResetting(true);
    try {
      await api.post("/admin/reset-demo");
      setResetMessage("Database reset successfully! Pristine test data restored.");
      setTimeout(() => {
        setResetMessage(null);
        window.location.reload();
      }, 1500);
    } catch (err) {
      // If unauthorized, fallback to normal seed
      try {
        await api.post("/admin/seed?wipe=true");
        setResetMessage("Seed data wiped and reinstated.");
        setTimeout(() => window.location.reload(), 1500);
      } catch (e2) {
        alert("Failed to reset demo data.");
      }
    } finally {
      setResetting(false);
    }
  };

  const roles = [
    { key: "admin", label: "Admin", email: "platform.admin@openbench.in", color: "bg-purple-100 text-purple-800 border-purple-200" },
    { key: "owner", label: "Lab Owner", email: "dr.anita.desai@vidyasagar.ac.in", color: "bg-amber-100 text-amber-800 border-amber-200" },
    { key: "manager", label: "Lab Manager", email: "priya.sharma@vidyasagar.ac.in", color: "bg-blue-100 text-blue-800 border-blue-200" },
    { key: "apprentice", label: "ITI Apprentice", email: "rahul.mondal@iti-jadavpur.ac.in", color: "bg-emerald-100 text-emerald-800 border-emerald-200" },
    { key: "msme", label: "MSME Engineer", email: "sneha.patil@patilprecision.com", color: "bg-teal-100 text-teal-800 border-teal-200" },
  ];

  const journeySteps = [
    { id: "s1", title: t("step1"), desc: t("step1Desc"), link: "/equipment/1" },
    { id: "s2", title: t("step2"), desc: t("step2Desc"), link: "/equipment/1" },
    { id: "s3", title: t("step3"), desc: t("step3Desc"), link: "/dashboard" },
    { id: "s4", title: t("step4"), desc: t("step4Desc"), link: "/manager/review-queue" },
    { id: "s5", title: t("step5"), desc: t("step5Desc"), link: "/bookings/1/session" },
    { id: "s6", title: t("step6"), desc: t("step6Desc"), link: "/bookings/1/session" },
    { id: "s7", title: t("step7"), desc: t("step7Desc"), link: "/bookings/1/session" },
    { id: "s8", title: t("step8"), desc: t("step8Desc"), link: "/dashboard" },
    { id: "s9", title: t("step9"), desc: t("step9Desc"), link: "/bookings/1/session" },
    { id: "s10", title: t("step10"), desc: t("step10Desc"), link: "/fairness-simulator" },
  ];

  const completedCount = Object.values(completedSteps).filter(Boolean).length;

  return (
    <section
      aria-label="Judge Evaluation Mode"
      className="bg-white rounded-3xl border-2 border-indigo-200/90 shadow-sm overflow-hidden"
    >
      {/* Top Bar Banner */}
      <div className="bg-gradient-to-r from-indigo-900 via-slate-900 to-indigo-950 text-white p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-500/30 border border-indigo-400/40 flex items-center justify-center text-indigo-300">
            <Gavel className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-black tracking-tight text-white">
                Hackathon Judge Evaluation Mode
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                10-Step Interactive Tour
              </span>
            </div>
            <p className="text-xs text-indigo-200/80 mt-0.5">
              Instant one-click role switching, full lifecycle checklist, and clean data reset for evaluators.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          {/* Reset Demo Button */}
          <button
            onClick={handleResetDemoData}
            disabled={resetting}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600/90 hover:bg-rose-600 text-white font-bold text-xs rounded-xl shadow-xs transition"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resetting ? "animate-spin" : ""}`} />
            {resetting ? t("resetting") : t("resetDemoData")}
          </button>

          <button
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            className="p-1.5 text-indigo-300 hover:text-white rounded-lg hover:bg-white/10 transition"
          >
            {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {resetMessage && (
        <div className="bg-emerald-50 border-b border-emerald-200 p-3 text-xs text-emerald-800 font-bold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{resetMessage}</span>
        </div>
      )}

      {expanded && (
        <div className="p-6 sm:p-8 space-y-6">
          {/* ── 1. ONE-CLICK LOGIN AS EACH ROLE ──────────────────────────────── */}
          <div className="space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500 block">
              {t("quickLoginAs")}
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {roles.map((r) => {
                const isCurrent = user?.email === r.email;
                return (
                  <button
                    key={r.key}
                    onClick={() => handleQuickLogin(r.key)}
                    disabled={loginLoading === r.key}
                    className={`p-3 rounded-2xl border text-left transition flex flex-col justify-between ${
                      isCurrent
                        ? "ring-2 ring-brand-500 bg-brand-50/50 border-brand-300"
                        : "bg-gray-50 hover:bg-gray-100/80 border-gray-200"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full border ${r.color}`}>
                        {r.label}
                      </span>
                      {isCurrent && (
                        <span className="text-[10px] font-bold text-brand-600">Active ●</span>
                      )}
                    </div>
                    <span className="text-xs font-bold text-gray-900 truncate block">
                      {loginLoading === r.key ? "Authenticating..." : r.email.split("@")[0]}
                    </span>
                    <span className="text-[10px] text-gray-400 truncate block">
                      @{r.email.split("@")[1]}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── 2. "TRY THE FULL JOURNEY" 10-STEP INTERACTIVE CHECKLIST ───────── */}
          <div className="pt-2 border-t border-gray-100 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-base font-black text-gray-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-600" />
                  {t("journeyTitle")}
                </h3>
                <p className="text-xs text-gray-500">
                  {t("journeySubtitle")}
                </p>
              </div>

              <div className="flex items-center gap-2 text-xs font-bold text-gray-600">
                <span>Progress:</span>
                <span className="px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200">
                  {completedCount} / 10 Completed
                </span>
              </div>
            </div>

            {/* Checklist Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              {journeySteps.map((step) => {
                const isDone = !!completedSteps[step.id];
                return (
                  <div
                    key={step.id}
                    className={`p-3.5 rounded-2xl border transition flex items-start justify-between gap-3 ${
                      isDone
                        ? "bg-emerald-50/50 border-emerald-200"
                        : "bg-gray-50/80 hover:bg-gray-50 border-gray-200"
                    }`}
                  >
                    <div className="flex items-start gap-2.5">
                      <input
                        type="checkbox"
                        checked={isDone}
                        onChange={() => toggleStep(step.id)}
                        className="mt-1 rounded border-gray-300 text-brand-600 focus:ring-brand-500 w-4 h-4 cursor-pointer"
                        id={`check-${step.id}`}
                      />
                      <label htmlFor={`check-${step.id}`} className="cursor-pointer">
                        <span className={`text-xs font-bold block ${isDone ? "text-emerald-950 line-through" : "text-gray-900"}`}>
                          {step.title}
                        </span>
                        <span className="text-[11px] text-gray-500 block mt-0.5 leading-snug">
                          {step.desc}
                        </span>
                      </label>
                    </div>

                    <Link
                      to={step.link}
                      className="shrink-0 text-xs font-bold text-brand-600 hover:text-brand-800 bg-white border border-gray-200 hover:border-brand-300 px-3 py-1.5 rounded-xl shadow-2xs transition inline-flex items-center gap-1"
                    >
                      {t("tryStep")}
                    </Link>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

