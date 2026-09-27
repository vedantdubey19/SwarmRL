import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export default function PolishedDummySwarm({ count = 50 }) {
  const groupRef = useRef();

  // Generate 50 procedural drone coordinate offsets matching terrain bounds
  const agentData = useMemo(() => {
    const agents = [];
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const radius = 8 + (i % 6) * 7.5;
      const x = Math.cos(angle) * radius + ((i % 4) - 1.5) * 3;
      const z = Math.sin(angle) * radius + ((i % 3) - 1) * 3;

      // Elevation based on Day 04 terrain equation + height buffer
      const baseElevation =
        Math.sin(x * 0.08) * Math.cos(z * 0.08) * 3.5 +
        Math.sin(x * 0.03 + 1.2) * Math.cos(z * 0.03 + 0.8) * 4.0 +
        5.0;

      agents.push({
        id: `agent-${String(i + 1).padStart(2, '0')}`,
        basePos: [x, baseElevation, z],
        phaseOffset: i * 0.35,
        speed: 1.5 + (i % 3) * 0.4,
      });
    }
    return agents;
  }, [count]);

  // Subtle aerodynamic hover bobbing
  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    groupRef.current.children.forEach((child, idx) => {
      const agent = agentData[idx];
      if (agent) {
        child.position.y = agent.basePos[1] + Math.sin(t * agent.speed + agent.phaseOffset) * 0.25;
      }
    });
  });

  return (
    <group ref={groupRef}>
      {agentData.map((agent) => (
        <group key={agent.id} position={agent.basePos}>
          {/* Main Airframe Core */}
          <mesh castShadow>
            <octahedronGeometry args={[0.4, 0]} />
            <meshStandardMaterial
              color="#38bdf8"
              emissive="#0284c7"
              emissiveIntensity={1.8}
              roughness={0.2}
              metalness={0.8}
            />
          </mesh>

          {/* Navigation Halo Ring */}
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.65, 0.75, 24]} />
            <meshBasicMaterial color="#00f0ff" side={THREE.DoubleSide} transparent opacity={0.6} />
          </mesh>

          {/* Downward Sensor Search Frustum (Radar Beam) */}
          <mesh position={[0, -1.2, 0]}>
            <coneGeometry args={[1.0, 2.4, 16, 1, true]} />
            <meshBasicMaterial
              color="#0284c7"
              wireframe
              transparent
              opacity={0.15}
              side={THREE.DoubleSide}
            />
          </mesh>
        </group>
      ))}
    </group>
  );
}