import React, { useMemo } from 'react';
import * as THREE from 'three';

export default function Terrain({ size = 120, segments = 64 }) {
  // Generate procedural height elevations
  const { geometry, colors } = useMemo(() => {
    const geo = new THREE.PlaneGeometry(size, size, segments, segments);
    geo.rotateX(-Math.PI / 2); // Lay flat on the XZ plane

    const pos = geo.attributes.position;
    const colorArray = new Float32Array(pos.count * 3);

    // Color definitions based on elevation
    const colorLow = new THREE.Color('#0f172a');     // Deep valley navy
    const colorMid = new THREE.Color('#1e293b');     // Mid ground slate
    const colorHigh = new THREE.Color('#0369a1');    // Mountain peak electric sky

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);

      // Procedural multi-frequency elevation formula
      const elevation =
        Math.sin(x * 0.08) * Math.cos(z * 0.08) * 3.5 +
        Math.sin(x * 0.03 + 1.2) * Math.cos(z * 0.03 + 0.8) * 4.0;

      pos.setY(i, elevation);

      // Height-based gradient interpolation
      const normalizedHeight = (elevation + 6) / 12; // Normalize roughly 0 to 1
      const vertexColor = new THREE.Color();

      if (normalizedHeight < 0.5) {
        vertexColor.lerpColors(colorLow, colorMid, normalizedHeight * 2);
      } else {
        vertexColor.lerpColors(colorMid, colorHigh, (normalizedHeight - 0.5) * 2);
      }

      colorArray[i * 3] = vertexColor.r;
      colorArray[i * 3 + 1] = vertexColor.g;
      colorArray[i * 3 + 2] = vertexColor.b;
    }

    geo.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));
    geo.computeVertexNormals();

    return { geometry: geo, colors: colorArray };
  }, [size, segments]);

  return (
    <group position={[0, -0.5, 0]}>
      {/* Shaded topographical surface */}
      <mesh geometry={geometry} receiveShadow>
        <meshStandardMaterial
          vertexColors
          roughness={0.8}
          metalness={0.2}
          wireframe={false}
        />
      </mesh>

      {/* Wireframe contour overlay for tactical search-and-rescue radar aesthetic */}
      <mesh geometry={geometry} position={[0, 0.02, 0]}>
        <meshBasicMaterial
          color="#38bdf8"
          wireframe
          transparent
          opacity={0.12}
        />
      </mesh>
    </group>
  );
}