import React from 'react';
import { Canvas } from '@react-three/fiber';
import { Grid } from '@react-three/drei';
import { Radio, Eye, Crosshair } from 'lucide-react';
import CameraRig from './components/CameraRig';
import SwarmManager from './components/SwarmManager';
import { useSwarmStore } from './store/useSwarmStore';

function SimulationCanvas() {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight
        position={[25, 50, 25]}
        intensity={1.5}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <hemisphereLight skyColor="#38bdf8" groundColor="#0f172a" intensity={0.4} />

      {/* Grid Floor */}
      <Grid
        position={[0, -0.01, 0]}
        args={[120, 120]}
        cellSize={2}
        cellThickness={0.7}
        cellColor="#1e293b"
        sectionSize={10}
        sectionThickness={1.4}
        sectionColor="#0284c7"
        fadeDistance={90}
      />

      <SwarmManager />
      <CameraRig />
    </>
  );
}

export default function App() {
  const { cameraMode, setCameraMode, selectedDroneId, setSelectedDroneId, drones } = useSwarmStore();

  return (
    <div className="relative w-screen h-screen select-none bg-[#080c14]">
      {/* Top Left HUD */}
      <header className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 backdrop-blur border border-slate-700/60 px-4 py-2.5 rounded-lg text-white shadow-xl">
        <Radio className="w-5 h-5 text-emerald-400 animate-pulse" />
        <div>
          <h1 className="text-sm font-semibold tracking-wide">SwarmRL Telemetry Viewport</h1>
          <p className="text-xs text-slate-400">Day 03: Basic Drone Mesh Models & Controls</p>
        </div>
      </header>

      {/* Drone Focus Selector HUD */}
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

      {/* View Mode Toggle */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={() => setCameraMode(cameraMode === 'orbit' ? 'follow' : 'orbit')}
          className="flex items-center gap-2 bg-slate-900/80 hover:bg-slate-800 text-xs text-slate-200 border border-slate-700 px-3 py-2 rounded shadow transition-colors"
        >
          <Eye className="w-4 h-4 text-sky-400" />
          Mode: {cameraMode.toUpperCase()}
        </button>
      </div>

      <Canvas
        camera={{ position: [0, 35, 45], fov: 50, near: 0.1, far: 1000 }}
        gl={{ antialias: true, alpha: false }}
      >
        <SimulationCanvas />
      </Canvas>
    </div>
  );
}