// Hook that encapsulates animation state management and control handlers.
// Keeps AssemblyViewer.tsx under the 200-line limit.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  type AnimationPhase,
  type AnimationState,
  type PartRenderState,
  INITIAL_STATE,
  scrubberToStep,
  TIMING,
} from "./animation";

const STEP_DURATION = TIMING.STEP_EASE_IN + TIMING.STEP_HOLD;

export function useAnimationControls(assemblyId: string | undefined, totalSteps: number) {
  const [uiPhase, setUiPhase] = useState<AnimationPhase>("idle");

  const animStateRef = useRef<AnimationState>({ ...INITIAL_STATE });
  const renderStatesRef = useRef<Record<string, PartRenderState>>({});
  const scrubberProgressRef = useRef(0);

  // Auto-play demo on assembly load / change
  const prevAssemblyId = useRef<string | null>(null);
  useEffect(() => {
    if (!assemblyId) return;
    if (assemblyId === prevAssemblyId.current) return;
    prevAssemblyId.current = assemblyId;
    animStateRef.current = { ...INITIAL_STATE, phase: "demo_fadein" };
    setUiPhase("demo_fadein");
  }, [assemblyId]);

  const onPhaseChange = useCallback((phase: AnimationPhase) => {
    setUiPhase(phase);
  }, []);

  const toggleAnimation = useCallback(() => {
    const s = animStateRef.current;
    if (s.phase === "idle") {
      Object.assign(animStateRef.current, {
        phase: "playing" as const,
        phaseTime: 0,
        stepIndex: 0,
        stepProgress: 0,
        paused: false,
      });
      setUiPhase("playing");
    } else if (s.paused) {
      animStateRef.current.paused = false;
    } else {
      animStateRef.current.paused = true;
    }
  }, []);

  const stepForward = useCallback(() => {
    const s = animStateRef.current;
    if (s.phase !== "playing" && s.phase !== "demo_assemble") {
      Object.assign(animStateRef.current, {
        phase: "playing" as const,
        phaseTime: 0,
        stepIndex: 0,
        stepProgress: 1,
        paused: true,
      });
      setUiPhase("playing");
      return;
    }
    if (s.stepIndex < totalSteps - 1) {
      const next = s.stepIndex + 1;
      Object.assign(animStateRef.current, {
        stepIndex: next,
        stepProgress: 0,
        phaseTime: next * STEP_DURATION,
        paused: true,
      });
    }
  }, [totalSteps]);

  const stepBackward = useCallback(() => {
    const s = animStateRef.current;
    if (s.phase !== "playing" && s.phase !== "demo_assemble") return;
    if (s.stepIndex > 0) {
      const prev = s.stepIndex - 1;
      Object.assign(animStateRef.current, {
        stepIndex: prev,
        stepProgress: 0,
        phaseTime: prev * STEP_DURATION,
        paused: true,
      });
    }
  }, []);

  const replayDemo = useCallback(() => {
    animStateRef.current = { ...INITIAL_STATE, phase: "demo_fadein" };
    setUiPhase("demo_fadein");
  }, []);

  const scrubStart = useCallback(() => {
    if (animStateRef.current.phase === "idle") {
      Object.assign(animStateRef.current, { phase: "scrubbing" as const, paused: true });
      setUiPhase("scrubbing");
    } else {
      animStateRef.current.paused = true;
    }
  }, []);

  const scrub = useCallback(
    (t: number) => {
      const { stepIndex, stepProgress } = scrubberToStep(t, totalSteps);
      Object.assign(animStateRef.current, {
        phase: "playing" as const,
        stepIndex,
        stepProgress,
        phaseTime: stepIndex * STEP_DURATION,
        paused: true,
      });
      setUiPhase("playing");
      scrubberProgressRef.current = t;
    },
    [totalSteps],
  );

  const scrubEnd = useCallback(() => {
    // Stay paused at current position
  }, []);

  // Force idle during live execution
  const forceIdle = useCallback(() => {
    if (animStateRef.current.phase !== "idle") {
      animStateRef.current = { ...INITIAL_STATE, demoPlayed: true };
      setUiPhase("idle");
    }
  }, []);

  return {
    uiPhase,
    animStateRef,
    renderStatesRef,
    scrubberProgressRef,
    onPhaseChange,
    toggleAnimation,
    stepForward,
    stepBackward,
    replayDemo,
    scrubStart,
    scrub,
    scrubEnd,
    forceIdle,
    isAnimating: uiPhase !== "idle",
    isPaused: animStateRef.current.paused,
    demoPlayed: animStateRef.current.demoPlayed,
  };
}
