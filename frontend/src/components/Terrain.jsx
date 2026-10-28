import React from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { mutableSimState, useSwarmStore } from '../store/useSwarmStore';

const sharedDataTexture = new THREE.DataTexture(
  mutableSimState.gridBuffer,
  50,
  50,
  THREE.RGBAFormat,
  THREE.UnsignedByteType
);
sharedDataTexture.minFilter = THREE.LinearFilter;
sharedDataTexture.magFilter = THREE.NearestFilter;
sharedDataTexture.wrapS = THREE.ClampToEdgeWrapping;
sharedDataTexture.wrapT = THREE.ClampToEdgeWrapping;
sharedDataTexture.flipY = false;
sharedDataTexture.needsUpdate = true;

export default function Terrain() {
  const world = useSwarmStore((s) => s.world);

  useFrame(() => {
    if (mutableSimState.gridNeedsUpdate) {
      sharedDataTexture.needsUpdate = true;
      mutableSimState.gridNeedsUpdate = false;
    }
  });

  // Extract obstacles & targets
  const obstacles = world?.obstacles || [];
  const targets = world?.targets || [];

  return (
    <group>
      {/* Exploration Map Ground Plane: 100m x 100m at Y = 0 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <planeGeometry args={[100, 100]} />
        <meshStandardMaterial
          map={sharedDataTexture}
          roughness={0.6}
          metalness={0.2}
        />
      </mesh>

      {/* Subtle world boundary grid frame */}
      <gridHelper args={[100, 50, '#38bdf8', '#1e293b']} position={[0, 0.01, 0]} />

      {/* World Boundary Wireframe Box (X: -50..50, Y: 0..20, Z: -50..50) */}
      <mesh position={[0, 10, 0]}>
        <boxGeometry args={[100, 20, 100]} />
        <meshBasicMaterial
          color="#0ea5e9"
          wireframe
          transparent
          opacity={0.15}
        />
      </mesh>

      {/* World Obstacles */}
      {obstacles.map((obs, idx) => {
        const shape = obs.shape || (obs.radius ? 'cylinder' : 'box');
        const pos = obs.position || [obs.x || 0, obs.y || 0, obs.z || 0];

        if (shape === 'cylinder' || obs.radius) {
          const r = obs.radius || 2;
          const h = obs.height || 10;
          return (
            <mesh key={`obs-${idx}`} position={[pos[0], h / 2, pos[2]]} castShadow receiveShadow>
              <cylinderGeometry args={[r, r, h, 16]} />
              <meshStandardMaterial color="#334155" roughness={0.7} metalness={0.3} />
            </mesh>
          );
        }

        const size = obs.size || [obs.dx || 4, obs.dy || 10, obs.dz || 4];
        return (
          <mesh key={`obs-${idx}`} position={[pos[0], size[1] / 2, pos[2]]} castShadow receiveShadow>
            <boxGeometry args={[size[0], size[1], size[2]]} />
            <meshStandardMaterial color="#334155" roughness={0.7} metalness={0.3} />
          </mesh>
        );
      })}

      {/* World Targets */}
      {targets.map((tgt, idx) => {
        const pos = tgt.position || [tgt.x || 0, tgt.y || 1, tgt.z || 0];
        const isFound = tgt.found || false;

        return (
          <group key={`tgt-${idx}`} position={[pos[0], pos[1], pos[2]]}>
            <mesh castShadow>
              <sphereGeometry args={[1.0, 16, 16]} />
              <meshStandardMaterial
                color={isFound ? '#10b981' : '#eab308'}
                emissive={isFound ? '#059669' : '#ca8a04'}
                emissiveIntensity={isFound ? 0.5 : 2.0}
                roughness={0.2}
              />
            </mesh>
            {/* Target Beacon Pulse Cylinder */}
            <mesh position={[0, 5, 0]}>
              <cylinderGeometry args={[0.08, 0.08, 10, 8]} />
              <meshBasicMaterial
                color={isFound ? '#10b981' : '#facc15'}
                transparent
                opacity={isFound ? 0.2 : 0.6}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}
