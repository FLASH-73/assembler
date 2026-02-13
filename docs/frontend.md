# AURA — Frontend Design System

## Product Name

**AURA** — Autonomous Universal Robotic Assembly. AIRA is the arm, AURA is the brain that orchestrates assembly.

CLI commands use `aura`: `aura run`, `aura teach step_003`, `aura status`.
The frontend header says **AURA** in the wordmark. The page title is "AURA — Assembly Platform."

---

## Design Philosophy

**Precise, clinical, authoritative.** This is a precision engineering instrument — think Jony Ive's Apple meets Dieter Rams's Braun meets a machinist's quality control station. The software should feel as precise as the machines it controls.

### Core Principles

1. **Cool and precise** — zinc-toned white backgrounds, sharp contrast. The palette is clinical, not warm. Cool neutrals convey precision; warmth conveys comfort. We want precision.

2. **Color is information** — the background is neutral. The brand accent is near-black (zinc-900) — confidence doesn't need color. The ONE color that pops is signal blue (#2563EB), used only for "system active" states (running execution, selected items, connected indicator). Blue means "something is happening." Nothing else screams.

3. **Typography is hierarchy** — big monospace numbers for metrics (cycle time at 36px, stats at 72px). Engraved-panel-style labels (10px, 600 weight, uppercase, wide tracking). The data should be scannable from across a desk.

4. **Whitespace is confidence** — don't cram. A few well-placed elements with room to breathe. The 3D viewer goes edge-to-edge. Metrics have generous spacing. The interface stays calm even when the robot is running.

5. **No decoration** — no gradients, no glassmorphism, no blob backgrounds, no floating particles, no animated borders. Every pixel earns its place by conveying information or supporting readability.

---

## Color System

```css
@theme inline {
  /* Backgrounds — cool zinc palette */
  --color-bg-primary: #FAFAFA;       /* Pure neutral white */
  --color-bg-secondary: #F4F4F5;     /* Zinc-50 — cards, panels */
  --color-bg-tertiary: #E4E4E7;      /* Zinc-200 — borders, dividers */
  --color-bg-viewer: #F8F8FA;        /* Slight cool tint for 3D viewer */
  --color-bg-elevated: #FFFFFF;      /* True white for elevated panels */

  /* Text — sharp contrast */
  --color-text-primary: #09090B;     /* Zinc-950 — headings, primary */
  --color-text-secondary: #52525B;   /* Zinc-600 — labels, descriptions */
  --color-text-tertiary: #A1A1AA;    /* Zinc-400 — metadata, timestamps */

  /* Brand — precision dark (the brand IS precision) */
  --color-accent: #18181B;           /* Zinc-900 — primary buttons, wordmark */
  --color-accent-hover: #27272A;     /* Zinc-800 */
  --color-accent-light: #F4F4F5;     /* Zinc-50 — subtle selected states */

  /* Signal — one electric blue for active/CTA states */
  --color-signal: #2563EB;           /* Blue-600 — "system active" */
  --color-signal-light: #EFF6FF;     /* Blue-50 */

  /* Status */
  --color-status-success: #16A34A;   /* Green-600 */
  --color-status-running: #2563EB;   /* Blue-600 (matches signal) */
  --color-status-warning: #CA8A04;   /* Yellow-600 */
  --color-status-error: #DC2626;     /* Red-600 */
  --color-status-human: #7C3AED;     /* Violet-600 */
  --color-status-pending: #D4D4D8;   /* Zinc-300 */

  /* Status backgrounds (used by AnalysisPanel + UploadDialog) */
  --color-status-success-bg: #F0FDF4;
  --color-status-running-bg: #EFF6FF;
  --color-status-warning-bg: #FEFCE8;
  --color-status-error-bg: #FEF2F2;
  --color-status-human-bg: #F5F3FF;
}
```

### Usage Rules

- The brand accent (`--accent`, zinc-900) creates dark primary buttons (Start, Watch Demo). The wordmark "AURA" uses `text-primary` (near-black), not accent.
- Signal blue (`--signal`, #2563EB) is the ONLY pop of color: selected step left-border, active timeline fill, focus rings, interactive highlights. Blue means "something is happening."
- Status colors appear ONLY on status dots, connection indicators, and step indicators. Never as background fills for entire sections.
- Text is always `text-primary` or `text-secondary`. Never use status colors for body text.
- Borders use `bg-tertiary`. One pixel, solid. No colored borders except on focused inputs (use `--signal`).

---

## Typography

```css
/* Primary: DM Sans — geometric, clean, distinctive 'a' and 'g' */
--font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Monospace: JetBrains Mono — industrial character, excellent for data */
--font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
```

### Type Scale

| Element | Size | Weight | Font | Color | Notes |
|---------|------|--------|------|-------|-------|
| AURA wordmark | 16px | 700 | Sans | `text-primary` | letter-spacing 0.2em, all caps |
| Cycle time (TopBar) | 36px | 500 | Mono | `text-primary` | dominant number on screen |
| Landing hero title | 64px | 800 | Sans | `text-primary` | letter-spacing 0.08em |
| Landing stats | 72px | 600 | Mono | `text-primary` | billboard numbers |
| Section heading | 14px | 600 | Sans | `text-primary` | |
| Step names | 14px | 500 | Sans | `text-primary` | slightly heavier than before |
| Body / labels | 13px | 400 | Sans | `text-secondary` | |
| Metric value (large) | 20px | 500 | Mono | `text-primary` | in StepDetail |
| Metric value (bottom bar) | 16px | 500 | Mono | `text-primary` | instrument readout |
| Metric/panel label | 10px | 600 | Sans uppercase | `text-tertiary` | tracking 0.06-0.08em, engraved style |
| Status badge | 10px | 600 | Sans uppercase | `text-secondary` | dot + label, no pill |
| Button text | 13px | 500 | Sans | white or `text-primary` | |

### Rules

- Never use font sizes below 9px (bottom bar labels are 9px)
- AURA wordmark uses 700 weight; other headings use 600
- Uppercase ONLY for panel labels, metric labels, and status badges
- Letter-spacing: `0.06em`-`0.08em` on uppercase labels, `0.2em` on wordmark, `0` elsewhere
- Line height: 1.5 for body text, 1.2 for headings, 1.0 for metrics

---

## Layout

### Main Screen (Assembly Dashboard)

This is the ONE screen. Everything happens here. No modals, no page navigation, no sidebar drawers (except settings).

```
┌─────────────────────────────────────────────────────────────────┐
│  AURA     [Assembly: Bearing Housing v1]       ⏱ 02:34   ▶ ⏸ ■ │  ← Top bar
├─────────────────────────────────────────┬───────────────────────┤
│                                         │                       │
│                                         │  Assembly Steps       │
│                                         │  ┌─────────────────┐  │
│                                         │  │ ① Pick housing ✓│  │
│          3D Assembly Viewer             │  │ ② Place housing ✓│  │
│                                         │  │ ③ Pick bearing ●│  │
│     [animated assembly sequence]        │  │ ④ Insert bearing │  │
│     [parts appear step by step]         │  │ ⑤ Press fit      │  │
│     [approach vectors visible]          │  └─────────────────┘  │
│                                         │                       │
│                                         │  Step Detail          │
│                                         │  ┌─────────────────┐  │
│                                         │  │ Pick bearing     │  │
│   ┌──────────────────────────────┐      │  │ Handler: primitive│ │
│   │ 📷 Camera PiP (during exec) │      │  │ Success: 94%     │  │
│   └──────────────────────────────┘      │  │ Avg time: 3.2s   │  │
│                                         │  └─────────────────┘  │
├─────────────────────────────────────────┴───────────────────────┤
│  Cycle 02:34  │  Success 87%  │  Steps 3/8  │  Run #14         │  ← Bottom bar
└─────────────────────────────────────────────────────────────────┘
```

### Top Bar (48px height)

- Left: **AURA·** wordmark in text-primary (16px/700/0.2em tracking), dot separator in text-tertiary. Assembly selector as borderless dropdown (appearance-none, hover bg-secondary). Connection dot (6px, label on hover only).
- Center: "CYCLE" micro-label (10px uppercase) above the cycle time (36px mono, dominant number on screen).
- Right: Run controls — Start (dark primary button), Pause, Stop, Intervene, E-stop (always red).
- Upload button has moved to the StepList panel header.

### Left Panel — 3D Assembly Viewer (60% width, always visible)

The 3D viewer is the hero of the entire product. It is always present, never hidden behind a tab. It serves three different roles depending on the phase:

**During Setup (no execution running):**
- Full interactive mode — orbit, zoom, pan
- Shows all parts in their final assembled positions (ghost/transparent)
- User clicks "Play Sequence" → parts animate in one by one, each arriving from its approach direction
- Clicking a step in the right panel highlights the relevant part(s) and shows the approach vector
- Parts can be individually selected to inspect grasp points

**During Execution (assembly running):**
- Camera picture-in-picture overlay in the bottom-left corner (resizable, ~25% of viewer)
- 3D view auto-tracks the current step: zooms to the relevant part, highlights it in accent color
- Completed parts solidify to full opacity
- Current part pulses subtly
- Pending parts remain ghosted
- Force/contact data can be overlaid as simple vectors on the current part

**During Teaching (teleop recording for a step):**
- Camera feed becomes full-screen in a modal overlay (operator needs to see the real robot)
- 3D viewer still visible behind at reduced opacity for spatial reference
- After recording, viewer shows the step that was just demonstrated

### Camera Picture-in-Picture

During execution, the live camera feed floats over the 3D viewer:
- Bottom-left corner, 25% viewer width, rounded corners, subtle shadow
- Click to expand to full viewer area (3D viewer slides to background)
- Click again to return to PiP
- Multiple cameras: small tabs at top of PiP to switch between feeds
- Status indicator dot: green = streaming, red = disconnected

### Right Panel (40% width)

**Two sections, stacked:**

1. **Assembly Steps** (top 55%) — Vertical list of steps. Each step is a card showing: step number, name, handler type (primitive/policy icon), status badge. The current step is highlighted. Click a step to see its detail below AND to highlight the corresponding part in the 3D viewer. During execution, auto-scrolls to current step.

   For linear assemblies, this is a simple vertical list. When parallel steps are needed later, this can be upgraded to a React Flow DAG.

2. **Step Detail** (bottom 45%) — Selected step's info: handler configuration, success rate chart (last N runs), average duration, number of demos recorded, trained policy info. Action buttons: "Record Demos", "Train", "Test Step".

### Bottom Bar (32px height)

Instrument panel readout: 16px monospace values with 9px uppercase labels above. Evenly spaced across the bar. Metrics: cycle time, success %, steps completed / total, run number. Hardware and teleop indicators use 6px status dots.

### Responsive Behavior

Don't worry about mobile. This runs on a laptop or desktop next to the robot. Minimum width: 1280px. If window is narrower, panels stack vertically (3D viewer on top, step list below).

---

## 3D Assembly Viewer — Detailed Specification

This is the most important component in the entire product. Build it with care.

### Technology

- `@react-three/fiber` — React renderer for Three.js
- `@react-three/drei` — helpers (OrbitControls, Environment, ContactShadows)
- `three` — core 3D engine
- Parts arrive from the backend as `.glb` (glTF binary) files, tessellated server-side by PythonOCC

### Scene Setup

```
Background:    Radial gradient (#FAFAFA center → #F0F0F2 edges) — studio lighting
Lighting:      One soft directional light (slightly warm) + ambient
               No harsh shadows. Soft contact shadows on the ground plane only.
Ground plane:  Subtle grid — 1px lines, --bg-tertiary at 30% opacity
               Extends beyond the assembly. Gives spatial grounding.
Camera:        Perspective, default position at 45° azimuth, 30° elevation
               OrbitControls: rotate (left drag), zoom (scroll), pan (right drag)
               Smooth damping enabled (damping factor 0.1)
```

### Part Rendering

Parts have four visual states:

| State | Appearance |
|-------|------------|
| **Ghost** (pending) | Wireframe or 10% opacity fill. Neutral grey `#D4D4D0`. Shows where the part will end up. |
| **Active** (current step) | Full opacity, slight warm tint. Accent-colored edge outline (2px). Subtle pulse (opacity 0.85↔1.0, 2s period). |
| **Complete** (step done) | Full opacity, neutral material. No outline. Solid and settled. |
| **Selected** (user clicked) | Full opacity, accent outline, grasp points and approach vector visible. |

Material: MeshStandardMaterial with roughness 0.6, metalness 0.1. Not shiny, not flat. Like machined aluminum under soft light. Parts should look physical.

### Assembly Animation

When the user clicks "Play Sequence" or during the setup review:

1. Start with empty scene (just ground plane)
2. For each step in order:
   - Part fades in at its **approach position** (offset along approach vector, ~2x part height above)
   - Part moves along approach vector to its **final assembled position** (500ms ease-in-out)
   - Brief pause (300ms)
   - Next step begins
3. Total animation is controllable: play, pause, step forward, step backward
4. Timeline scrubber at the bottom of the viewer (thin, unobtrusive)

The approach position and vector come from the assembly graph's step data. If not specified, default to straight-down approach (part drops from above).

### Approach Vectors

Shown as thin lines with small arrowheads:
- Color: `--text-tertiary` at 60% opacity
- Length: proportional to part size (1.5x bounding box height)
- Only visible on active or selected parts
- Arrow points in the direction the part travels during insertion

### Grasp Points

Shown as small spheres (radius = 3% of part bounding box):
- Color: `--signal` (#2563EB) at 80% opacity
- Only visible when a part is selected and the step uses a primitive
- Connected to the part surface with a thin line
- Tooltip on hover: grasp index, approach angle

### Camera Controls Overlay

Top-right of the viewer, minimal buttons (icon only, 28px, semi-transparent background on hover):
- 🔄 Reset view (return to default camera position)
- 📐 Toggle wireframe overlay
- 💥 Toggle exploded view (parts spread apart along their approach vectors)
- ▶ Play/pause assembly animation
- ⏮ ⏭ Step backward/forward in animation

### Performance

- Target: 60fps with up to 50 parts visible
- Use instancing for identical parts (e.g., multiple screws)
- LOD (Level of Detail) if parts have >50K triangles: simplify when zoomed out
- Lazy load part meshes — show bounding boxes immediately, swap in real geometry
- Frustum culling enabled by default in Three.js

### The Demo Moment

When a STEP file is uploaded and parsed, the 3D viewer should:

1. Parts appear one by one in their assembled positions (fast, 100ms each)
2. Brief pause showing the complete assembly
3. "Explode" — parts spread apart along their approach vectors
4. "Assemble" — parts animate back together in the proposed sequence order
5. User sees the assembly plan come alive in seconds

This is the moment someone understands what AURA does. Make it smooth, make it fast, make it feel inevitable.

---

## Components

### Step Card (ruled lines, no card backgrounds)

```
  3  Pick bearing            · RUNNING
     primitive · pick           3.2s
─────────────────────────────────────
  4  Insert bearing           · PENDING
     primitive · linear_insert
```

- Left: 20px monospace step number in a 32px column
- Center: step name (14px/500, primary text), handler type (12px, secondary)
- Right: dot+label status badge, duration
- Steps separated by 1px ruled lines (border-b bg-tertiary), no card background
- Selected step: 2px left border in signal blue, no background change

States:
- **Pending** — number in text-tertiary, "PENDING" dot+label
- **Running** — number in signal blue with pulse animation, "RUNNING" dot+label
- **Success** — thin 1px-stroke checkmark SVG in success green, "DONE" dot+label
- **Failed** — thin 1px-stroke X in error red, "FAILED" dot+label
- **Human** — number in violet, "HUMAN" dot+label
- **Retrying** — number in warning amber, "RETRY 2/3" dot+label

### Metric Card

```
┌──────────────┐
│  CYCLE TIME  │  ← label: 11px, uppercase, tertiary color
│    02:34     │  ← value: 32px, monospace, primary color
│  avg 02:12   │  ← context: 12px, mono, tertiary color
└──────────────┘
```

No border. No background. Just the number with its label. The whitespace around it IS the card.

### Action Button

Primary (Start Assembly): accent background, white text, 13px font-weight 500, 8px padding vertical, 16px horizontal, 6px border-radius. No shadow.

Secondary (Pause, Train): transparent background, `--text-primary` text, 1px `--bg-tertiary` border. Same sizing.

Danger (E-Stop, Stop): `--status-error` background, white text. Always visible during execution.

### Status Badge

6px circle (filled with status color) + 10px uppercase label in text-secondary. No pill background, no colored text. Cleaner, more technical — like an LED indicator with an engraved label.

### 3D Viewer

See the **3D Assembly Viewer — Detailed Specification** section above for full rendering, animation, and interaction specs. The viewer is the hero component and deserves the most engineering attention.

### Camera Picture-in-Picture

Floating overlay during execution:
- Bottom-left of 3D viewer, ~25% viewer width
- Rounded corners (8px), subtle drop shadow (0 2px 8px rgba(0,0,0,0.08))
- Click to expand / collapse (25% → 60% of viewer)
- Camera selector tabs if multiple feeds
- Green/red streaming status dot

### Upload Dialog

Modal triggered by "+ Upload" button in StepList panel header:
- Drag-and-drop zone for `.step` / `.stp` files
- File input fallback
- States: idle → uploading (spinner) → error
- Calls `POST /assemblies/upload` with FormData
- On success: closes, triggers assembly list refresh, selects new assembly
- Close on Escape key or overlay click

### Recording Controls

Shown in StepDetail panel when a step is selected:
- "Record Demos" button starts teleop + recording (`POST /recording/step/{stepId}/start`)
- Elapsed timer (MM:SS format) during active recording
- "Stop Recording" flushes to HDF5, "Discard" abandons
- Shows demo count for current step

### Demo List

Below RecordingControls in StepDetail:
- Lists all recorded demos for the selected step
- Each row: timestamp, duration, delete button
- Fetches from `GET /recording/demos/{assemblyId}/{stepId}`
- Empty state: "No demos recorded yet"

### Training Progress

Shown in StepDetail for policy-type steps:
- "Train Policy" button → `POST /training/step/{stepId}/train`
- Polls `GET /training/jobs/{jobId}` every 2s during training
- Shows: progress %, loss sparkline (Recharts AreaChart), status
- States: idle → training (with progress) → complete (policy ID) → failed

### Mini Chart

Small inline chart used in StepDetail metrics:
- Recharts AreaChart showing recent run success/failure
- Maps runs to 1 (success) / 0 (failure) values
- Minimal: no axes, no labels, just the shape

### Animation System

Pure logic in `lib/animation.ts` (no React or Three.js dependencies):
- Phase machine: `idle → demo_fadein → demo_hold → demo_explode → demo_assemble → playing → scrubbing`
- Per-part render state: `{ position, opacity, visualState }` computed by `computePartAnimation()`
- Easing: cubic ease-in-out
- Scrubber: bidirectional `scrubberToStep()` / `stepToScrubber()` mapping

`lib/useAnimationControls.ts` — React hook wrapping animation state:
- Returns: `toggleAnimation`, `stepForward`, `stepBackward`, `replayDemo`, `scrubStart`, `scrub`, `scrubEnd`, `forceIdle`
- Auto-plays demo on assembly change

`viewer/AnimationController.tsx` — Renderless component inside Canvas:
- `useFrame` callback ticks phase machine every frame
- Writes to shared refs (not React state) for 60fps performance
- Computes centroid and explode offsets on part change

---

## Tech Stack

```json
{
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@react-three/fiber": "^9.0.0",
    "@react-three/drei": "^10.0.0",
    "three": "^0.182.0",
    "recharts": "^3.7.0",
    "tailwindcss": "^4.0.0",
    "swr": "^2.4.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/react": "^19.0.0",
    "@types/three": "^0.182.0"
  }
}
```

### Rules

- **TypeScript strict mode.** No `any`. No `// @ts-ignore`.
- **One component per file**, max 200 lines. If it's bigger, split it.
- **No component libraries** (no shadcn, no MUI, no Chakra). Hand-craft the ~25 components you need. They'll be simpler and more cohesive.
- **No prop drilling** beyond 2 levels. Use React context for shared state (assembly, execution status, WebSocket connection).
- **Data fetching:** `useSWR` for polling data (metrics, step status). WebSocket for real-time streams (motor telemetry, camera feeds).
- **No `useEffect` for data fetching.** Use SWR or Server Components.
- **State management:** React state + context. No Redux, no Zustand, no Jotai. The state is simple: current assembly, execution status, selected step.

### File Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout with Providers wrapper
│   ├── page.tsx                # Assembly dashboard (main + only screen)
│   └── globals.css             # Tailwind v4 @theme inline + color tokens
├── components/
│   ├── Providers.tsx           # SWR + WebSocket + Assembly + Execution context nesting
│   ├── TopBar.tsx              # AURA wordmark, assembly selector, upload, controls
│   ├── BottomBar.tsx           # Metrics strip + teleop indicator
│   ├── DemoBanner.tsx          # "Demo Mode" banner when no hardware connected
│   ├── RunControls.tsx         # Start / pause / resume / stop / intervene / E-stop
│   ├── UploadDialog.tsx        # Modal: drag-drop .step/.stp upload → POST /assemblies/upload
│   ├── StepList.tsx            # Assembly steps list with auto-scroll
│   ├── StepCard.tsx            # Individual step card (status icon, badge, duration)
│   ├── StepDetail.tsx          # Selected step info + metrics + recording + training
│   ├── RecordingControls.tsx   # Start/stop/discard recording with elapsed timer
│   ├── DemoList.tsx            # Recorded demos with timestamps and delete
│   ├── TrainingProgress.tsx    # Train button, polling progress, loss sparkline
│   ├── MetricCard.tsx          # Single metric display (label, value, context)
│   ├── MiniChart.tsx           # Recharts AreaChart for success/failure history
│   ├── StatusBadge.tsx         # Step status dot + label (pending/running/success/failed/human/retrying)
│   ├── ActionButton.tsx        # Primary / secondary / danger variants
│   ├── CameraPiP.tsx           # Picture-in-picture camera overlay (placeholder)
│   ├── TeachingOverlay.tsx     # Full-screen camera during teleop recording
│   └── viewer/
│       ├── AssemblyViewer.tsx  # Main Three.js canvas + scene setup
│       ├── PartMesh.tsx        # Single part: ghost/active/complete/selected states
│       ├── AnimationController.tsx # Renderless: ticks phase machine at 60fps via useFrame
│       ├── ViewerControls.tsx  # Overlay buttons (reset, wireframe, explode, play, step)
│       ├── AnimationTimeline.tsx # Draggable scrubber bar with step dots
│       ├── GroundPlane.tsx     # Grid + contact shadows
│       ├── ApproachVector.tsx  # Arrow showing insertion direction
│       └── GraspPoint.tsx      # Grasp pose indicator sphere
├── context/
│   ├── AssemblyContext.tsx      # SWR-backed assembly + step selection
│   ├── ExecutionContext.tsx     # Sequencer state (WebSocket or mock timer fallback)
│   └── WebSocketContext.tsx     # Real-time connection with mock heartbeat fallback
├── lib/
│   ├── types.ts                # Shared TypeScript types (mirrors backend models)
│   ├── api.ts                  # All API calls + withMockFallback() wrapper
│   ├── ws.ts                   # AuraWebSocket class with graceful degradation
│   ├── animation.ts            # Pure animation logic (no React/Three.js deps)
│   ├── useAnimationControls.ts # React hook for 3D viewer animation state
│   ├── hooks.ts                # useKeyboardShortcuts, useConnectionStatus
│   └── mock-data.ts            # Mock assembly, execution state, metrics
├── package.json
└── tsconfig.json
```

Note: Tailwind v4 uses `@theme inline` in `globals.css` — there is no `tailwind.config.ts`.

### API Client Pattern

```typescript
// lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// All fetches use withMockFallback() — catches TypeError (network unavailable)
// and returns mock data from lib/mock-data.ts. HTTP errors are NOT caught.

export const api = {
  // Health / System
  health: () => get<{ status: string }>("/health"),
  fetchSystemInfo: () => get<SystemInfo>("/system/info"),

  // Assembly
  getAssemblies: () => get<AssemblySummary[]>("/assemblies"),
  getAssembly: (id: string) => get<Assembly>(`/assemblies/${id}`),
  uploadCAD: (file: File) => postFile<Assembly>("/assemblies/upload", file),
  updateStep: (assemblyId: string, stepId: string, data: Partial<AssemblyStep>) =>
    patch(`/assemblies/${assemblyId}/steps/${stepId}`, data),

  // Execution
  startAssembly: (id: string) => post(`/execution/start`, { assembly_id: id }),
  pauseExecution: () => post("/execution/pause"),
  resumeExecution: () => post("/execution/resume"),
  stopExecution: () => post("/execution/stop"),
  intervene: () => post("/execution/intervene"),
  getExecutionState: () => get<ExecutionState>("/execution/state"),

  // Teleop
  startTeleop: (arms: string[], mock?: boolean) => post("/teleop/start", { arms }, mock),
  stopTeleop: () => post("/teleop/stop"),
  getTeleopState: () => get<TeleopState>("/teleop/state"),

  // Recording
  startRecording: (stepId: string, assemblyId: string) =>
    post(`/recording/step/${stepId}/start`, { assembly_id: assemblyId }),
  stopRecording: () => post("/recording/stop"),
  discardRecording: () => post("/recording/discard"),
  listDemos: (assemblyId: string, stepId: string) =>
    get<DemoInfo[]>(`/recording/demos/${assemblyId}/${stepId}`),

  // Training (STUBBED on backend)
  trainStep: (stepId: string, config: TrainConfig) =>
    post(`/training/step/${stepId}/train`, config),
  getTrainingJob: (jobId: string) => get<TrainStatus>(`/training/jobs/${jobId}`),
  listTrainingJobs: () => get<TrainStatus[]>("/training/jobs"),

  // Analytics
  getStepMetrics: (assemblyId: string) => get<StepMetrics[]>(`/analytics/${assemblyId}/steps`),
};
```

---

## Animations & Transitions

Minimal. Intentional. Never decorative.

**Allowed:**
- Step status badge color transitions: 200ms ease
- Panel show/hide: 150ms ease-out
- Current step highlight pulse: subtle opacity oscillation (0.8 → 1.0, 2s period)
- 3D viewer part appearance: quick fade-in (200ms) when stepping through sequence
- Loading indicators: simple spinner or progress bar

**Not allowed:**
- Page transitions
- Card hover animations
- Staggered list reveals
- Parallax
- Bouncing, wobbling, or spring physics
- Anything that makes the user wait

---

## Accessibility

- All interactive elements have focus states (2px `--signal` blue outline)
- Status is never conveyed by color alone (always has text label or icon)
- Keyboard navigation for step list (arrow keys) and run controls (spacebar = start/pause)
- Minimum contrast ratio: 4.5:1 for body text, 3:1 for large text
- Camera feeds have alt text describing what the camera shows ("Workspace camera — top view")

---

## What This Is NOT

- Not a design system for a marketing site
- Not a component library to be published
- Not a dark-themed hacker interface
- Not a mobile-first responsive app
- Not a dashboard with 20 different pages
- Not anything with a sidebar navigation

It's ONE screen that shows an operator everything they need to set up, teach, run, and monitor an assembly. If you need a second screen, you've designed the first one wrong.
