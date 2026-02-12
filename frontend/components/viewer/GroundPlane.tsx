"use client";

import { Grid, ContactShadows } from "@react-three/drei";

export function GroundPlane() {
  return (
    <group>
      <Grid
        args={[2, 2]}
        cellSize={0.02}
        cellColor="#E8E7E4"
        sectionSize={0.1}
        sectionColor="#D4D3CF"
        fadeDistance={1}
        fadeStrength={1}
        infiniteGrid
        position={[0, -0.02, 0]}
      />
      <ContactShadows
        position={[0, -0.019, 0]}
        opacity={0.25}
        scale={0.5}
        blur={2}
        far={0.15}
      />
    </group>
  );
}
