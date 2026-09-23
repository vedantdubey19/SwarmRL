import React from 'react';
import DroneMesh from './DroneMesh';
import { useSwarmStore } from '../store/useSwarmStore';

export default function SwarmManager() {
  const { drones, selectedDroneId, setSelectedDroneId } = useSwarmStore();

  return (
    <group>
      {Object.values(drones).map((drone) => {
        const position = Array.isArray(drone.pos)
          ? drone.pos
          : [drone.x || 0, drone.y || 0, drone.z || 0];
        const heading = typeof drone.heading === 'number' ? drone.heading : 0;

        return (
          <DroneMesh
            key={drone.id}
            id={drone.id}
            position={position}
            heading={heading}
            isSelected={selectedDroneId === drone.id}
            onSelect={setSelectedDroneId}
          />
        );
      })}
    </group>
  );
}