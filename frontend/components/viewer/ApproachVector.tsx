"use client";

import { Line, Cone } from "@react-three/drei";

interface ApproachVectorProps {
  origin: [number, number, number];
  direction: [number, number, number];
  length: number;
}

export function ApproachVector({ origin, direction, length }: ApproachVectorProps) {
  const end: [number, number, number] = [
    origin[0] + direction[0] * length,
    origin[1] + direction[1] * length,
    origin[2] + direction[2] * length,
  ];

  // Cone tip sits at the end of the line
  const conePos: [number, number, number] = [
    end[0] + direction[0] * 0.004,
    end[1] + direction[1] * 0.004,
    end[2] + direction[2] * 0.004,
  ];

  // Calculate rotation so cone points along direction
  // Default cone points up (0,1,0). We need to rotate from (0,1,0) to direction.
  const coneRotation: [number, number, number] = [
    direction[2] > 0 ? Math.PI / 2 : direction[2] < 0 ? -Math.PI / 2 : 0,
    0,
    direction[0] !== 0 ? -Math.atan2(direction[0], direction[1]) : 0,
  ];

  return (
    <group>
      <Line
        points={[origin, end]}
        color="#9C9C97"
        lineWidth={1}
        transparent
        opacity={0.6}
      />
      <Cone
        args={[0.003, 0.008, 8]}
        position={conePos}
        rotation={coneRotation}
      >
        <meshBasicMaterial color="#9C9C97" transparent opacity={0.6} />
      </Cone>
    </group>
  );
}
