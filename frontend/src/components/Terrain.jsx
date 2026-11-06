import React, { useMemo } from 'react';
import * as THREE from 'three';

export default function Terrain({ size = 120, segments = 64 }) {
  const { geometry } = useMemo(() => {
    const geo = new THREE.PlaneGeometry(size, size, segments, segments);
    geo.rotateX(-Math.PI / 2);

    const pos = geo.attributes.position;
    const colors = [];
    const colorBottom = new THREE.Color('#0f172a'); // Valleys
    const colorMid = new THREE.Color('#1e293b');    // Plateaus
    const colorTop = new THREE.Color('#0369a1');    // Peaks

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);

      const y =
        Math.sin(x * 0.08) * Math.cos(z * 0.08) * 3.5 +
        Math.sin(x * 0.03 + 1.2) * Math.cos(z * 0.03 + 0.8) * 4.0;

      pos.setY(i, y);

      const normalizedY = (y + 7.5) / 15.0;
      const vertexColor = new THREE.Color();
      if (normalizedY < 0.5) {
        vertexColor.lerpColors(colorBottom, colorMid, normalizedY * 2);
      } else {
        vertexColor.lerpColors(colorMid, colorTop, (normalizedY - 0.5) * 2);
      }

      colors.push(vertexColor.r, vertexColor.g, vertexColor.b);
    }

    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return { geometry: geo };
  }, [size, segments]);

  return (
    <group>
      <mesh geometry={geometry} receiveShadow>
        <meshStandardMaterial
          vertexColors
          roughness={0.8}
          metalness={0.1}
          flatShading
        />
      </mesh>
      <mesh geometry={geometry} position={[0, 0.02, 0]}>
        <meshBasicMaterial
          color="#38bdf8"
          wireframe
          transparent
          opacity={0.08}
        />
      </mesh>
    </group>
  );
}