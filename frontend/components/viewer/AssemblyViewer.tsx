"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { useAssembly } from "@/context/AssemblyContext";
import { useExecution } from "@/context/ExecutionContext";
import { partStepIndex } from "@/lib/animation";
import { useAnimationControls } from "@/lib/useAnimationControls";
import { GroundPlane } from "./GroundPlane";
import { PartMesh } from "./PartMesh";
import { ApproachVector } from "./ApproachVector";
import { AnimationController } from "./AnimationController";
import { ViewerControls } from "./ViewerControls";
import { AnimationTimeline } from "./AnimationTimeline";

export function AssemblyViewer() {
  const { assembly, selectedStepId, selectStep } = useAssembly();
  const { executionState } = useExecution();
  const controlsRef = useRef<OrbitControlsImpl>(null);

  const [exploded, setExploded] = useState(false);
  const [wireframe, setWireframe] = useState(false);

  const parts = useMemo(() => (assembly ? Object.values(assembly.parts) : []), [assembly]);
  const stepOrder = assembly?.stepOrder ?? [];
  const steps = assembly?.steps ?? {};
  const totalSteps = stepOrder.length;

  const anim = useAnimationControls(assembly?.id, totalSteps);

  // Pre-compute part → first step id mapping
  const partToStepId = useMemo(() => {
    const map: Record<string, string | null> = {};
    if (!assembly) return map;
    for (const part of parts) {
      const idx = partStepIndex(part.id, assembly.stepOrder, assembly.steps);
      map[part.id] = idx >= 0 ? (assembly.stepOrder[idx] ?? null) : null;
    }
    return map;
  }, [assembly, parts]);

  // Force idle during live execution
  useEffect(() => {
    if (executionState.phase === "running" || executionState.phase === "paused") {
      anim.forceIdle();
    }
  }, [executionState.phase, anim]);

  const handlePartClick = useCallback(
    (partId: string) => {
      if (!assembly) return;
      const stepId = assembly.stepOrder.find((sid) => assembly.steps[sid]?.partIds.includes(partId));
      selectStep(stepId ?? null);
    },
    [assembly, selectStep],
  );

  return (
    <div className="relative h-full w-full">
      <Canvas
        camera={{ position: [0.15, 0.12, 0.15], fov: 45, near: 0.001, far: 10 }}
        style={{ background: "#F5F5F3" }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 8, 3]} intensity={0.8} />
        <Environment preset="studio" environmentIntensity={0.3} />
        <GroundPlane />

        <AnimationController
          parts={parts}
          stepOrder={stepOrder}
          steps={steps}
          exploded={exploded}
          animStateRef={anim.animStateRef}
          renderStatesRef={anim.renderStatesRef}
          scrubberProgressRef={anim.scrubberProgressRef}
          onPhaseChange={anim.onPhaseChange}
        />

        {assembly &&
          parts.map((part) => (
            <group key={part.id}>
              <PartMesh
                part={part}
                renderStatesRef={anim.renderStatesRef}
                selectedStepId={selectedStepId}
                firstStepIdForPart={partToStepId[part.id] ?? null}
                wireframeOverlay={wireframe}
                onClick={() => handlePartClick(part.id)}
              />
              {selectedStepId === partToStepId[part.id] && part.graspPoints[0] && (
                <ApproachVector
                  origin={(part.position as [number, number, number]) ?? [0, 0, 0]}
                  direction={
                    (part.graspPoints[0].approach as [number, number, number]) ?? [0, -1, 0]
                  }
                  length={0.04}
                />
              )}
            </group>
          ))}

        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.1}
          minDistance={0.05}
          maxDistance={1}
          makeDefault
        />
      </Canvas>

      <ViewerControls
        exploded={exploded}
        onToggleExplode={() => setExploded((e) => !e)}
        wireframe={wireframe}
        onToggleWireframe={() => setWireframe((w) => !w)}
        animating={anim.isAnimating}
        paused={anim.isPaused}
        onToggleAnimation={anim.toggleAnimation}
        onStepForward={anim.stepForward}
        onStepBackward={anim.stepBackward}
        onResetView={() => controlsRef.current?.reset()}
        onReplayDemo={anim.replayDemo}
        demoPlayed={anim.demoPlayed}
      />

      {(anim.isAnimating || anim.demoPlayed) && (
        <AnimationTimeline
          totalSteps={totalSteps}
          scrubberProgressRef={anim.scrubberProgressRef}
          onScrub={anim.scrub}
          onScrubStart={anim.scrubStart}
          onScrubEnd={anim.scrubEnd}
        />
      )}
    </div>
  );
}
