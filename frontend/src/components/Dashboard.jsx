import React from 'react';
import { useSwarmStore } from '../store/useSwarmStore';
import { Activity, ShieldAlert, Target, Compass, Wifi, Radio, Eye, EyeOff } from 'lucide-react';

export default function Dashboard() {
  const connectionStatus = useSwarmStore((s) => s.connectionStatus);
  const reconnectAttempt = useSwarmStore((s) => s.reconnectAttempt);
  const hudMetrics = useSwarmStore((s) => s.hudMetrics);
  const perfHistory = useSwarmStore((s) => s.perfHistory);
  const selectedDroneId = useSwarmStore((s) => s.selectedDroneId);
  const setSelectedDroneId = useSwarmStore((s) => s.setSelectedDroneId);

  const {
    exploredFraction,
    collisionTotals,
    targetsFound,
    totalTargets,
    activeAgents,
    difficulty,
    fps,
    latencyMs,
    step,
  } = hudMetrics;

  const exploredPct = (exploredFraction * 100).toFixed(1);

  // Connection badge color
  const statusColor =
    connectionStatus === 'connected'
      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      : connectionStatus === 'reconnecting'
      ? 'bg-amber-500/20 text-amber-400 border-amber-500/30 animate-pulse'
      : 'bg-red-500/20 text-red-400 border-red-500/30';

  // Rolling latency SVG points
  const points = perfHistory
    .map((p, idx) => {
      const x = (idx / 29) * 120;
      const y = 30 - Math.min(30, (p.latencyMs / 50) * 30);
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between text-slate-200 select-none">
      {/* Top Bar: Title, Status, Difficulty */}
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-3">
          <div className="bg-slate-900/80 backdrop-blur border border-slate-700/60 rounded-xl px-4 py-2 flex items-center gap-3 shadow-lg pointer-events-auto">
            <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
            <div>
              <h1 className="text-sm font-bold tracking-wider text-slate-100 uppercase">
                SwarmRL Tactical SAR
              </h1>
              <p className="text-xs text-slate-400 font-mono">50-Agent CTDE MAPPO</p>
            </div>
          </div>

          <div
            className={`border rounded-xl px-3 py-1.5 flex items-center gap-2 text-xs font-mono shadow-lg backdrop-blur ${statusColor} pointer-events-auto`}
          >
            <Wifi className="w-3.5 h-3.5" />
            <span className="capitalize">
              {connectionStatus}
              {connectionStatus === 'reconnecting' && ` (retry ${reconnectAttempt})`}
            </span>
          </div>
        </div>

        {/* Right Header: Track Drone, Difficulty and Step */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setSelectedDroneId(selectedDroneId === null ? 0 : null)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-mono flex items-center gap-2 transition cursor-pointer shadow-lg backdrop-blur pointer-events-auto ${
              selectedDroneId !== null
                ? 'bg-purple-600/30 text-purple-300 border-purple-500/50 hover:bg-purple-600/40'
                : 'bg-slate-900/80 text-slate-300 border-slate-700/60 hover:bg-slate-800'
            }`}
          >
            {selectedDroneId !== null ? <Eye className="w-3.5 h-3.5 text-purple-400" /> : <EyeOff className="w-3.5 h-3.5 text-slate-400" />}
            <span>{selectedDroneId !== null ? `Tracking Drone #${selectedDroneId}` : 'Track Drone'}</span>
          </button>

          <div className="bg-slate-900/80 backdrop-blur border border-slate-700/60 rounded-xl px-4 py-2 flex items-center gap-4 text-xs font-mono shadow-lg pointer-events-auto">
            <div>
              <span className="text-slate-400">Step:</span>{' '}
              <span className="text-cyan-300 font-bold">{step}</span>
            </div>
            <div>
              <span className="text-slate-400">Difficulty:</span>{' '}
              <span className="text-amber-400 font-bold">Lvl {difficulty}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar: Tactical Metrics & Mini Performance Chart */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 w-full max-w-4xl">
        {/* Metric 1: Explored Territory */}
        <div className="bg-slate-900/80 backdrop-blur border border-slate-700/60 rounded-xl p-3 shadow-lg pointer-events-auto">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-cyan-400" /> Area Explored
            </span>
            <span className="text-cyan-400 font-mono font-bold">{exploredPct}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
            <div
              className="bg-cyan-400 h-full transition-all duration-300 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, exploredFraction * 100))}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-1 font-mono">
            Grid: 50x50 (2500 cells @ 2m)
          </div>
        </div>

        {/* Metric 2: Targets */}
        <div className="bg-slate-900/80 backdrop-blur border border-slate-700/60 rounded-xl p-3 shadow-lg pointer-events-auto">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5 text-amber-400" /> Targets Recovered
            </span>
            <span className="text-amber-400 font-mono font-bold">
              {targetsFound} / {totalTargets || 4}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
            <div
              className="bg-amber-400 h-full transition-all duration-300 ease-out"
              style={{
                width: `${totalTargets > 0 ? (targetsFound / totalTargets) * 100 : 0}%`,
              }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-1 font-mono">
            Active Drones: {activeAgents} / 50
          </div>
        </div>

        {/* Metric 3: Collisions by Type */}
        <div className="bg-slate-900/80 backdrop-blur border border-slate-700/60 rounded-xl p-3 shadow-lg pointer-events-auto">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" /> Collisions
            </span>
            <span className="text-red-400 font-mono font-bold">
              {collisionTotals.total} total
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1 text-[10px] font-mono mt-1 text-center">
            <div className="bg-slate-800/80 rounded px-1 py-0.5 border border-slate-700">
              <span className="text-slate-400 block">Drone</span>
              <span className="text-red-300 font-bold">{collisionTotals.drone}</span>
            </div>
            <div className="bg-slate-800/80 rounded px-1 py-0.5 border border-slate-700">
              <span className="text-slate-400 block">Obs</span>
              <span className="text-red-300 font-bold">{collisionTotals.obstacle}</span>
            </div>
            <div className="bg-slate-800/80 rounded px-1 py-0.5 border border-slate-700">
              <span className="text-slate-400 block">Bound</span>
              <span className="text-amber-300 font-bold">{collisionTotals.boundary}</span>
            </div>
          </div>
        </div>

        {/* Metric 4: Mini Rolling Perf Sparkline */}
        <div className="bg-slate-900/80 backdrop-blur border border-slate-700/60 rounded-xl p-3 shadow-lg pointer-events-auto">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-purple-400" /> Link Latency
            </span>
            <span className="text-purple-300 font-mono font-bold">
              {latencyMs}ms ({fps} fps)
            </span>
          </div>
          <div className="h-7 w-full flex items-center justify-center bg-slate-950/50 rounded border border-slate-800 overflow-hidden">
            {perfHistory.length > 1 ? (
              <svg className="w-full h-full p-1" viewBox="0 0 120 30" preserveAspectRatio="none">
                <polyline
                  fill="none"
                  stroke="#a855f7"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={points}
                />
              </svg>
            ) : (
              <span className="text-[10px] text-slate-500 font-mono">Syncing link...</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
