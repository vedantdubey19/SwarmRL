import React, { useMemo } from 'react';
import * as THREE from 'three';

export default function DummySwarmSpheres({ count = 45 }) {
  // Generate fixed pseudo-random scatter positions across the map bounds
  const dummyPositions = useMemo(() => {
    const points = [];
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const radius = 10 + (i % 5) * 8;
      const x = Math.cos(angle) * radius + ((i % 3) - 1) * 4;
      const z = Math.sin(angle) * radius + ((i % 2) - 0.5) * 6;
      
      // Calculate elevation to keep spheres floating above local terrain peaks
      const terrainHeight =
        Math.sin(x * 0.08) * Math.cos(z * 0.08) * 3.5 +
        Math.sin(x * 0.03 + 1.2) * Math.cos(z * 0.03 + 0.8) * 4.0;
      
      const y = terrainHeight + 4.5 + (i % 4) * 0.8; // Altitude buffer
      points.push({ id: `dummy-${i + 1}`, pos: [x, y, z] });
    }
    return points;
  }, [count]);

  return (
    <group>
      {dummyPositions.map((agent) => (
        <group key={agent.id} position={agent.pos}>
          {/* Agent core sphere */}
          <mesh castShadow>
            <sphereGeometry args={[0.35, 16, 16]} />
            <meshStandardMaterial
              color="#38bdf8"
              emissive="#0284c7"
              emissiveIntensity={1.2}
              roughness={0.3}
            />
          </mesh>
          {/* Range radar beacon pulse */}
          <mesh>
            <sphereGeometry args={[0.6, 12, 12]} />
            <meshBasicMaterial
              color="#38bdf8"
              wireframe
              transparent
              opacity={0.25}
            />
          </mesh>
        </group>
      ))}
    </group>
  );
}