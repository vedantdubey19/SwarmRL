import React, { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { useSwarmStore, mutableSimState } from '../store/useSwarmStore';

export default function CameraRig() {
  const controlsRef = useRef();
  const { camera } = useThree();
  const selectedDroneId = useSwarmStore((s) => s.selectedDroneId);
  const setFps = useSwarmStore((s) => s.setFps);

  const fpsFrames = useRef(0);
  const fpsLastTime = useRef(0);

  useEffect(() => {
    fpsLastTime.current = performance.now();
    camera.position.set(0, 50, 70);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  useFrame(() => {
    // 1. Calculate rendering FPS
    fpsFrames.current++;
    const now = performance.now();
    if (now - fpsLastTime.current >= 1000) {
      const calculatedFps = Math.round((fpsFrames.current * 1000) / (now - fpsLastTime.current));
      setFps(calculatedFps);
      fpsFrames.current = 0;
      fpsLastTime.current = now;
    }

    // 2. Camera Tracking if a drone is selected
    if (selectedDroneId !== null) {
      const drones = mutableSimState.frameBuffer.getInterpolatedDrones();
      const drone = drones.find((d) => (d.id ?? d.agent_id) === selectedDroneId);
      if (drone && drone.interpolatedPosition) {
        const [x, y, z] = drone.interpolatedPosition;
        if (controlsRef.current) {
          controlsRef.current.target.lerp(new THREE.Vector3(x, y, z), 0.08);
        }
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
      maxDistance={180}
      maxPolarAngle={Math.PI / 2.02}
    />
  );
}
