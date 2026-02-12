"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { useAssembly } from "@/context/AssemblyContext";
import { useExecution } from "@/context/ExecutionContext";
import { GroundPlane } from "./GroundPlane";
import { PartMesh } from "./PartMesh";
import { ApproachVector } from "./ApproachVector";
import { ViewerControls } from "./ViewerControls";
import { AnimationTimeline } from "./AnimationTimeline";

type PartState = "ghost" | "active" | "complete" | "selected";

export function AssemblyViewer() {
  const { assembly, selectedStepId, selectStep } = useAssembly();
  const { executionState } = useExecution();
  const controlsRef = useRef<OrbitControlsImpl>(null);

  const [exploded, setExploded] = useState(false);
  const [wireframe, setWireframe] = useState(false);
  const [animating, setAnimating] = useState(false);
  const [animationStep, setAnimationStep] = useState(0);

  const totalSteps = assembly?.stepOrder.length ?? 0;

  // Animation timer
  useEffect(() => {
    if (!animating) return;
    const interval = setInterval(() => {
      setAnimationStep((prev) => {
        const next = prev + 1;
        if (next >= totalSteps) {
          setAnimating(false);
          return totalSteps - 1;
        }
        return next;
      });
    }, 800);
    return () => clearInterval(interval);
  }, [animating, totalSteps]);

  // Determine which visual state each part should have
  const getPartState = useCallback(
    (partId: string): PartState => {
      if (!assembly) return "ghost";

      // If selected and matches the selected step's parts
      if (selectedStepId) {
        const selStep = assembly.steps[selectedStepId];
        if (selStep?.partIds.includes(partId)) return "selected";
      }

      const isRunning = executionState.phase === "running" || executionState.phase === "paused";

      if (isRunning) {
        // Find which step this part belongs to
        for (const stepId of assembly.stepOrder) {
          const step = assembly.steps[stepId];
          if (!step?.partIds.includes(partId)) continue;
          const rs = executionState.stepStates[stepId];
          if (!rs) continue;
          if (rs.status === "success") return "complete";
          if (rs.status === "running" || rs.status === "retrying" || rs.status === "human") {
            return "active";
          }
          return "ghost";
        }
        return "ghost";
      }

      // Animation mode
      if (animating || animationStep > 0) {
        for (let i = 0; i < assembly.stepOrder.length; i++) {
          const stepId = assembly.stepOrder[i];
          if (!stepId) continue;
          const step = assembly.steps[stepId];
          if (!step?.partIds.includes(partId)) continue;
          if (i < animationStep) return "complete";
          if (i === animationStep) return "active";
          return "ghost";
        }
      }

      return "ghost";
    },
    [assembly, selectedStepId, executionState, animationStep, animating],
  );

  const handlePartClick = useCallback(
    (partId: string) => {
      if (!assembly) return;
      // Find the first step that references this part
      const stepId = assembly.stepOrder.find((sid) => {
        const step = assembly.steps[sid];
        return step?.partIds.includes(partId);
      });
      selectStep(stepId ?? null);
    },
    [assembly, selectStep],
  );

  const handleResetView = useCallback(() => {
    controlsRef.current?.reset();
  }, []);

  return (
    <div className="relative h-full w-full">
      <Canvas
        camera={{
          position: [0.15, 0.12, 0.15],
          fov: 45,
          near: 0.001,
          far: 10,
        }}
        style={{ background: "#F5F5F3" }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 8, 3]} intensity={0.8} />
        <Environment preset="studio" environmentIntensity={0.3} />

        <GroundPlane />

        {assembly &&
          Object.values(assembly.parts).map((part) => {
            const state = getPartState(part.id);
            return (
              <group key={part.id}>
                <PartMesh
                  part={part}
                  state={state}
                  exploded={exploded}
                  wireframeOverlay={wireframe}
                  onClick={() => handlePartClick(part.id)}
                />
                {(state === "active" || state === "selected") && part.graspPoints[0] && (
                  <ApproachVector
                    origin={part.position ?? [0, 0, 0]}
                    direction={(part.graspPoints[0].approach as [number, number, number]) ?? [0, -1, 0]}
                    length={0.04}
                  />
                )}
              </group>
            );
          })}

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
        animating={animating}
        onToggleAnimation={() => {
          if (!animating) {
            setAnimationStep(0);
            setAnimating(true);
          } else {
            setAnimating(false);
          }
        }}
        onStepForward={() =>
          setAnimationStep((s) => Math.min(s + 1, totalSteps - 1))
        }
        onStepBackward={() => setAnimationStep((s) => Math.max(s - 1, 0))}
        onResetView={handleResetView}
      />

      {(animating || animationStep > 0) && (
        <AnimationTimeline
          currentStep={animationStep}
          totalSteps={totalSteps}
          onScrub={setAnimationStep}
        />
      )}
    </div>
  );
}
