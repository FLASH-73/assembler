/**
 * Lightweight event bus for recording lifecycle events.
 * Allows TeachingContext to observe recording state without coupling to RecordingControls.
 */

type RecordingEvent =
  | { type: "started"; stepId: string; startTime: number }
  | { type: "stopped" }
  | { type: "discarded" };

type Listener = (event: RecordingEvent) => void;

const listeners = new Set<Listener>();

export const recordingEvents = {
  emit(event: RecordingEvent): void {
    for (const fn of listeners) fn(event);
  },
  subscribe(fn: Listener): () => void {
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  },
};

export type { RecordingEvent };
