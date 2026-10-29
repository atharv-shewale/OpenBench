import React, { useState, useEffect, useRef } from "react";
import api from "../api/client";
import {
  Activity,
  Power,
  Zap,
  Radio,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Cpu,
} from "lucide-react";

export default function MachineSimulatorPanel({ equipmentId, equipmentName }) {
  const [isActive, setIsActive] = useState(false);
  const [powerWatts, setPowerWatts] = useState(450);
  const [activityType, setActivityType] = useState("spindle_run");
  const [autoHeartbeat, setAutoHeartbeat] = useState(false);
  const [lastSignalTime, setLastSignalTime] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const heartbeatRef = useRef(null);

  const emitSignal = async (active = isActive) => {
    if (!equipmentId) return;
    setSubmitting(true);
    try {
      const res = await api.post(`/equipment/${equipmentId}/usage-signal`, {
        is_active: active,
        power_watts: active ? powerWatts : 15.0,
        activity_type: active ? activityType : "idle",
        telemetry: {
          simulated: true,
          voltage: 230,
          current_amps: active ? (powerWatts / 230).toFixed(2) : 0.05,
          vibration_frequency_hz: active ? 120 : 0,
        },
        simulated: true,
      });
      setLastSignalTime(new Date(res.data.signal_received_at));
      setStatusMessage(`Signal ACK at ${new Date(res.data.signal_received_at).toLocaleTimeString()}`);
    } catch (err) {
      console.error(err);
      setStatusMessage("Failed to emit simulated usage signal.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActivity = () => {
    const nextActive = !isActive;
    setIsActive(nextActive);
    emitSignal(nextActive);
  };

  useEffect(() => {
    if (autoHeartbeat) {
      heartbeatRef.current = setInterval(() => {
        emitSignal(isActive);
      }, 10000); // 10 second pulse
    } else if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
    }
    return () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    };
  }, [autoHeartbeat, isActive, powerWatts, activityType, equipmentId]);

  return (
    <div className="bg-slate-900 border border-slate-700/80 rounded-3xl p-6 text-white shadow-lg overflow-hidden relative">
      {/* Simulation Badge */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-black text-sm text-white tracking-tight">
                Machine Simulator Panel
              </span>
              <span className="bg-amber-400/20 text-amber-300 border border-amber-400/40 text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full">
                SIMULATED TELEMETRY (DEMO)
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Mock IoT sensor stream for {equipmentName || `Equipment #${equipmentId}`}.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2.5 h-2.5 rounded-full ${isActive ? "bg-emerald-400 animate-ping" : "bg-slate-500"}`} />
          <span className={`font-bold ${isActive ? "text-emerald-400" : "text-slate-400"}`}>
            {isActive ? "SIMULATING ACTIVE WORK" : "SIMULATING IDLE"}
          </span>
        </div>
      </div>

      {/* Simulator Controls */}
      <div className="py-5 grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
        {/* Toggle Button */}
        <div>
          <label className="block text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-2">
            Simulated Power State
          </label>
          <button
            type="button"
            onClick={handleToggleActivity}
            disabled={submitting}
            className={`w-full py-3 px-4 rounded-2xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition shadow-sm ${
              isActive
                ? "bg-rose-600 hover:bg-rose-700 text-white shadow-rose-600/30"
                : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/30"
            }`}
          >
            <Power className="w-4 h-4" />
            {isActive ? "Stop Activity" : "Start Activity"}
          </button>
        </div>

        {/* Load / Wattage */}
        <div>
          <label className="block text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-2 flex items-center justify-between">
            <span>Simulated Power Draw:</span>
            <span className="text-amber-400 font-bold font-mono">{isActive ? `${powerWatts} W` : "15 W (Standby)"}</span>
          </label>
          <input
            type="range"
            min="50"
            max="2500"
            step="50"
            value={powerWatts}
            disabled={!isActive}
            onChange={(e) => setPowerWatts(Number(e.target.value))}
            className="w-full accent-amber-400 h-2 bg-slate-800 rounded-lg cursor-pointer"
          />
        </div>

        {/* Activity Profile */}
        <div>
          <label className="block text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-2">
            Simulated Operation
          </label>
          <select
            value={activityType}
            disabled={!isActive}
            onChange={(e) => setActivityType(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl py-2 px-3 text-xs font-bold focus:ring-2 focus:ring-amber-400"
          >
            <option value="spindle_run">Milling / Spindle Cut</option>
            <option value="laser_cut">CO2 Laser Pulse</option>
            <option value="hydraulic_press">Hydraulic Load Test</option>
            <option value="3d_print_extrusion">Extrusion Layer</option>
          </select>
        </div>
      </div>

      {/* Manual Pulse & Auto Heartbeat Footer */}
      <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => emitSignal(isActive)}
            disabled={submitting}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold px-3.5 py-1.5 rounded-xl flex items-center gap-1.5 transition"
          >
            <Radio className={`w-3.5 h-3.5 text-amber-400 ${submitting ? "animate-spin" : ""}`} />
            Emit Heartbeat Signal
          </button>

          <label className="flex items-center gap-2 cursor-pointer text-slate-300 font-medium">
            <input
              type="checkbox"
              checked={autoHeartbeat}
              onChange={(e) => setAutoHeartbeat(e.target.checked)}
              className="rounded border-slate-700 text-amber-500 focus:ring-amber-400"
            />
            <span>Auto-pulse (10s)</span>
          </label>
        </div>

        <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-indigo-400" />
          <span>
            {statusMessage || (lastSignalTime ? `Last ACK: ${lastSignalTime.toLocaleTimeString()}` : "No signals emitted yet")}
          </span>
        </div>
      </div>
    </div>
  );
}
