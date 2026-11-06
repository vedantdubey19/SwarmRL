import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';
import { globalSyncBuffer } from '../utils/syncBuffer';
import DroneMesh from './DroneMesh';

function SynchronizedAgentNode({ id, isSelected, onSelect }) {
  const groupRef = useRef();
  const droneData = useSwarmStore((state) => state.drones[id]);

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    const syncedState = globalSyncBuffer.getInterpolatedState(id);
    if (syncedState) {
      const damp = 1.0 - Math.exp(-25 * delta);

      groupRef.current.position.x = THREE.MathUtils.lerp(
        groupRef.current.position.x,
        syncedState.x,
        damp
      );
      groupRef.current.position.y = THREE.MathUtils.lerp(
        groupRef.current.position.y,
        syncedState.y,
        damp
      );
      groupRef.current.position.z = THREE.MathUtils.lerp(
        groupRef.current.position.z,
        syncedState.z,
        damp
      );

      groupRef.current.rotation.y = THREE.MathUtils.lerpAngle(
        groupRef.current.rotation.y,
        syncedState.yaw,
        damp
      );
    }
  });

  return (
    <group
      ref={groupRef}
      position={[droneData?.x || 0, droneData?.y || 0, droneData?.z || 0]}
    >
      <DroneMesh
        id={id}
        position={[0, 0, 0]}
        yaw={0}
        collision={Boolean(droneData?.collision)}
        isSelected={isSelected}
        onSelect={onSelect}
      />
    </group>
  );
}

export default function SwarmPipeline() {
  const drones = useSwarmStore((state) => state.drones);
  const selectedDroneId = useSwarmStore((state) => state.selectedDroneId);
  const setSelectedDroneId = useSwarmStore((state) => state.setSelectedDroneId);

  const droneKeys = Object.keys(drones);

  return (
    <group>
      {droneKeys.map((id) => (
        <SynchronizedAgentNode
          key={id}
          id={id}
          isSelected={selectedDroneId === id}
          onSelect={setSelectedDroneId}
        />
      ))}
    </group>
  );
}