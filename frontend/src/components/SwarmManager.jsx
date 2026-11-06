import React from 'react';
import DroneMesh from './DroneMesh';
import { useSwarmStore } from '../store/useSwarmStore';

export default function SwarmManager() {
  const drones = useSwarmStore((state) => state.drones);
  const selectedDroneId = useSwarmStore((state) => state.selectedDroneId);
  const setSelectedDroneId = useSwarmStore((state) => state.setSelectedDroneId);

  const droneList = Object.values(drones);

  return (
    <group>
      {droneList.map((drone) => (
        <DroneMesh
          key={drone.id}
          id={drone.id}
          position={[drone.x, drone.y, drone.z]}
          yaw={drone.yaw || 0}
          collision={Boolean(drone.collision)}
          isSelected={selectedDroneId === drone.id}
          onSelect={setSelectedDroneId}
        />
      ))}
    </group>
  );
}