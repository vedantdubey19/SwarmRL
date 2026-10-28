import React from 'react';
import { Canvas } from '@react-three/fiber';
import CameraRig from './components/CameraRig';
import Terrain from './components/Terrain';
import DroneMesh from './components/DroneMesh';
import Dashboard from './components/Dashboard';
import { useSwarmWebSocket } from './hooks/useSwarmWebSocket';

function Scene() {
  return (
    <>
      <color attach="background" args={['#080c14']} />
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[30, 60, 30]}
        intensity={1.5}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <hemisphereLight skyColor="#38bdf8" groundColor="#080c14" intensity={0.3} />

      {/* Exploration Map Ground Plane & World Elements */}
      <Terrain />

      {/* 50-Drone Single InstancedMesh */}
      <DroneMesh />

      {/* Orbit & Follow Dynamic Camera Controls */}
      <CameraRig />
    </>
  );
}

export default function App() {
  // Connect to live WebSocket relay (respecting VITE_WS_URL or fallback)
  useSwarmWebSocket();

  return (
    <div className="relative w-screen h-screen select-none bg-[#080c14] overflow-hidden">
      {/* 3D WebGL Viewport */}
      <Canvas
        shadows
        gl={{ antialias: true, powerPreference: 'high-performance' }}
        camera={{ position: [0, 50, 70], fov: 45 }}
      >
        <Scene />
      </Canvas>

      {/* 4Hz Throttled HUD Overlay */}
      <Dashboard />
    </div>
  );
}
