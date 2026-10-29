import React, { useState, useEffect } from "react";
import { Server, Sparkles, CheckCircle2, RefreshCw } from "lucide-react";

export default function ColdStartNotice() {
  const [isWakingUp, setIsWakingUp] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [isAwake, setIsAwake] = useState(false);

  useEffect(() => {
    let timer = null;
    let pollInterval = null;
    let isMounted = true;

    // Fast check: ping /api/health
    const checkHealth = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3500);
        const res = await fetch("/api/health", { signal: controller.signal });
        clearTimeout(timeoutId);
        if (res.ok) {
          if (isMounted) {
            setIsAwake(true);
            setTimeout(() => {
              if (isMounted) setIsWakingUp(false);
            }, 800);
          }
          return true;
        }
      } catch (err) {
        // If slow, aborted, or connection refused, backend is sleeping (cold start)
        if (isMounted) setIsWakingUp(true);
        return false;
      }
      return false;
    };

    checkHealth().then((ok) => {
      if (!ok) {
        // Start counter
        timer = setInterval(() => {
          setElapsed((prev) => prev + 1);
        }, 1000);

        // Poll health every 3 seconds until awake
        pollInterval = setInterval(async () => {
          const healthy = await checkHealth();
          if (healthy) {
            clearInterval(pollInterval);
            clearInterval(timer);
          }
        }, 3000);
      }
    });

    return () => {
      isMounted = false;
      if (timer) clearInterval(timer);
      if (pollInterval) clearInterval(pollInterval);
    };
  }, []);

  if (!isWakingUp) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 max-w-md w-full p-4 animate-in fade-in slide-in-from-bottom-5 duration-300">
      <div className="bg-slate-900/95 backdrop-blur-md text-white border border-indigo-500/40 rounded-2xl p-4 shadow-2xl space-y-3">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center text-indigo-400 shrink-0">
            {isAwake ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <Server className="w-5 h-5 animate-pulse text-amber-400" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                {isAwake ? "Server Connected!" : "Waking up server, please wait..."}
              </h4>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-indigo-300 border border-slate-700">
                {elapsed}s
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              {isAwake
                ? "Backend is live and responsive! Loading data..."
                : "Render free-tier instances sleep when idle. OpenBench is spinning up (takes ~25–40s)."}
            </p>
          </div>
        </div>

        {/* Progress pulse bar */}
        {!isAwake && (
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-500 via-amber-400 to-emerald-400 h-1.5 w-full animate-pulse"></div>
          </div>
        )}
      </div>
    </div>
  );
}

