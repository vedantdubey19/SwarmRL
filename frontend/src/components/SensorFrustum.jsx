import React, { useMemo } from 'react';
import * as THREE from 'three';

export default function SensorFrustum({
  sensorRange = 6.5,
  fovAngleRad = Math.PI / 3.5,
  isActive = true,
  isAlert = false,
}) {
  const { geometry, edgesGeometry } = useMemo(() => {
    const radius = Math.tan(fovAngleRad / 2) * sensorRange;
    const coneGeo = new THREE.ConeGeometry(radius, sensorRange, 24, 1, true);

    coneGeo.rotateX(Math.PI);
    coneGeo.translate(0, -sensorRange / 2, 0);

    const edges = new THREE.EdgesGeometry(coneGeo, 25);
    return { geometry: coneGeo, edgesGeometry: edges };
  }, [sensorRange, fovAngleRad]);

  const coneColor = isAlert ? '#ef4444' : '#0284c7';
  const groundRingRadius = Math.tan(fovAngleRad / 2) * sensorRange;

  if (!isActive) return null;

  return (
    <group>
      <mesh geometry={geometry}>
        <meshBasicMaterial
          color={coneColor}
          transparent
          opacity={isAlert ? 0.25 : 0.08}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      <lineSegments geometry={edgesGeometry}>
        <lineBasicMaterial
          color={isAlert ? '#f87171' : '#38bdf8'}
          transparent
          opacity={isAlert ? 0.7 : 0.3}
        />
      </lineSegments>

      <mesh position={[0, -sensorRange, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[groundRingRadius * 0.92, groundRingRadius, 32]} />
        <meshBasicMaterial
          color={isAlert ? '#ef4444' : '#38bdf8'}
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}