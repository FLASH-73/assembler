"use client";

// Minimal point-sprite particle burst on step success.
// Uses a fixed pool of 16 points — no allocations per frame.

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { Vec3 } from "@/lib/animation";

interface SuccessParticlesProps {
  /** Burst origin, or null when inactive. */
  burstPosition: Vec3 | null;
  /** Assembly scale factor (assemblyRadius) for sizing. */
  scale: number;
}

const PARTICLE_COUNT = 16;
const BURST_DURATION = 0.8;
const GRAVITY = -9.8;

export function SuccessParticles({ burstPosition, scale }: SuccessParticlesProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const burstTimeRef = useRef(BURST_DURATION + 1); // start expired
  const velocitiesRef = useRef(new Float32Array(PARTICLE_COUNT * 3));
  const prevBurstRef = useRef<Vec3 | null>(null);

  const { geometry, material } = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.PointsMaterial({
      color: "#2A9D5C",
      size: Math.max(scale * 0.008, 0.003),
      transparent: true,
      opacity: 1,
      sizeAttenuation: true,
      depthWrite: false,
    });
    return { geometry: geo, material: mat };
  }, [scale]);

  useFrame((_, delta) => {
    if (!pointsRef.current) return;

    // Detect new burst
    if (
      burstPosition &&
      (prevBurstRef.current === null ||
        burstPosition[0] !== prevBurstRef.current[0] ||
        burstPosition[1] !== prevBurstRef.current[1] ||
        burstPosition[2] !== prevBurstRef.current[2])
    ) {
      prevBurstRef.current = burstPosition;
      burstTimeRef.current = 0;

      const pos = geometry.attributes.position as THREE.BufferAttribute;
      const vel = velocitiesRef.current;
      const s = Math.max(scale, 0.05);
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const i3 = i * 3;
        (pos.array as Float32Array)[i3] = burstPosition[0];
        (pos.array as Float32Array)[i3 + 1] = burstPosition[1];
        (pos.array as Float32Array)[i3 + 2] = burstPosition[2];
        vel[i3] = (Math.random() - 0.5) * s * 0.3;
        vel[i3 + 1] = Math.random() * s * 0.4;
        vel[i3 + 2] = (Math.random() - 0.5) * s * 0.3;
      }
      pos.needsUpdate = true;
    }

    burstTimeRef.current += delta;
    if (burstTimeRef.current > BURST_DURATION) {
      material.opacity = 0;
      return;
    }

    const t = burstTimeRef.current;
    material.opacity = 1 - t / BURST_DURATION;

    const posArr = (geometry.attributes.position as THREE.BufferAttribute).array as Float32Array;
    const vel = velocitiesRef.current;
    const grav = GRAVITY * Math.max(scale, 0.05);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      const vx = vel[i3] ?? 0, vy = vel[i3 + 1] ?? 0, vz = vel[i3 + 2] ?? 0;
      posArr[i3] = (posArr[i3] ?? 0) + vx * delta;
      posArr[i3 + 1] = (posArr[i3 + 1] ?? 0) + vy * delta;
      posArr[i3 + 2] = (posArr[i3 + 2] ?? 0) + vz * delta;
      vel[i3 + 1] = vy + grav * delta;
    }
    (geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
  });

  return <points ref={pointsRef} geometry={geometry} material={material} />;
}
