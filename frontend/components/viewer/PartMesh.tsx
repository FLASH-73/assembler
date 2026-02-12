"use client";

import { Suspense, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Edges, useGLTF } from "@react-three/drei";
import type { Group, MeshStandardMaterial } from "three";
import type { Part } from "@/lib/types";
import type { PartRenderState } from "@/lib/animation";
import { GraspPoint } from "./GraspPoint";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GHOST_COLOR = "#D4D4D0";
const COMPLETE_COLOR = "#C8C8C4";
const ACCENT_COLOR = "#E05A1A";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PlaceholderGeometry({ geometry, dimensions }: { geometry: string; dimensions: number[] }) {
  switch (geometry) {
    case "cylinder":
      return <cylinderGeometry args={[dimensions[0], dimensions[0], dimensions[1], 32]} />;
    case "sphere":
      return <sphereGeometry args={[dimensions[0], 32, 32]} />;
    default:
      return <boxGeometry args={[dimensions[0], dimensions[1], dimensions[2]]} />;
  }
}

function GlbMesh({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene.clone()} />;
}

// ---------------------------------------------------------------------------
// PartMesh
// ---------------------------------------------------------------------------

interface PartMeshProps {
  part: Part;
  renderStatesRef: React.RefObject<Record<string, PartRenderState>>;
  selectedStepId: string | null;
  firstStepIdForPart: string | null;
  wireframeOverlay: boolean;
  onClick: () => void;
}

export function PartMesh({
  part,
  renderStatesRef,
  selectedStepId,
  firstStepIdForPart,
  wireframeOverlay,
  onClick,
}: PartMeshProps) {
  const groupRef = useRef<Group>(null);
  const matRef = useRef<MeshStandardMaterial>(null);
  const dims = part.dimensions ?? [0.05, 0.05, 0.05];

  // Track visual state for conditional rendering (edges, grasps)
  const visualRef = useRef<"ghost" | "active" | "complete">("complete");

  useFrame(({ clock }) => {
    const rs = renderStatesRef.current?.[part.id];
    if (!groupRef.current || !matRef.current || !rs) return;

    // Position
    groupRef.current.position.set(rs.position[0], rs.position[1], rs.position[2]);

    // Determine effective state — selection overrides animation
    const isSelected = selectedStepId != null && selectedStepId === firstStepIdForPart;
    const effectiveState = isSelected ? "active" : rs.visualState;
    visualRef.current = effectiveState;

    // Opacity — pulse for active
    const isGhost = effectiveState === "ghost";
    let opacity = rs.opacity;
    if (effectiveState === "active") {
      opacity = 0.85 + 0.15 * Math.sin(clock.elapsedTime * Math.PI);
    } else if (isGhost) {
      opacity = Math.min(opacity, 0.12);
    }

    matRef.current.opacity = opacity;
    matRef.current.transparent = isGhost || effectiveState === "active" || opacity < 1;
    matRef.current.wireframe = isGhost || wireframeOverlay;

    // Color
    if (isGhost) {
      matRef.current.color.set(GHOST_COLOR);
    } else if (effectiveState === "complete" && !isSelected) {
      matRef.current.color.set(COMPLETE_COLOR);
    } else {
      matRef.current.color.set(part.color ?? "#B0AEA8");
    }
  });

  const showEdges = visualRef.current === "active";
  const isSelected = selectedStepId != null && selectedStepId === firstStepIdForPart;
  const showGrasps = isSelected;

  return (
    <group ref={groupRef}>
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        castShadow
      >
        {part.meshFile ? (
          <Suspense fallback={<PlaceholderGeometry geometry={part.geometry ?? "box"} dimensions={dims} />}>
            <GlbMesh url={part.meshFile} />
          </Suspense>
        ) : (
          <PlaceholderGeometry geometry={part.geometry ?? "box"} dimensions={dims} />
        )}
        <meshStandardMaterial
          ref={matRef}
          color={part.color ?? "#B0AEA8"}
          roughness={0.6}
          metalness={0.1}
          transparent
          opacity={1}
        />
        {(showEdges || isSelected) && <Edges color={ACCENT_COLOR} linewidth={2} />}
      </mesh>

      {showGrasps &&
        part.graspPoints.map((_, i) => (
          <GraspPoint key={i} position={[0, dims[1] ? dims[1] / 2 : 0.02, 0]} index={i} />
        ))}
    </group>
  );
}
