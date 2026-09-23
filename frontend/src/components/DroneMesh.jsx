import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export default function DroneMesh({
  id,
  position = [0, 0, 0],
  heading = 0,
  isSelected = false,
  onSelect,
}) {
  const rotorsRef = useRef([]);

  // Spin rotor blades continuously on each animation frame
  useFrame((_, delta) => {
    rotorsRef.current.forEach((rotor) => {
      if (rotor) rotor.rotation.y += delta * 25;
    });
  });

  return (
    <group
      position={position}
      rotation={[0, -heading + Math.PI / 2, 0]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(id);
      }}
    >
      {/* Central Chassis / Fuselage */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[1.2, 0.25, 1.2]} />
        <meshStandardMaterial
          color={isSelected ? '#38bdf8' : '#1e293b'}
          roughness={0.3}
          metalness={0.8}
        />
      </mesh>

      {/* Center Status Glow LED */}
      <mesh position={[0, 0.15, 0]}>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial
          color={isSelected ? '#00f0ff' : '#10b981'}
          emissive={isSelected ? '#00f0ff' : '#10b981'}
          emissiveIntensity={2.5}
        />
      </mesh>

      {/* 4 Diagonal Carbon Fiber Motor Arms */}
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

      {/* 4 Motor Pods & Spinning Propellers */}
      {[
        [0.8, 0.1, 0.8],
        [-0.8, 0.1, 0.8],
        [0.8, 0.1, -0.8],
        [-0.8, 0.1, -0.8],
      ].map(([x, y, z], idx) => (
        <group key={idx} position={[x, y, z]}>
          {/* Motor Pod Mount */}
          <mesh>
            <cylinderGeometry args={[0.12, 0.12, 0.18, 12]} />
            <meshStandardMaterial color="#0f172a" metalness={0.7} />
          </mesh>
          {/* Rotor Blade */}
          <mesh
            ref={(el) => (rotorsRef.current[idx] = el)}
            position={[0, 0.12, 0]}
          >
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

      {/* Agent ID HUD Label Ring */}
      {isSelected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.2, 0]}>
          <ringGeometry args={[1.5, 1.65, 32]} />
          <meshBasicMaterial color="#38bdf8" side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
}