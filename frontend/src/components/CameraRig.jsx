import React, { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';

export default function CameraRig() {
  const controlsRef = useRef();
  const { camera } = useThree();
  const selectedDroneId = useSwarmStore((s) => s.selectedDroneId);
  const cameraMode = useSwarmStore((s) => s.cameraMode);
  const followOffset = useRef(new THREE.Vector3(0, 5, 10));
  const followPos = useRef(new THREE.Vector3());

  useEffect(() => {
    // Standard tactical isometric view
    camera.position.set(0, 45, 60);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  useFrame(() => {
    if (cameraMode !== 'follow' || !selectedDroneId) return;
    const entry = useSwarmStore.getState().getDroneTelemetry(selectedDroneId);
    if (!entry) return;

    followPos.current.copy(entry.currentPos).add(followOffset.current);
    camera.position.lerp(followPos.current, 0.05);
    if (controlsRef.current) {
      controlsRef.current.target.lerp(entry.currentPos, 0.05);
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