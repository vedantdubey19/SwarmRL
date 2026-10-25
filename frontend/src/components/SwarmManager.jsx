import React from 'react';
import DroneMesh from './DroneMesh';
import { useSwarmStore } from '../store/useSwarmStore';

export default function SwarmManager() {
  const droneIds = useSwarmStore((state) => state.droneIds);
  const selectedDroneId = useSwarmStore((state) => state.selectedDroneId);
  const setSelectedDroneId = useSwarmStore((state) => state.setSelectedDroneId);

  return (
    <group>
      {droneIds.map((id) => (
        <DroneMesh
          key={id}
          id={id}
          isSelected={selectedDroneId === id}
          onSelect={setSelectedDroneId}
        />
      ))}
    </group>
  );
}