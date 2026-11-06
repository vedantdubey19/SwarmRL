import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';
import SensorFrustum from './SensorFrustum';
import {
  CHASSIS_GEOMETRY,
  LED_GEOMETRY,
  ARM_GEOMETRY,
  MOTOR_GEOMETRY,
  BLADE_GEOMETRY,
  DANGER_GEOMETRY,
  SELECTION_RING_GEOMETRY,
  CHASSIS_MATERIAL_NORMAL,
  CHASSIS_MATERIAL_SELECTED,
  CHASSIS_MATERIAL_COLLISION,
  ARM_MATERIAL,
  MOTOR_MATERIAL,
  BLADE_MATERIAL,
  DANGER_MATERIAL,
  SELECTION_MATERIAL,
} from '../utils/droneAssets';

const ARM_OFFSETS = [
  [0.8, 0, 0.8, Math.PI / 4],
  [-0.8, 0, 0.8, -Math.PI / 4],
  [0.8, 0, -0.8, -Math.PI / 4],
  [-0.8, 0, -0.8, Math.PI / 4],
];

const MOTOR_OFFSETS = [
  [0.8, 0.1, 0.8],
  [-0.8, 0.1, 0.8],
  [0.8, 0.1, -0.8],
  [-0.8, 0.1, -0.8],
];

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
  const showSensorCones = useSwarmStore((state) => state.showSensorCones);

  useFrame((_, delta) => {
    const rotationDelta = delta * 32;
    for (let i = 0; i < 4; i++) {
      if (rotorsRef.current[i]) {
        rotorsRef.current[i].rotation.y += rotationDelta;
      }
    }
  });

  const chassisMaterial = collision
    ? CHASSIS_MATERIAL_COLLISION
    : isSelected
    ? CHASSIS_MATERIAL_SELECTED
    : CHASSIS_MATERIAL_NORMAL;

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
      <mesh
        castShadow
        receiveShadow
        geometry={CHASSIS_GEOMETRY}
        material={chassisMaterial}
      />

      <mesh position={[0, 0.16, 0]} geometry={LED_GEOMETRY}>
        <meshStandardMaterial
          color={statusColor}
          emissive={statusColor}
          emissiveIntensity={collision ? 3.5 : 2.0}
        />
      </mesh>

      {ARM_OFFSETS.map(([x, y, z, rot], idx) => (
        <group key={idx} position={[x * 0.5, y, z * 0.5]} rotation={[0, rot, 0]}>
          <mesh geometry={ARM_GEOMETRY} material={ARM_MATERIAL} />
        </group>
      ))}

      {MOTOR_OFFSETS.map(([x, y, z], idx) => (
        <group key={idx} position={[x, y, z]}>
          <mesh geometry={MOTOR_GEOMETRY} material={MOTOR_MATERIAL} />
          <mesh
            ref={(el) => (rotorsRef.current[idx] = el)}
            position={[0, 0.12, 0]}
            geometry={BLADE_GEOMETRY}
            material={BLADE_MATERIAL}
          />
        </group>
      ))}

      <SensorFrustum
        sensorRange={6.5}
        fovAngleRad={Math.PI / 3.5}
        isActive={showSensorCones}
        isAlert={collision}
      />

      {collision && showCollisionDebug && (
        <mesh geometry={DANGER_GEOMETRY} material={DANGER_MATERIAL} />
      )}

      {isSelected && (
        <mesh
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, -0.2, 0]}
          geometry={SELECTION_RING_GEOMETRY}
          material={SELECTION_MATERIAL}
        />
      )}
    </group>
  );
}