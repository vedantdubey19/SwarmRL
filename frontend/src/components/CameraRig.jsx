import React, { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { useSwarmStore } from '../store/useSwarmStore';
import { globalSyncBuffer } from '../utils/syncBuffer';

export default function CameraRig() {
  const controlsRef = useRef();
  const { camera } = useThree();
  const { selectedDroneId, cameraMode, setRenderFps } = useSwarmStore();

  const fpsFrames = useRef(0);
  const fpsLastTime = useRef(performance.now());

  useEffect(() => {
    camera.position.set(0, 45, 65);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  useFrame(() => {
    // 1. Calculate rendering FPS
    fpsFrames.current++;
    const now = performance.now();
    if (now - fpsLastTime.current >= 1000) {
      const calculatedFps = Math.round((fpsFrames.current * 1000) / (now - fpsLastTime.current));
      setRenderFps(calculatedFps);
      fpsFrames.current = 0;
      fpsLastTime.current = now;
    }

    // 2. Camera Tracking in Follow Mode
    if (cameraMode === 'follow' && selectedDroneId) {
      const agentState = globalSyncBuffer.getInterpolatedState(selectedDroneId);
      if (agentState) {
        const targetPos = new THREE.Vector3(agentState.x, agentState.y + 6, agentState.z + 12);
        camera.position.lerp(targetPos, 0.08);
        if (controlsRef.current) {
          controlsRef.current.target.lerp(
            new THREE.Vector3(agentState.x, agentState.y, agentState.z),
            0.08
          );
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
      maxDistance={150}
      maxPolarAngle={Math.PI / 2.05}
    />
  );
}