import React, { useEffect } from 'react';
import DroneMesh from './DroneMesh';
import { useSwarmStore } from '../store/useSwarmStore';

export default function SwarmManager() {
  const { drones, selectedDroneId, setSelectedDroneId, updateDroneBatch } = useSwarmStore();

  // Populate sample drones on Day 03 to verify mesh positioning
  useEffect(() => {
    const initialSwarm = [
      { id: 'drone-01', x: -8, y: 4, z: -5, timestamp: Date.now() },
      { id: 'drone-02', x: 0, y: 6, z: 0, timestamp: Date.now() },
      { id: 'drone-03', x: 8, y: 5, z: 6, timestamp: Date.now() },
      { id: 'drone-04', x: -6, y: 7, z: 8, timestamp: Date.now() },
      { id: 'drone-05', x: 7, y: 3, z: -7, timestamp: Date.now() },
    ];
    updateDroneBatch(initialSwarm);
  }, [updateDroneBatch]);

  return (
    <group>
      {Object.values(drones).map((drone) => (
        <DroneMesh
          key={drone.id}
          id={drone.id}
          position={[drone.x, drone.y, drone.z]}
          isSelected={selectedDroneId === drone.id}
          onSelect={setSelectedDroneId}
        />
      ))}
    </group>
  );
}