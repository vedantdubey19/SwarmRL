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

  useFrame((_, delta) => {
    // Profiler
    fpsFrames.current++;
    const now = performance.now();
    if (now - fpsLastTime.current >= 1000) {
      setRenderFps(Math.round((fpsFrames.current * 1000) / (now - fpsLastTime.current)));
      fpsFrames.current = 0;
      fpsLastTime.current = now;
    }

    // Follow Mode
    if (cameraMode === 'follow' && selectedDroneId) {
      const agentState = globalSyncBuffer.getInterpolatedState(selectedDroneId);
      if (agentState) {
        const distance = 10;
        const elevation = 5;

        const camX = agentState.x - Math.sin(agentState.yaw) * distance;
        const camY = agentState.y + elevation;
        const camZ = agentState.z - Math.cos(agentState.yaw) * distance;

        const targetCamPos = new THREE.Vector3(camX, camY, camZ);
        const lookTarget = new THREE.Vector3(agentState.x, agentState.y + 1, agentState.z);

        const damp = 1.0 - Math.exp(-8 * delta);
        camera.position.lerp(targetCamPos, damp);

        if (controlsRef.current) {
          controlsRef.current.target.lerp(lookTarget, damp);
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
      minDistance={3}
      maxDistance={160}
      maxPolarAngle={Math.PI / 2.05}
    />
  );
}