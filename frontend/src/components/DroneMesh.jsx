import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';

export default function DroneMesh({
  id,
  position = [0, 0, 0],
  yaw = 0,
  collision = false,
  isSelected = false,
  onSelect,
}) {
  const rotorsRef = useRef([]);
  const showCollisionDebug = useSwarmStore((state) => state.showCollisionDebug);

  // Spin rotor blades continuously
  useFrame((_, delta) => {
    rotorsRef.current.forEach((rotor) => {
      if (rotor) rotor.rotation.y += delta * 28;
    });
  });

  const statusColor = collision ? '#ef4444' : isSelected ? '#00f0ff' : '#10b981';

  return (
    <group
      position={position}
      rotation={[0, yaw, 0]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(id);
      }}
    >
      {/* Central Chassis */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[1.2, 0.25, 1.2]} />
        <meshStandardMaterial
          color={collision ? '#7f1d1d' : isSelected ? '#0284c7' : '#1e293b'}
          roughness={0.3}
          metalness={0.8}
        />
      </mesh>

      {/* Center Status LED */}
      <mesh position={[0, 0.16, 0]}>
        <sphereGeometry args={[0.18, 16, 16]} />
        <meshStandardMaterial
          color={statusColor}
          emissive={statusColor}
          emissiveIntensity={collision ? 3.5 : 2.0}
        />
      </mesh>

      {/* Carbon Fiber Motor Arms */}
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

      {/* Motors & Blades */}
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
            <meshStandardMaterial
              color="#94a3b8"
              transparent
              opacity={0.75}
              roughness={0.5}
            />
          </mesh>
        </group>
      ))}

      {/* Collision Penalty Danger Sphere (2.0m radius debug volume) */}
      {collision && showCollisionDebug && (
        <mesh>
          <sphereGeometry args={[2.0, 16, 16]} />
          <meshBasicMaterial
            color="#ef4444"
            wireframe
            transparent
            opacity={0.4}
          />
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