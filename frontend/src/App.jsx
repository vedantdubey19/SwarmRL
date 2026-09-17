import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import { Radio } from 'lucide-react';

function SwarmScene() {
  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight position={[20, 30, 20]} intensity={1.5} />
      <Grid
        position={[0, -0.01, 0]}
        args={[100, 100]}
        cellSize={2}
        cellThickness={0.8}
        cellColor="#1e293b"
        sectionSize={10}
        sectionThickness={1.5}
        sectionColor="#38bdf8"
        fadeDistance={80}
      />
      <OrbitControls makeDefault maxPolarAngle={Math.PI / 2.05} />
    </>
  );
}

export default function App() {
  return (
    <div className="relative w-screen h-screen">
      <header className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 backdrop-blur border border-slate-700/60 px-4 py-2.5 rounded-lg text-white shadow-xl">
        <Radio className="w-5 h-5 text-emerald-400 animate-pulse" />
        <div>
          <h1 className="text-sm font-semibold tracking-wide">SwarmRL Telemetry Canvas</h1>
          <p className="text-xs text-slate-400">Day 01: Three.js Viewport Initialized</p>
        </div>
      </header>

      <Canvas camera={{ position: [0, 35, 45], fov: 50 }} gl={{ antialias: true }}>
        <SwarmScene />
      </Canvas>
    </div>
  );
}