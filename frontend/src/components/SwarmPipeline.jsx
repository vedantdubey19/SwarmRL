import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';

function SwarmAgentNode({ id, telemetry, isSelected, showCollisionDebug, onSelect }) {
  const groupRef = useRef();
  const rotorsRef = useRef([]);

  // Per-frame spatial interpolation (Lerping) for smooth 60 FPS motion
  useFrame((_, delta) => {
    if (!groupRef.current || !telemetry) return;

    // Linear interpolation toward latest target coordinates
    const [tx, ty, tz] = telemetry.targetPos || [telemetry.x, telemetry.y, telemetry.z];
    groupRef.current.position.x = THREE.MathUtils.lerp(groupRef.current.position.x, tx, 0.25);
    groupRef.current.position.y = THREE.MathUtils.lerp(groupRef.current.position.y, ty, 0.25);
    groupRef.current.position.z = THREE.MathUtils.lerp(groupRef.current.position.z, tz, 0.25);

    // Smooth yaw rotation
    const currentRot = groupRef.current.rotation.y;
    groupRef.current.rotation.y = THREE.MathUtils.lerp(currentRot, telemetry.targetYaw || 0, 0.2);

    // Rotor spin animation
    rotorsRef.current.forEach((rotor) => {
      if (rotor) rotor.rotation.y += delta * 30;
    });
  });

  const isCollision = telemetry?.collision || false;
  const statusColor = isCollision ? '#ef4444' : isSelected ? '#00f0ff' : '#10b981';

  return (
    <group
      ref={groupRef}
      position={[telemetry.x, telemetry.y, telemetry.z]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(id);
      }}
    >
      {/* Airframe Fuselage */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[1.2, 0.25, 1.2]} />
        <meshStandardMaterial
          color={isCollision ? '#7f1d1d' : isSelected ? '#0284c7' : '#1e293b'}
          roughness={0.3}
          metalness={0.8}
        />
      </mesh>

      {/* Telemetry Indicator Beacon */}
      <mesh position={[0, 0.16, 0]}>
        <sphereGeometry args={[0.18, 16, 16]} />
        <meshStandardMaterial
          color={statusColor}
          emissive={statusColor}
          emissiveIntensity={isCollision ? 3.5 : 2.0}
        />
      </mesh>

      {/* Diagonal Arms */}
      {[
        [0.8, 0, 0.8, Math.PI / 4],
        [-0.8, 0, 0.8, -Math.PI / 4],
        [0.8, 0, -0.8, -Math.PI / 4],
        [-0.8, 0, -0.8, Math.PI / 4],
      ].map(([x, y, z, rot], idx) => (
        <group key={idx} position={[x * 0.5, y, z * 0.5]} rotation={[0, rot, 0]}>
          <mesh>
            <cylinderGeometry args={[0.04, 0.04, 1.2, 8]} />
            <meshStandardMaterial color="#475569" metalness={0.9} roughness={0.2} />
          </mesh>
        </group>
      ))}

      {/* 4 Rotors */}
      {[
        [0.8, 0.1, 0.8],
        [-0.8, 0.1, 0.8],
        [0.8, 0.1, -0.8],
        [-0.8, 0.1, -0.8],
      ].map(([x, y, z], idx) => (
        <group key={idx} position={[x, y, z]}>
          <mesh>
            <cylinderGeometry args={[0.12, 0.12, 0.18, 12]} />
            <meshStandardMaterial color="#0f172a" metalness={0.7} />
          </mesh>
          <mesh ref={(el) => (rotorsRef.current[idx] = el)} position={[0, 0.12, 0]}>
            <boxGeometry args={[0.9, 0.02, 0.1]} />
            <meshStandardMaterial color="#94a3b8" transparent opacity={0.75} roughness={0.5} />
          </mesh>
        </group>
      ))}

      {/* Collision Penalty Danger Volume */}
      {isCollision && showCollisionDebug && (
        <mesh>
          <sphereGeometry args={[2.0, 16, 16]} />
          <meshBasicMaterial color="#ef4444" wireframe transparent opacity={0.35} />
        </mesh>
      )}

      {/* Selection Halo */}
      {isSelected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.2, 0]}>
          <ringGeometry args={[1.5, 1.65, 32]} />
          <meshBasicMaterial color="#38bdf8" side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
}

export default function SwarmPipeline() {
  const drones = useSwarmStore((state) => state.drones);
  const selectedDroneId = useSwarmStore((state) => state.selectedDroneId);
  const showCollisionDebug = useSwarmStore((state) => state.showCollisionDebug);
  const setSelectedDroneId = useSwarmStore((state) => state.setSelectedDroneId);

  const droneEntries = Object.entries(drones);

  return (
    <group>
      {droneEntries.map(([id, telemetry]) => (
        <SwarmAgentNode
          key={id}
          id={id}
          telemetry={telemetry}
          isSelected={selectedDroneId === id}
          showCollisionDebug={showCollisionDebug}
          onSelect={setSelectedDroneId}
        />
      ))}
    </group>
  );
}