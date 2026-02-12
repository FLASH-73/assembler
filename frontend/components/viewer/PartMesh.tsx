"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Edges } from "@react-three/drei";
import type { Mesh } from "three";
import type { Part } from "@/lib/types";
import { GraspPoint } from "./GraspPoint";

type PartState = "ghost" | "active" | "complete" | "selected";

interface PartMeshProps {
  part: Part;
  state: PartState;
  exploded: boolean;
  onClick: () => void;
}

function PartGeometry({ geometry, dimensions }: { geometry: string; dimensions: number[] }) {
  switch (geometry) {
    case "cylinder":
      return <cylinderGeometry args={[dimensions[0], dimensions[0], dimensions[1], 32]} />;
    case "sphere":
      return <sphereGeometry args={[dimensions[0], 32, 32]} />;
    default:
      return <boxGeometry args={[dimensions[0], dimensions[1], dimensions[2]]} />;
  }
}

const GHOST_COLOR = "#D4D4D0";
const COMPLETE_COLOR = "#C8C8C4";
const ACCENT_COLOR = "#E05A1A";

export function PartMesh({ part, state, exploded, onClick }: PartMeshProps) {
  const meshRef = useRef<Mesh>(null);
  const pos = part.position ?? [0, 0, 0];
  const dims = part.dimensions ?? [0.05, 0.05, 0.05];

  // Explode offset: move parts up along Y
  const explodeOffset = exploded ? 0.06 : 0;
  const position: [number, number, number] = [
    pos[0],
    pos[1] + explodeOffset,
    pos[2],
  ];

  // Pulse animation for active state
  useFrame(({ clock }) => {
    if (meshRef.current && state === "active") {
      const mat = meshRef.current.material;
      if ("opacity" in mat) {
        (mat as { opacity: number }).opacity = 0.85 + 0.15 * Math.sin(clock.elapsedTime * Math.PI);
      }
    }
  });

  const isGhost = state === "ghost";
  const showEdges = state === "active" || state === "selected";
  const showGrasps = state === "selected";

  const color = isGhost
    ? GHOST_COLOR
    : state === "complete"
      ? COMPLETE_COLOR
      : (part.color ?? "#B0AEA8");

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        castShadow
      >
        <PartGeometry geometry={part.geometry ?? "box"} dimensions={dims} />
        <meshStandardMaterial
          color={color}
          roughness={0.6}
          metalness={0.1}
          transparent={isGhost || state === "active"}
          opacity={isGhost ? 0.12 : 1}
          wireframe={isGhost}
        />
        {showEdges && <Edges color={ACCENT_COLOR} linewidth={2} />}
      </mesh>

      {/* Grasp points */}
      {showGrasps &&
        part.graspPoints.map((gp, i) => (
          <GraspPoint key={i} position={[0, dims[1] ? dims[1] / 2 : 0.02, 0]} index={i} />
        ))}
    </group>
  );
}
