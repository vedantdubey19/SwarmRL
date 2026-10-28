import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { mutableSimState, useSwarmStore } from '../store/useSwarmStore';

const MAX_DRONES = 100;
const linePositions = new Float32Array(MAX_DRONES * 8 * 2 * 3);
const lineColors = new Float32Array(MAX_DRONES * 8 * 2 * 3);

export default function DroneMesh() {
  const meshRef = useRef();
  const detectionLinesRef = useRef();
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colorActive = useMemo(() => new THREE.Color('#00f0ff'), []);
  const colorCollision = useMemo(() => new THREE.Color('#ef4444'), []);
  const colorOutOfBounds = useMemo(() => new THREE.Color('#f59e0b'), []);
  const colorSelected = useMemo(() => new THREE.Color('#a855f7'), []);

  const selectedDroneId = useSwarmStore((s) => s.selectedDroneId);

  useFrame(() => {
    if (!meshRef.current) return;

    const drones = mutableSimState.frameBuffer.getInterpolatedDrones();
    const count = Math.min(drones.length, MAX_DRONES);

    let lineVertexIdx = 0;

    for (let i = 0; i < count; i++) {
      const drone = drones[i];
      const pos = drone.interpolatedPosition || drone.position || [0, 0, 0];
      const rotY = drone.interpolatedRotationY ?? 0;

      dummy.position.set(pos[0], pos[1], pos[2]);
      dummy.rotation.set(0, rotY, 0);
      dummy.scale.set(1, 1, 1);
      dummy.updateMatrix();

      meshRef.current.setMatrixAt(i, dummy.matrix);

      // Color mapping
      let color = colorActive;
      const droneId = drone.id ?? i;
      if (droneId === selectedDroneId) {
        color = colorSelected;
      } else if (drone.status === 'collided_drone' || drone.status === 'collided_obstacle') {
        color = colorCollision;
      } else if (drone.status === 'out_of_bounds') {
        color = colorOutOfBounds;
      }

      meshRef.current.setColorAt(i, color);

      // Sensor detection lines
      if (drone.detections && Array.isArray(drone.detections)) {
        for (const det of drone.detections) {
          if (lineVertexIdx + 6 > linePositions.length) break;
          // Drone position
          linePositions[lineVertexIdx] = pos[0];
          linePositions[lineVertexIdx + 1] = pos[1];
          linePositions[lineVertexIdx + 2] = pos[2];

          // Compute detected endpoint from bearing_x, bearing_y, distance
          const dist = det.distance || 0;
          const globalAngle = rotY + (det.bearing_x || 0);
          const endX = pos[0] + Math.sin(globalAngle) * dist;
          const endY = Math.max(0, pos[1] + Math.sin(det.bearing_y || 0) * dist);
          const endZ = pos[2] + Math.cos(globalAngle) * dist;

          linePositions[lineVertexIdx + 3] = endX;
          linePositions[lineVertexIdx + 4] = endY;
          linePositions[lineVertexIdx + 5] = endZ;

          // Color detection: target (gold) vs obstacle (red)
          const isTarget = det.type === 'target';
          const r = isTarget ? 1.0 : 0.9;
          const g = isTarget ? 0.8 : 0.2;
          const b = isTarget ? 0.0 : 0.2;

          for (let c = 0; c < 2; c++) {
            lineColors[lineVertexIdx + c * 3] = r;
            lineColors[lineVertexIdx + c * 3 + 1] = g;
            lineColors[lineVertexIdx + c * 3 + 2] = b;
          }

          lineVertexIdx += 6;
        }
      }
    }

    // Hide remaining unused instances
    for (let i = count; i < MAX_DRONES; i++) {
      dummy.position.set(0, -9999, 0);
      dummy.scale.set(0, 0, 0);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }

    // Update detection lines
    if (detectionLinesRef.current) {
      const geo = detectionLinesRef.current.geometry;
      geo.attributes.position.needsUpdate = true;
      geo.attributes.color.needsUpdate = true;
      geo.setDrawRange(0, lineVertexIdx / 3);
    }
  });

  // Drone quadcopter shape geometry: central cylinder body + cross arms
  const droneGeometry = useMemo(() => {
    const groupGeo = new THREE.CylinderGeometry(0.5, 0.6, 0.2, 8);
    groupGeo.rotateY(Math.PI / 4);
    return groupGeo;
  }, []);

  return (
    <group>
      {/* Single InstancedMesh for all 50 drones */}
      <instancedMesh
        ref={meshRef}
        args={[droneGeometry, null, MAX_DRONES]}
        castShadow
        receiveShadow
      >
        <meshStandardMaterial
          roughness={0.3}
          metalness={0.7}
          toneMapped={false}
        />
      </instancedMesh>

      {/* Detection rays */}
      <lineSegments ref={detectionLinesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={linePositions.length / 3}
            array={linePositions}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-color"
            count={lineColors.length / 3}
            array={lineColors}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial
          vertexColors
          transparent
          opacity={0.6}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>
    </group>
  );
}
