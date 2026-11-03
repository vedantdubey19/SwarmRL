import React from 'react';
import { Canvas } from '@react-three/fiber';
import {
  Radio,
  Eye,
  Crosshair,
  Wifi,
  WifiOff,
  AlertTriangle,
  ShieldAlert,
  Maximize2,
  Gauge,
  Scan,
  Compass,
  Paintbrush,
} from 'lucide-react';
import CameraRig from './components/CameraRig';
import Terrain from './components/Terrain';
import SwarmPipeline from './components/SwarmPipeline';
import GroundPainter from './components/GroundPainter';
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

      {/* 3D Topographical Map */}
      <Terrain size={120} segments={64} />

      {/* Day 18: Dynamic Ground-Painted Explored Grid */}
      <GroundPainter />

      {/* 50 Dynamic Agents */}
      <SwarmPipeline />

      <CameraRig />
    </>
  );
}

export default function App() {
  const { isConnected } = useSwarmWebSocket('ws://localhost:8765');

  const {
    cameraMode,
    setCameraMode,
    selectedDroneId,
    setSelectedDroneId,
    drones,
    totalCollisions,
    showCollisionDebug,
    toggleCollisionDebug,
    showSensorCones,
    toggleSensorCones,
    showGroundPainting,
    toggleGroundPainting,
    coveragePercentage,
    avgLatencyMs,
    networkJitterMs,
    swarmDispersionRadius,
    renderFps,
  } = useSwarmStore();

  const activeDroneCount = Object.keys(drones).length;
  const activeCollisions = Object.values(drones).filter((d) => d.collision).length;

  return (
    <div className="relative w-screen h-screen select-none bg-[#080c14] overflow-hidden">
      {/* Top Left Header */}
      <header className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 backdrop-blur border border-slate-700/60 px-4 py-2.5 rounded-lg text-white shadow-xl">
        <Radio className="w-5 h-5 text-emerald-400 animate-pulse" />
        <div>
          <h1 className="text-sm font-semibold tracking-wide">SwarmRL Telemetry Viewport</h1>
          <p className="text-xs text-slate-400">Day 18: Ground-Painting Search Perception (MAPPO)</p>
        </div>
      </header>

      {/* Top Right HUD Controls & Metrics */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          {isConnected ? (
            <Wifi className="w-4 h-4 text-emerald-400" />
          ) : (
            <WifiOff className="w-4 h-4 text-rose-500 animate-bounce" />
          )}
          <span>{isConnected ? `SYNC (${avgLatencyMs}ms / ±${networkJitterMs}ms)` : 'OFFLINE'}</span>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          <Gauge className="w-4 h-4 text-emerald-400" />
          <span>FPS: {renderFps}</span>
        </div>

        {/* Coverage Percentage Badge */}
        <div className="flex items-center gap-2 bg-sky-950/80 border border-sky-600/70 px-3 py-2 rounded text-xs text-sky-300">
          <Compass className="w-4 h-4 text-sky-400" />
          <span>Area Covered: {coveragePercentage}%</span>
        </div>

        {/* Swarm Dispersion */}
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-700/60 px-3 py-2 rounded text-xs text-slate-300">
          <Maximize2 className="w-4 h-4 text-sky-400" />
          <span>Dispersion: {swarmDispersionRadius}m</span>
        </div>

        {/* Ground Painting Toggle */}
        <button
          onClick={toggleGroundPainting}
          className={`flex items-center gap-1.5 text-xs border px-3 py-2 rounded shadow transition-colors ${
            showGroundPainting
              ? 'bg-sky-900/50 border-sky-500 text-sky-200'
              : 'bg-slate-900/80 border-slate-700 text-slate-400'
          }`}
        >
          <Paintbrush className="w-4 h-4" />
          Heatmap: {showGroundPainting ? 'ON' : 'OFF'}
        </button>

        {/* Sensor Cones Toggle */}
        <button
          onClick={toggleSensorCones}
          className={`flex items-center gap-1.5 text-xs border px-3 py-2 rounded shadow transition-colors ${
            showSensorCones
              ? 'bg-sky-900/50 border-sky-500 text-sky-200'
              : 'bg-slate-900/80 border-slate-700 text-slate-400'
          }`}
        >
          <Scan className="w-4 h-4 text-sky-400" />
          Sensors: {showSensorCones ? 'ON' : 'OFF'}
        </button>

        {/* Collision Debug Wire Toggle */}
        <button
          onClick={toggleCollisionDebug}
          className={`flex items-center gap-1.5 text-xs border px-3 py-2 rounded shadow transition-colors ${
            showCollisionDebug
              ? 'bg-rose-900/40 border-rose-600 text-rose-200'
              : 'bg-slate-900/80 border-slate-700 text-slate-400'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          Debug: {showCollisionDebug ? 'ON' : 'OFF'}
        </button>

        {/* Camera Perspective Mode Toggle */}
        <button
          onClick={() => setCameraMode(cameraMode === 'orbit' ? 'follow' : 'orbit')}
          className="flex items-center gap-2 bg-slate-900/80 hover:bg-slate-800 text-xs text-slate-200 border border-slate-700 px-3 py-2 rounded shadow transition-colors"
        >
          <Eye className="w-4 h-4 text-sky-400" />
          Mode: {cameraMode.toUpperCase()}
        </button>
      </div>

      {/* Focus Selector */}
      <div className="absolute bottom-4 left-4 z-10 flex items-center gap-2 bg-slate-900/90 backdrop-blur border border-slate-800 p-2 rounded-lg text-xs text-slate-300 shadow-xl">
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