import React, { useRef, useMemo, useEffect } from 'react';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';

const GRID_SIZE = 60;
const CELL_WORLD_SIZE = 2.0;
const HALF_BOUNDS = 60;

const getElevation = (x, z) =>
  Math.sin(x * 0.08) * Math.cos(z * 0.08) * 3.5 +
  Math.sin(x * 0.03 + 1.2) * Math.cos(z * 0.03 + 0.8) * 4.0;

export default function ExploredAreaMesh() {
  const meshRef = useRef();
  const showGroundPainting = useSwarmStore((state) => state.showGroundPainting);
  const exploredCells = useSwarmStore((state) => state.exploredCells);

  const cellPositions = useMemo(() => {
    const list = [];
    exploredCells.forEach((key) => {
      const [cx, cz] = key.split('_').map(Number);
      const wx = cx * CELL_WORLD_SIZE - HALF_BOUNDS + CELL_WORLD_SIZE / 2;
      const wz = cz * CELL_WORLD_SIZE - HALF_BOUNDS + CELL_WORLD_SIZE / 2;
      const wy = getElevation(wx, wz) + 0.08;
      list.push([wx, wy, wz]);
    });
    return list;
  }, [exploredCells]);

  const maxInstances = GRID_SIZE * GRID_SIZE;
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useEffect(() => {
    if (!meshRef.current) return;
    const count = cellPositions.length;
    meshRef.current.count = count;

    for (let i = 0; i < count; i++) {
      const [x, y, z] = cellPositions[i];
      dummy.position.set(x, y, z);
      dummy.rotation.x = -Math.PI / 2;
      dummy.scale.set(CELL_WORLD_SIZE * 0.95, CELL_WORLD_SIZE * 0.95, 1);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [cellPositions, dummy]);

  if (!showGroundPainting) return null;

  return (
    <instancedMesh
      ref={meshRef}
      args={[null, null, maxInstances]}
      frustumCulled={false}
    >
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial
        color="#0284c7"
        transparent
        opacity={0.3}
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </instancedMesh>
  );
}