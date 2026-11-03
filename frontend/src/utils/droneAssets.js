import * as THREE from 'three';

// Shared Geometries
export const CHASSIS_GEOMETRY = new THREE.BoxGeometry(1.2, 0.25, 1.2);
export const LED_GEOMETRY = new THREE.SphereGeometry(0.18, 12, 12);
export const ARM_GEOMETRY = new THREE.CylinderGeometry(0.04, 0.04, 1.2, 6);
export const MOTOR_GEOMETRY = new THREE.CylinderGeometry(0.12, 0.12, 0.18, 8);
export const BLADE_GEOMETRY = new THREE.BoxGeometry(0.9, 0.02, 0.1);
export const DANGER_GEOMETRY = new THREE.SphereGeometry(2.0, 12, 12);
export const SELECTION_RING_GEOMETRY = new THREE.RingGeometry(1.5, 1.65, 24);

// Shared Static Materials
export const CHASSIS_MATERIAL_NORMAL = new THREE.MeshStandardMaterial({
  color: '#1e293b',
  roughness: 0.3,
  metalness: 0.8,
});

export const CHASSIS_MATERIAL_SELECTED = new THREE.MeshStandardMaterial({
  color: '#0284c7',
  roughness: 0.3,
  metalness: 0.8,
});

export const CHASSIS_MATERIAL_COLLISION = new THREE.MeshStandardMaterial({
  color: '#7f1d1d',
  roughness: 0.3,
  metalness: 0.8,
});

export const ARM_MATERIAL = new THREE.MeshStandardMaterial({
  color: '#475569',
  metalness: 0.9,
  roughness: 0.2,
});

export const MOTOR_MATERIAL = new THREE.MeshStandardMaterial({
  color: '#0f172a',
  metalness: 0.7,
});

export const BLADE_MATERIAL = new THREE.MeshStandardMaterial({
  color: '#94a3b8',
  transparent: true,
  opacity: 0.75,
  roughness: 0.5,
});

export const DANGER_MATERIAL = new THREE.MeshBasicMaterial({
  color: '#ef4444',
  wireframe: true,
  transparent: true,
  opacity: 0.35,
});

export const SELECTION_MATERIAL = new THREE.MeshBasicMaterial({
  color: '#38bdf8',
  side: THREE.DoubleSide,
});