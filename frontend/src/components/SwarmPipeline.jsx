import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';
import { globalSyncBuffer } from '../utils/syncBuffer';

function SynchronizedAgentNode({ id, isSelected, showCollisionDebug, onSelect }) {
  const groupRef = useRef();
  const rotorsRef = useRef([]);

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    // 1. Fetch smoothed interpolated coordinates from the sync buffer
    const syncedState = globalSyncBuffer.getInterpolatedState(id);
    if (syncedState) {
      groupRef.current.position.x = syncedState.x;
      groupRef.current.position.y = syncedState.y;
      groupRef.current.position.z = syncedState.z;
      groupRef.current.rotation.y = syncedState.yaw;
    }

    // 2. Spin rotors continuously
    rotorsRef.current.forEach((rotor) => {
      if (rotor) rotor.rotation.y += delta * 30;
    });
  });

  const droneData = useSwarmStore((state) => state.drones[id]);
  const isCollision = droneData?.collision || false;
  const statusColor = isCollision ? '#ef4444' : isSelected ? '#00f0ff' : '#10b981';

  return (
    <group
      ref={groupRef}
      position={[droneData?.x || 0, droneData?.y || 0, droneData?.z || 0]}
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

      {/* Telemetry Status Indicator */}
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

      {/* Collision Volume */}
      {isCollision && showCollisionDebug && (
        <mesh>
          <sphereGeometry args={[2.0, 16, 16]} />
          <meshBasicMaterial color="#ef4444" wireframe transparent opacity={0.35} />
        </mesh>
      )}

      {/* Selection Target Ring */}
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

  const droneKeys = Object.keys(drones);

  return (
    <group>
      {droneKeys.map((id) => (
        <SynchronizedAgentNode
          key={id}
          id={id}
          isSelected={selectedDroneId === id}
          showCollisionDebug={showCollisionDebug}
          onSelect={setSelectedDroneId}
        />
      ))}
    </group>
  );
}