import React, { useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { Radio, Eye, Mountain, Crosshair, Wifi } from 'lucide-react';
import CameraRig from './components/CameraRig';
import SwarmManager from './components/SwarmManager';
import Terrain from './components/Terrain';
import { useSwarmStore } from './store/useSwarmStore';

function SimulationCanvas() {
  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight
        position={[30, 60, 30]}
        intensity={1.8}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <hemisphereLight skyColor="#38bdf8" groundColor="#080c14" intensity={0.4} />

      {/* 3D Topographical Map */}
      <Terrain size={120} segments={64} />

      {/* Active Drone Mesh Units driven by live WebSocket stream */}
      <SwarmManager />

      <CameraRig />
    </>
  );
}

export default function App() {
  const {
    cameraMode,
    setCameraMode,
    selectedDroneId,
    setSelectedDroneId,
    drones,
    isConnected,
    connectWebSocket,
  } = useSwarmStore();

  useEffect(() => {
    connectWebSocket();
  }, [connectWebSocket]);

  const activeDroneCount = Object.keys(drones).length;

  return (
    <div className="relative w-screen h-screen select-none bg-[#080c14]">
      {/* Top Left HUD */}
      <header className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 backdrop-blur border border-slate-700/60 px-4 py-2.5 rounded-lg text-white shadow-xl">
        <Radio className={`w-5 h-5 ${isConnected ? 'text-emerald-400' : 'text-amber-400'} animate-pulse`} />
        <div>
          <h1 className="text-sm font-semibold tracking-wide">SwarmRL Telemetry Viewport</h1>
          <p className="text-xs text-slate-400">
            {isConnected ? `Streaming live telemetry (${activeDroneCount} active drones)` : 'Connecting to relay...'}
          </p>
        </div>
      </header>

      {/* Status Badges */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          <Wifi className={`w-4 h-4 ${isConnected ? 'text-emerald-400' : 'text-rose-400'}`} />
          <span>{isConnected ? 'Relay: Connected' : 'Relay: Offline'}</span>
        </div>
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          <Mountain className="w-4 h-4 text-emerald-400" />
          <span>Terrain: Displaced Mesh (64 seg)</span>
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
        camera={{ position: [0, 50, 70], fov: 50, near: 0.1, far: 1000 }}
        gl={{ antialias: true, alpha: false }}
      >
        <SimulationCanvas />
      </Canvas>
    </div>
  );
}