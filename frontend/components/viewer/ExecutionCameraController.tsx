"use client";

// Renderless R3F component — gently nudges OrbitControls target toward
// the active part during execution. Does not override user dragging.

import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { Vec3 } from "@/lib/animation";
import type { ExecutionAnimState } from "@/lib/executionAnimation";

interface ExecutionCameraControllerProps {
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  executionActive: boolean;
  executionAnimRef: React.RefObject<ExecutionAnimState>;
  assemblyCenter: Vec3;
}

const NUDGE_FACTOR = 0.02;

export function ExecutionCameraController({
  controlsRef,
  executionActive,
  executionAnimRef,
  assemblyCenter,
}: ExecutionCameraControllerProps) {
  const initialSetRef = useRef(false);

  // Set initial camera target on execution start
  useEffect(() => {
    if (!executionActive) {
      initialSetRef.current = false;
      return;
    }
    if (initialSetRef.current) return;
    initialSetRef.current = true;

    const controls = controlsRef.current;
    if (!controls) return;
    controls.target.set(assemblyCenter[0], assemblyCenter[1], assemblyCenter[2]);
    controls.update();
  }, [executionActive, controlsRef, assemblyCenter]);

  useFrame(() => {
    if (!executionActive) return;
    const controls = controlsRef.current;
    const state = executionAnimRef.current;
    if (!controls || !state) return;
    if (state.endEffectorPhase === "idle") return;

    const target = state.endEffectorTarget;
    const ct = controls.target;
    ct.x += (target[0] - ct.x) * NUDGE_FACTOR;
    ct.y += (target[1] - ct.y) * NUDGE_FACTOR;
    ct.z += (target[2] - ct.z) * NUDGE_FACTOR;
  });

  return null;
}
