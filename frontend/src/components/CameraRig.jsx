import React, { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';

export default function CameraRig() {
  const controlsRef = useRef();
  const { camera } = useThree();
  const { selectedDroneId, drones, cameraMode } = useSwarmStore();

  useEffect(() => {
    // Standard tactical isometric view
    camera.position.set(0, 45, 60);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  useFrame(() => {
    if (cameraMode === 'follow' && selectedDroneId && drones[selectedDroneId]) {
      const target = drones[selectedDroneId];
      const targetPos = new THREE.Vector3(target.x, target.y + 5, target.z + 10);
      camera.position.lerp(targetPos, 0.05);
      if (controlsRef.current) {
        controlsRef.current.target.lerp(new THREE.Vector3(target.x, target.y, target.z), 0.05);
      }
    }
  });

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping
      dampingFactor={0.05}
      minDistance={5}
      maxDistance={150}
      maxPolarAngle={Math.PI / 2.05}
    />
  );
}