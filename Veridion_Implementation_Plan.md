# Veridion — End-to-End Implementation Plan
### Cinematic landing experience → live trust-engine product

This plan assumes the existing repo structure from your `implementation_plan.txt` and `README.md` (Next.js/TypeScript + FastAPI + PostgreSQL/PostGIS + Redis + Supabase Auth, Docker Compose, offline demo mode). It does **not** replace that plan — it makes Phase 6 (landing experience) fully specified and buildable, and shows exactly how it wires into Phases 2–5 so the whole thing is real, not a mockup.

Nothing here is code to run. This is the spec to build from.

---

## 0. What "done" looks like

- A visitor lands on a near-black, gold-linework hero that matches the reference image exactly (typography, spacing, globe framing, navbar).
- Scrolling does not scroll a page — it drives a single WebGL scene through a fixed camera path, cross-faded with text panels, until the globe "becomes" the operational dashboard.
- Every visual event in the scroll story (sources lighting up, collusion collapse, drift turning a node red, confidence interval shrinking) is rendered from **real precomputed data**, not baked animation — so the story is honest and the same engine that powers the dashboard powers the intro.
- After the story, the same Canvas either docks into a dashboard globe widget or unmounts cleanly into the authenticated app shell — no jump cut, no reload.
- Reduced-motion and low-power devices get a real fallback, not a broken experience.

---

## 1. Design System (must be locked before any scene work starts)

| Token | Value / role |
|---|---|
| `--bg-near-black` | Base canvas + page background |
| `--ivory` | Primary text on dark |
| `--gold` | Primary accent — linework, active nodes, CTAs, underlines |
| `--umber` | Secondary text, muted UI chrome |
| `--olive` | Success / verified-source state |
| `--oxide-red` | Risk / discounted / drift-flag state |
| No blue, anywhere | Not in charts, not in map/globe water, not in generated imagery, not in focus rings |

- One serif-display face for headline moments (Section 1, Section 4, Section 7 cards), one technical sans for UI, labels, and dashboard chrome.
- Focus states: gold outline, never blue — must be verified against WCAG contrast on near-black (gold on near-black passes; ivory-on-umber must be checked).
- These tokens live in one shared `theme.ts` / CSS variable file imported by both the landing scene (as JS constants, since WebGL can't read CSS vars directly) and the dashboard component library, so a palette change never drifts out of sync.

---

## 2. High-level technical approach for the cinematic landing page

**Core principle: one persistent WebGL canvas, driven by scroll progress as a single number (0→1), not eight separate animations.**

```
ScrollProgress (0.0 – 1.0)
        │
        ├─▶ Camera Director   (position, lookAt, fov per keyframe)
        ├─▶ Scene Director    (which visual state: dormant / awakening / network / collapse / drift / confidence / final card / dock)
        ├─▶ Text Director     (which copy panel is visible, fade timing)
        └─▶ Data Director     (which precomputed trust snapshot feeds the visuals at this point)
```

Everything downstream reads from one `scrollProgress` value. This is the only way to keep camera, text, and data visually synchronized and to make the transition into the dashboard a continuation of the same state machine rather than a hard cut.

### 2.1 Stack

| Concern | Tool | Why |
|---|---|---|
| Scene renderer | **React Three Fiber** (Three.js) | Declarative scene graph, plays well with React state/Zustand |
| Camera/lighting helpers | **@react-three/drei** | OrbitControls (disabled during story, enabled after dock), `Line`, `Html`, `useTexture`, `Stars` |
| Scroll engine | **Lenis** (smooth scroll) + **GSAP ScrollTrigger** | Lenis normalizes scroll input across trackpad/wheel/touch; ScrollTrigger converts scroll position into a 0–1 progress value and drives a pinned section |
| Cross-fading text/UI over canvas | **Framer Motion** | Opacity/translate transitions for text panels, nav state changes |
| Global scroll state | **Zustand** | `scrollProgress`, `activeSection`, `sceneState` shared between the R3F canvas (inside `<Canvas>`, can't use React context from outside easily) and the DOM overlay |
| Postprocessing | `@react-three/postprocessing` | Bloom (for gold glow on active nodes/arcs), subtle vignette — used sparingly, restrained per your motion rules |
| Trust graph (post-landing dashboard) | **React Flow** or **Cytoscape.js** | 2D interactive graph, not part of the 3D globe scene |

### 2.2 Page structure

```
/app/(marketing)/page.tsx
  └─ <LandingExperience>
       ├─ <FixedCanvasLayer>        (position: fixed, full-viewport, z-index below overlay)
       │    └─ <Canvas>
       │         ├─ <Globe />
       │         ├─ <SatelliteField />
       │         ├─ <TrustArcs data={snapshot} />
       │         ├─ <CollusionCluster />
       │         ├─ <DriftSensor />
       │         ├─ <ConfidenceParticles />
       │         └─ <CameraDirector progress={scrollProgress} />
       ├─ <ScrollSections>          (tall DOM sections, height only — invisible spacers that drive ScrollTrigger)
       │    ├─ <Section id="silence" />
       │    ├─ <Section id="awakening" />
       │    ├─ <Section id="network" />
       │    ├─ <Section id="collusion" />
       │    ├─ <Section id="drift" />
       │    ├─ <Section id="confidence" />
       │    ├─ <Section id="verdict" />
       │    └─ <Section id="dock" />
       ├─ <TextOverlay progress={scrollProgress} />   (Framer Motion text panels, DOM, above canvas)
       └─ <NavBar state={navState} />                 (solid → glass transition)
```

The DOM `<Section>` elements have real height (e.g. 100–150vh each) purely to give ScrollTrigger scroll distance to measure. The Canvas itself does not scroll — it's `position: fixed`, pinned by ScrollTrigger for the entire story duration, and everything visible changes because `scrollProgress` changes, not because anything moves in DOM space.

### 2.3 Scroll → progress wiring

- Wrap the whole story region in one GSAP `ScrollTrigger` with `pin: true`, `scrub: true` (or a small numeric scrub value like `0.6` for slight lag — reads as "cinematic," not laggy/broken), `start`/`end` spanning the total height of the eight stacked `<Section>` spacers.
- On every scroll update, write `progress` (0–1) into the Zustand store. Do not call `setState` directly from the GSAP callback into React render — write to a ref-backed store (Zustand `subscribeWithSelector` or a plain mutable ref read inside `useFrame`) so the R3F render loop reads it on every frame without triggering React re-renders. This is the single most important performance decision: **camera and shader updates happen inside `useFrame`, driven by a mutable ref, never by React state re-renders.**
- Lenis is initialized once at the app root and its `scroll` event is what drives GSAP's ticker (`gsap.ticker.add`), so trackpad/wheel/touch all normalize through one smooth-scroll pipeline before ScrollTrigger reads it.

### 2.4 Camera Director — the actual choreography

Define a fixed array of camera keyframes as data, not ad hoc code:

```
keyframes = [
  { t: 0.00, pos: [0, 0, 12], lookAt: [0,0,0], fov: 35 },   // Section 1 — Silence, full globe, static
  { t: 0.12, pos: [0, 0, 8],  lookAt: [0,0,0], fov: 35 },   // Section 2 — push in, sources wake
  { t: 0.30, pos: [3, 1, 4],  lookAt: [2,0.5,1], fov: 40 }, // Section 3 — lock over Asia region
  { t: 0.45, pos: [2.2,0.8,3.2], lookAt: [2,0.6,1], fov: 30 }, // Section 4 — zoom into 3-node cluster
  { t: 0.58, pos: [-2,0.5,3.5], lookAt: [-1.8,0.4,1], fov: 32 }, // Section 5 — pan to drifting sensor
  { t: 0.70, pos: [0,0,2],   lookAt: [0,0,0], fov: 50 },    // Section 6 — pull inside, abstract confidence space
  { t: 0.85, pos: [0,0,10],  lookAt: [0,0,0], fov: 35 },    // Section 7 — pull back, full globe, verdict card
  { t: 1.00, pos: [0,-1.5,6],lookAt: [0,0,0], fov: 35 },    // Section 8 — dock position, globe slides to dashboard slot
]
```

- Interpolate between keyframes with cubic easing per segment (not linear) — use `THREE.CatmullRomCurve3` for `pos` across all keyframes so the camera travels a single smooth spline rather than snapping direction at each waypoint, and slerp for orientation via `lookAt` targets interpolated the same way.
- `useFrame` on every tick: read `scrollProgress` from the ref, find the surrounding keyframe segment, compute eased local `t`, set `camera.position` and call `camera.lookAt(...)`. No `OrbitControls` active during the story (`enabled={false}`); re-enabled only at `t = 1` when the user reaches the dashboard-docked globe widget, so post-story the globe becomes genuinely explorable.

### 2.5 The Globe

- Base sphere: `THREE.SphereGeometry`, custom `ShaderMaterial` (not a stock texture) so day/night terminator, gold coastline linework, and glow can be tuned to the palette — avoid photographic Earth textures with blue oceans, which breaks the no-blue rule. Coastlines rendered as thin emissive gold line overlays on a near-black/umber sphere, consistent with "precise gold technical linework on a near-black field" from the reference.
- Atmosphere: a slightly larger backface sphere with a Fresnel-based glow shader, gold-tinted, low opacity — gives the rim glow visible in the reference image without introducing any blue.
- Rotation: slow constant idle rotation (`group.rotation.y += delta * 0.02`) during Section 1 only; rotation is taken over by the Camera Director once the story begins so scroll position, not autoplay, controls what's visible.

### 2.6 Satellites, sensors, and trust arcs (Sections 2–3)

- Source nodes (satellites, ground stations, sensors) are positioned on the globe surface from **real lat/lon coordinates in the source registry**, converted to 3D sphere coordinates (`lat/lon → xyz` standard formula), not placed by hand. This is what makes the intro data-true rather than decorative.
- Each node is a small instanced mesh (`InstancedMesh` for performance — there may be dozens to hundreds of sources) with an emissive material; brightness/color driven by that source's **current trust score** pulled from the same precomputed snapshot the dashboard uses (see §4).
- Trust/corroboration edges: `THREE.CatmullRomCurve3` arcs between two node positions, lofted outward from the sphere surface (like airline-route arcs), rendered as a thin `TubeGeometry` or `Line2` (fat line) in gold, with opacity/width scaled by edge weight from the trust graph.
- Node/arc appearance is staggered in on scroll progress via a simple `t`-indexed reveal (each source has a `revealAt` value spread across the `0.12–0.30` scroll range) rather than all appearing at once — this is what creates the "world waking up" feel without being random or fake.

### 2.7 Section 4 — Collusion collapse (this is the "Oh" moment, protect it)

- At `t ≈ 0.42–0.48`: three specific source nodes (a real dependency cluster identified by the collusion-discounting layer, not staged) pulse bright olive/gold as if independently verified.
- At `t ≈ 0.46`: camera keyframe zooms tight on that cluster (per §2.4).
- Animate the three arcs connecting those nodes to a shared upstream point contracting/merging into one line — implemented as a `THREE.TubeGeometry` whose control points interpolate from three separate curves to one shared curve over a short scroll window, driven by the same `t` inside `useFrame` (lerp control points directly, not a scripted animation clip — keeps it scroll-scrubbable in both directions, including scrolling back up).
- The three node materials transition color olive → oxide-red over the same window; a numeric "combined trust weight" label (rendered via `<Html>` from drei, billboard-facing camera) ticks down live, matching the real discounted value the collusion-detection layer produced for that cluster in the source registry.
- Critically: **this must work scrolling backward too** — since everything is driven by `t`, not a one-shot animation trigger, scrubbing up should reverse the merge cleanly. Test this explicitly; it's the easiest thing to get wrong with GSAP timelines that aren't purely scrub-driven.

### 2.8 Section 5 — Drift

- One specific sensor node (a real one with a documented CUSUM drift event, or a clearly-labeled synthetic fixture per Phase 2's "clearly label all adversarial scenarios" rule) transitions color olive → amber → oxide-red as `t` sweeps `0.55–0.62`, driven by that source's actual CUSUM statistic value at sequential historical timestamps, not a fake gradient.
- Behind/below it, a thin 2D line-chart plane (rendered as a `<Html>` overlay or a flat plane with a canvas-texture sparkline) shows the real trust-over-time series for that source, drawn progressively as `t` advances — same data the dashboard's "trust-over-time" drill-down uses.

### 2.9 Section 6 — Confidence (abstract space)

- Camera pulls to `fov: 50`, globe fades out (opacity animated via the shader material's uniform, not by unmounting — unmounting/remounting a shader-heavy mesh mid-scrub causes visible stutter).
- Render a small number of particle clusters representing confidence-interval width for a new vs. established source, using real Bayesian-LCB output values (interval bounds) mapped to visual spread — an established source's particles are tight around the mean, a brand-new source's particles are wide and slowly narrow as `t` advances through its (compressed, illustrative) history window.
- This section carries real methodology into visuals; do not let it become arbitrary "particles look pretty" motion — every width/spread number should trace back to an actual Wilson/Bayesian LCB computation for a specific source you choose ahead of time for the story.

### 2.10 Section 7 — Verdict card

- Globe fades back in, camera pulls to full-globe framing.
- A single `<Html>`-rendered card (real DOM, not WebGL text — text should never be WebGL-rendered, it kills accessibility and text quality) fades in with the actual current incident/assessment output: confidence %, source count, discounted count, drifting count, "Evidence trail →" link.
- This card's content comes from a real API call (`GET /assessments/latest-featured` or similar — see §4) made once on page load, not hardcoded — if the underlying data changes, the landing page reflects it. Cache this response at build/ISR time if you don't want the marketing page hitting the live DB on every visitor.

### 2.11 Section 8 — Dock into dashboard

- `t = 0.85 → 1.0`: camera eases to the "dock" keyframe; simultaneously the DOM nav bar transitions from transparent/hero state to the persistent glass app header (see §2.13); the eight `<Section>` scroll spacers end and normal document flow resumes.
- Two implementation options — pick one explicitly before building:
  - **(A) Canvas persists across the route boundary**: the landing globe becomes the literal globe widget embedded in the dashboard mission-control page (e.g., a mini interactive globe panel). Requires the Canvas and its Zustand store to live above the Next.js route in a persistent layout, and the dashboard route to just resize/reposition it. More impressive, more engineering risk (state must survive route change, canvas must resize cleanly, auth-gated dashboard content must not require the public marketing bundle).
  - **(B) Canvas unmounts, dashboard has its own separate (lighter-weight) globe widget** that fades in as the story globe fades out, positioned identically at the dock keyframe so the cut is imperceptible. Simpler, safer, recommended for the first working version — ship (B), revisit (A) as a polish pass once the base product is solid.
- Recommendation: **build (B) first.** It's fully achievable, isolates risk, and still delivers "feels seamless" if the dock keyframe position/framing is matched pixel-for-pixel between the two components.

### 2.12 Reduced motion / performance fallback

- Respect `prefers-reduced-motion`: skip the scroll-driven camera entirely, render each section as a static framed shot of the same 3D scene (camera snapped to each keyframe, no interpolation, no particle motion) that advances on a simple "Next" affordance or normal scroll without pinning. Same visuals, no motion.
- Device tiering: detect low-end GPU/mobile (e.g., via a cheap heuristic — `navigator.hardwareConcurrency`, viewport width, or a WebGL renderer-info check) and serve a pre-rendered video/Lottie fallback of the same story instead of live WebGL, or drop postprocessing (Bloom) and instanced-node counts.
- Cap devicePixelRatio (e.g., `Math.min(window.devicePixelRatio, 2)`) — uncapped DPR on retina/4K displays is the most common cause of a "cinematic" WebGL scene tanking to single-digit FPS.

### 2.13 Navbar transition

- Two visual states only: **solid** (Section 1, opaque near-black, full-contrast gold logo/links) and **glass** (from the moment scroll begins past Section 1, `backdrop-filter: blur()` + semi-transparent near-black background).
- Driven by the same `scrollProgress`: state flips once `t > ~0.03` (i.e., essentially "has the user started scrolling at all"), with a Framer Motion cross-fade on background/opacity — not tied to individual section boundaries, so it doesn't flicker.
- Must independently pass contrast/focus-visible checks in the glass state, since translucency over moving imagery is the easiest place to silently fail accessibility.

---

## 3. Backend / trust engine (feeds every scene, not just the dashboard)

This is unchanged in substance from Phases 2–3 of your existing implementation plan — repeating the essentials here because the landing page depends on it directly:

1. **Ingestion**: scheduled workers pull NASA FIRMS hotspot data + weather context; raw snapshots retained with freshness/licensing/ingest metadata.
2. **Spatial-temporal normalization**: PostGIS clusters nearby readings into candidate incidents.
3. **Source registry**: provider, instrument, coverage, latency, lineage, calibration history, live operational health — this table is what supplies lat/lon + trust score to `<TrustArcs>` and node coloring in the landing scene.
4. **Trust engine**:
   - Bayesian LCB for sparse-history sources (feeds §2.9).
   - CUSUM/Page-Hinkley drift monitoring (feeds §2.8).
   - Dependency clustering: declared provenance + residual co-movement + shared failure patterns + graph structure + disagreement with anchors → collusion clusters (feeds §2.7).
   - Fusion at the independent-family level → confidence interval + evidence contribution + contradiction records (feeds §2.10's verdict card).
5. **What-if recomputation**: remove a source/family, diff against immutable baseline — this exact function powers both the dashboard's what-if simulator and, optionally, a lightweight version could seed the Section 4 collapse animation with a real "before/after" trust-weight number instead of a hardcoded one.

**Key integration point**: expose one additional lightweight, cacheable endpoint specifically for the marketing/landing page — e.g. `GET /public/story-snapshot` — that returns a curated, small payload: the specific source cluster used in Section 3–4, the specific drifting sensor used in Section 5, the specific new-vs-established source pair used in Section 6, and the featured incident for Section 7. This keeps the landing page **honest** (real numbers) without making it depend on live, expensive queries against the full production dataset on every page load. Regenerate this snapshot on a schedule (e.g., nightly) or on-demand from an admin action, and cache it at the edge/ISR layer.

---

## 4. API surface additions (on top of your existing Phase 5 list)

| Endpoint | Purpose |
|---|---|
| `GET /public/story-snapshot` | Curated, cached payload powering the landing page's data-true visuals (§3) |
| `GET /assessments/latest-featured` | Backing data for the Section 7 verdict card |
| `GET /sources?fields=lat,lon,trust_score,status` | Lightweight source registry projection for node placement/coloring — avoid shipping the full registry payload to the public landing bundle |

Everything else (incidents, assessments, evidence trails, source registry/history, what-if analysis, ingestion admin, audit history) is exactly as already scoped in Phase 5.

---

## 5. Build sequence (so nothing gets built out of order)

1. **Design tokens + typography system locked** (Section 1). Nothing visual starts before this.
2. **Static hero only** — exact reproduction of the reference image, no scroll behavior yet, no WebGL. Confirms typography/spacing/navbar/framing are right before any 3D work begins.
3. **Static (non-interactive) Globe component** — shader material, coastlines, atmosphere glow, idle rotation. Confirms the palette/look in 3D before adding motion logic.
4. **Scroll plumbing** — Lenis + ScrollTrigger + Zustand `scrollProgress`, with `<Section>` spacers and a temporary on-screen debug readout of the progress value. No camera choreography yet — just prove scroll → number is reliable, including on scroll-back-up.
5. **Camera Director** — wire keyframes from §2.4, confirm smooth spline travel, forward and backward.
6. **Data-true nodes/arcs** — connect to `/public/story-snapshot`, place real sources, real edges (§2.6).
7. **Section 4 collusion collapse** — build and scrub-test bidirectionally (§2.7) before moving on; this is the highest-risk animation.
8. **Section 5 drift + Section 6 confidence particles** — same scrub-both-directions test discipline.
9. **Section 7 verdict card + Section 8 dock/nav transition.**
10. **Reduced-motion and low-end fallback paths** (§2.12) — build these before calling the landing page done, not as an afterthought.
11. **Wire the dashboard-side globe widget (Option B, §2.11)** and confirm the visual match at the dock position.
12. Only after the landing page is solid: proceed with/continue Phases 3–5 dashboard build (trust graph via React Flow/Cytoscape, evidence trail, what-if simulator, source admin) exactly as scoped in your existing implementation plan — the landing page consumes data from this layer but doesn't block it being built in parallel by someone else.

---

## 6. Testing checklist specific to the cinematic layer

- Scroll forward **and backward** through the entire story at variable speed (slow drag, fast flick, keyboard Page Down) — every section must reverse cleanly since all motion is `t`-driven, not timeline-triggered.
- Resize mid-scroll (rotate a tablet, resize a browser window) — ScrollTrigger + Canvas must recompute pin boundaries and camera aspect without breaking the pin.
- `prefers-reduced-motion: reduce` end-to-end pass.
- Low-end device pass (throttle CPU 4–6x in devtools, or a real mid-range Android) — confirm fallback tier engages and stays above ~30fps.
- Verify every number shown in the story (trust weight, confidence %, source counts) matches what the dashboard shows for the same underlying data — this is the "story teaches the model honestly" requirement, and it's easy to silently drift out of sync if the snapshot endpoint isn't regenerated alongside engine changes.
- Full keyboard/screen-reader pass on the DOM overlay layer (text panels, nav, verdict card) — the WebGL layer should be `aria-hidden`, and all real information must also exist as accessible DOM content, not only as canvas pixels.
