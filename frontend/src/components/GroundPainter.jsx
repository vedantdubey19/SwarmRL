import React, { useMemo } from 'react';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';

const GRID_SIZE = 60;
const CELL_WORLD_SIZE = 2.0;
const HALF_BOUNDS = 60;

// Procedural elevation math matching Terrain.jsx
const getElevation = (x, z) =>
  Math.sin(x * 0.08) * Math.cos(z * 0.08) * 3.5 +
  Math.sin(x * 0.03 + 1.2) * Math.cos(z * 0.03 + 0.8) * 4.0;

export default function GroundPainter() {
  const showGroundPainting = useSwarmStore((state) => state.showGroundPainting);
  const exploredCells = useSwarmStore((state) => state.exploredCells);

  const cellCoordinates = useMemo(() => {
    const coords = [];
    exploredCells.forEach((key) => {
      const [cx, cz] = key.split('_').map(Number);
      const worldX = cx * CELL_WORLD_SIZE - HALF_BOUNDS + CELL_WORLD_SIZE / 2;
      const worldZ = cz * CELL_WORLD_SIZE - HALF_BOUNDS + CELL_WORLD_SIZE / 2;
      const worldY = getElevation(worldX, worldZ) + 0.08; // Slight Y-offset above terrain to prevent z-fighting
      coords.push([worldX, worldY, worldZ]);
    });
    return coords;
  }, [exploredCells]);

  if (!showGroundPainting || cellCoordinates.length === 0) return null;

  return (
    <group>
      {cellCoordinates.map(([x, y, z], idx) => (
        <mesh key={idx} position={[x, y, z]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[CELL_WORLD_SIZE * 0.95, CELL_WORLD_SIZE * 0.95]} />
          <meshBasicMaterial
            color="#0ea5e9"
            transparent
            opacity={0.35}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  );
}