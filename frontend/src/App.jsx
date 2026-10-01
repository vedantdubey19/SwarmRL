import React, { useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { Radio, Eye, Crosshair, Wifi, WifiOff, Activity } from 'lucide-react';
import CameraRig from './components/CameraRig';
import SwarmManager from './components/SwarmManager';
import Terrain from './components/Terrain';
import { useSwarmStore } from './store/useSwarmStore';
import { useSwarmWebSocket } from './hooks/useSwarmWebSocket';

function SimulationCanvas() {
  return (
    <>
      <ambientLight intensity={0.65} />
      <directionalLight
        position={[30, 60, 30]}
        intensity={1.8}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <hemisphereLight skyColor="#38bdf8" groundColor="#080c14" intensity={0.4} />

      {/* Procedural 3D Terrain */}
      <Terrain size={120} segments={64} />

      {/* 50 Dynamic Agents from WebSocket */}
      <SwarmManager />

      <CameraRig />
    </>
  );
}

export default function App() {
  const { isConnected, lastLatencyMs } = useSwarmWebSocket('ws://localhost:8765');
  const { cameraMode, setCameraMode, selectedDroneId, setSelectedDroneId, drones } = useSwarmStore();

  const activeDroneCount = Object.keys(drones).length;

  return (
    <div className="relative w-screen h-screen select-none bg-[#080c14]">
      {/* Top Left Status HUD */}
      <header className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 backdrop-blur border border-slate-700/60 px-4 py-2.5 rounded-lg text-white shadow-xl">
        <Radio className={`w-5 h-5 ${isConnected ? 'text-emerald-400' : 'text-amber-400'} animate-pulse`} />
        <div>
          <h1 className="text-sm font-semibold tracking-wide">SwarmRL Telemetry Viewport</h1>
          <p className="text-xs text-slate-400">Day 07: Live WebSocket Telemetry Binding</p>
        </div>
      </header>

      {/* Stream Metrics HUD */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          {isConnected ? (
            <Wifi className="w-4 h-4 text-emerald-400" />
          ) : (
            <WifiOff className="w-4 h-4 text-rose-500 animate-bounce" />
          )}
          <span>{isConnected ? `STREAM ACTIVE (${lastLatencyMs}ms)` : 'DISCONNECTED'}</span>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          <Activity className="w-4 h-4 text-sky-400" />
          <span>Active Agents: {activeDroneCount}</span>
        </div>

        <button
          onClick={() => setCameraMode(cameraMode === 'orbit' ? 'follow' : 'orbit')}
          className="flex items-center gap-2 bg-slate-900/80 hover:bg-slate-800 text-xs text-slate-200 border border-slate-700 px-3 py-2 rounded shadow transition-colors"
        >
          <Eye className="w-4 h-4 text-sky-400" />
          Mode: {cameraMode.toUpperCase()}
        </button>
      </div>

      {/* Drone Focus Selector */}
      <div className="absolute bottom-4 left-4 z-10 flex items-center gap-2 bg-slate-900/90 backdrop-blur border border-slate-800 p-2 rounded-lg text-xs text-slate-300">
        <Crosshair className="w-4 h-4 text-sky-400" />
        <span>Focus Agent:</span>
        <select
          value={selectedDroneId || ''}
          onChange={(e) => setSelectedDroneId(e.target.value || null)}
          className="bg-slate-800 text-slate-100 border border-slate-700 rounded px-2 py-1 outline-none"
        >
          <option value="">None (Free Orbit)</option>
          {Object.keys(drones).map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </div>

      <Canvas
        camera={{ position: [0, 50, 75], fov: 50, near: 0.1, far: 1000 }}
        gl={{ antialias: true, alpha: false }}
      >
        <SimulationCanvas />
      </Canvas>
    </div>
  );
}