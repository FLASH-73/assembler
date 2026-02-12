"use client";

interface AnimationTimelineProps {
  currentStep: number;
  totalSteps: number;
  onScrub: (step: number) => void;
}

export function AnimationTimeline({
  currentStep,
  totalSteps,
  onScrub,
}: AnimationTimelineProps) {
  if (totalSteps === 0) return null;

  const progress = totalSteps > 1 ? currentStep / (totalSteps - 1) : 0;

  return (
    <div className="absolute bottom-3 left-6 right-6 flex items-center gap-2">
      <div className="relative h-4 flex-1 flex items-center">
        {/* Track */}
        <div className="absolute h-[2px] w-full rounded-full bg-bg-tertiary" />

        {/* Fill */}
        <div
          className="absolute h-[2px] rounded-full bg-accent transition-all duration-300"
          style={{ width: `${progress * 100}%` }}
        />

        {/* Step dots */}
        {Array.from({ length: totalSteps }, (_, i) => {
          const x = totalSteps > 1 ? (i / (totalSteps - 1)) * 100 : 50;
          const isActive = i <= currentStep;
          return (
            <button
              key={i}
              onClick={() => onScrub(i)}
              className={`absolute h-[6px] w-[6px] -translate-x-1/2 rounded-full transition-colors ${
                isActive ? "bg-accent" : "bg-bg-tertiary"
              }`}
              style={{ left: `${x}%` }}
            />
          );
        })}

        {/* Handle */}
        <div
          className="absolute h-2 w-2 -translate-x-1/2 rounded-full bg-accent shadow-sm transition-all duration-300"
          style={{ left: `${progress * 100}%` }}
        />
      </div>

      <span className="text-[11px] font-mono text-text-tertiary tabular-nums">
        {currentStep + 1}/{totalSteps}
      </span>
    </div>
  );
}
