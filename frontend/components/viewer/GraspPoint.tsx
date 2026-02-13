"use client";

import { useState } from "react";
import { Sphere, Html } from "@react-three/drei";

interface GraspPointProps {
  position: [number, number, number];
  index: number;
}

export function GraspPoint({ position, index }: GraspPointProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <group position={position}>
      <Sphere
        args={[0.003, 16, 16]}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <meshBasicMaterial color="#2563EB" transparent opacity={0.8} />
      </Sphere>

      {hovered && (
        <Html center distanceFactor={0.15}>
          <div className="whitespace-nowrap rounded bg-text-primary px-2 py-1 text-[11px] font-medium text-white shadow-sm">
            Grasp {index}
          </div>
        </Html>
      )}
    </group>
  );
}
