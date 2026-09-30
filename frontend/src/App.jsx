import React, { useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { Radio, Eye, Mountain, ShieldCheck, Activity } from 'lucide-react';
import CameraRig from './components/CameraRig';
import Terrain from './components/Terrain';
import PolishedDummySwarm from './components/PolishedDummySwarm';
import { useSwarmStore } from './store/useSwarmStore';

function SimulationCanvas() {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight
        position={[30, 60, 30]}
        intensity={1.8}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <hemisphereLight skyColor="#38bdf8" groundColor="#080c14" intensity={0.4} />

      {/* Topographical Map */}
      <Terrain size={120} segments={64} />

      {/* Polished 50-Agent Dummy Swarm */}
      <PolishedDummySwarm count={50} />

      <CameraRig />
    </>
  );
}

export default function App() {
  const { cameraMode, setCameraMode } = useSwarmStore();

  return (
    <div className="relative w-screen h-screen select-none bg-[#080c14]">
      {/* Top Left HUD */}
      <header className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 backdrop-blur border border-slate-700/60 px-4 py-2.5 rounded-lg text-white shadow-xl">
        <Radio className={`w-5 h-5 ${isConnected ? 'text-emerald-400' : 'text-amber-400'} animate-pulse`} />
        <div>
          <h1 className="text-sm font-semibold tracking-wide">SwarmRL Telemetry Viewport</h1>
          <p className="text-xs text-slate-400">Day 05: 50-Agent Polished Swarm & M1 Baseline</p>
        </div>
      </header>

      {/* Top Right Status & Controls */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          <Activity className="w-4 h-4 text-sky-400" />
          <span>Swarm Count: 50 Agents</span>
        </div>
        <div className="flex items-center gap-2 bg-slate-900/80 border border-emerald-700/60 px-3 py-2 rounded text-xs text-emerald-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Milestone 1 Ready</span>
        </div>
        <button
          onClick={() => setCameraMode(cameraMode === 'orbit' ? 'follow' : 'orbit')}
          className="flex items-center gap-2 bg-slate-900/80 hover:bg-slate-800 text-xs text-slate-200 border border-slate-700 px-3 py-2 rounded shadow transition-colors"
        >
          <Eye className="w-4 h-4 text-sky-400" />
          Mode: {cameraMode.toUpperCase()}
        </button>
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