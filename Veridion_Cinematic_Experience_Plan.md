# Veridion — "The Corroboration": Full Cinematic Experience Plan
### A ground-up translation of the Everest/Suraj interaction model into Veridion's real trust engine

This supersedes the earlier landing-page-only plan. Everest's site uses the *physical ascent* as its spine — altitude, oxygen, danger zones, a summit. Veridion has no mountain, so the spine here is the **real pipeline a signal travels through to become trusted intelligence**: raw hotspot detection → validation → dependency/collusion analysis → drift check → confidence fusion → published incident. That pipeline is the "ascent." The camera literally flies the globe visiting real incident locations in the order the pipeline would process them, and the "altitude" telemetry is replaced by trust telemetry that is real, not decorative.

Every mechanic from the reference is mapped 1:1 below, with the Veridion equivalent, exact technical implementation, and — per your instruction — a **Failure Mode Register** at the end that names what breaks, why, and the concrete fix, instead of "add a fallback."

---

## 1. Global Navigation Paradigms

Two modes, same as the reference, no third mode invented:

### 1.1 Scroll Climb → "Trace Mode" (default)
- Scroll input drives a camera spline exactly as in §2 of the earlier plan (Lenis + GSAP ScrollTrigger → single `progress` ref → `useFrame`-driven camera).
- **Dynamic velocity is not cosmetic here — it is driven by real data**, not a hardcoded deceleration curve. Each waypoint (§4) carries a `frictionCoefficient` computed from the actual trust-engine severity at that location: a waypoint sitting on a **collusion cluster** or an **active drift event** gets a low `scrollToProgressRatio` (requires more physical scroll input to advance the same `progress` distance) — mechanically identical to Everest's Icefall deceleration, but the trigger is `dependency_cluster.severity` or `drift_event.cusum_statistic`, pulled from the same source-registry data as the dashboard. This is what makes it honest rather than theatrical.
- At the terminal waypoint (the published incident / "Verdict"), scroll input stops advancing camera position along the spline and instead drives a slow orbital rotation around the final incident marker — same behavioral swap as Everest's summit.

### 1.2 "Run the Trace" — automated cinematic mode
- One primary button: **"Run the Trace"**, paired with a toggle back to manual scroll.
- Activating it: apply CSS letterbox bars (top/bottom, animated in via `clip-path` or simple absolutely-positioned bars, not a JS-driven mask — cheaper and avoids the failure mode in §7.1), lock aspect ratio, hand camera control to a GSAP timeline that plays the entire spline at a fixed pace synced to the audio score (§6).
- While active, the same `progress` value still drives everything (HUD, waypoint cards, node coloring) — the automated timeline **writes to the same ref** the scroll handler would have written to. This is the only way cinematic mode and manual mode stay visually identical; do not build two separate code paths for "what the scene looks like at progress=0.4," only one path for "what sets progress."
- Seek bar appears at the bottom, scrubbing `progress` directly, identical UX to a video player.

---

## 2. Free Flight — the real GIS sandbox

- Button labeled **"Explore the Network"**, also bound to key `E`.
- On activation: camera detaches from spline, `OrbitControls`/custom FPS-style rig takes over.
- Controls: mouse → pitch/yaw, `WASD` → lateral translation, `Space` → altitude up, `Shift` → speed multiplier, `Esc` → interpolate camera back to last spline position (store the exact `progress` value at the moment of detachment, re-run the Camera Director's keyframe lookup for that `progress` to compute the return position — do not store the raw camera transform, since re-entering at a stale transform will look like a jump-cut if the spline itself was edited later).
- What's explorable is the **actual live source graph** — every real node/arc from the source registry, not a subset curated for the story. This is the one place in the whole experience where the user can wander off-narrative and this is deliberate: it proves (same as Everest proving the terrain is a real dataset, not a backdrop) that Veridion's trust graph is a real, queryable structure, not a scripted animation.
- Free Flight requires a second, heavier tier of instancing (full registry vs. curated snapshot) — see Failure Mode Register §7.4 for the exact performance fix.

---

## 3. HUD / Telemetry — real trust variables, not fake ones

Persistent header: static coordinate readout is replaced with nothing fixed (Veridion is global, there's no single lat/lon to anchor); instead show **live UTC + "N sources monitored"** count pulled from the source registry on load.

Primary telemetry dashboard, six variables, all bound to the trust engine's actual output at the current waypoint — not interpolated for effect:

| Telemetry Variable | At Stage 1 (raw signal) | At Final Stage (verdict) | Real data source |
|---|---|---|---|
| **Confidence** | ~12% (single unverified hotspot) | 94% (fused, independent-family confidence) | Fusion layer output, same field the dashboard's confidence band uses |
| **Independent Sources** | 1 | 17 (post-dependency-collapse count) | `evidence_contribution` count after clustering |
| **Discounted / Collusion Flags** | 0 | 2 | Count of sources folded into a dependency cluster |
| **Drift Flags** | 0 | 1 | Count of sources with an active CUSUM alert |
| **Freshness** | Live (seconds old) | Live (seconds old) | `ingest_timestamp` delta, actually ticking, not scripted |
| **Pipeline Stage** | "Raw Detection" | "Published Incident" | Literal `stage` enum the backend already tracks per assessment |

- These six values update **every `useFrame` tick** by reading the currently-active waypoint's snapshot object (see §5) and interpolating numerically between the previous and next waypoint's values as `progress` moves through that segment — this gives the "counting up/down" feel Everest's altimeter has, without it ever showing a number the backend didn't actually produce.
- HUD numbers must be DOM (`<Html>` from drei or a plain absolutely-positioned React overlay), never WebGL-rendered text — non-negotiable, same reasoning as the earlier plan (accessibility + legibility + no re-render cost on font metrics).

---

## 4. Stage-by-Stage Architecture — the pipeline as waypoints

Everest has 13 fixed physical stages. Veridion's spine is the trust pipeline, which has a fixed number of **stages** (6, matching the actual backend phases) but a **variable, real number of waypoints per stage** (however many notable sources/incidents illustrate that stage well, chosen from real data, refreshed on the same cadence as `/public/story-snapshot` in the earlier plan). Do not hardcode a fixed "13" — hardcoding a count that must map to real data is exactly the kind of assumption you asked to remove.

**Stage I — Raw Signal.** Camera opens over a single real NASA FIRMS hotspot detection, isolated, dim, no corroboration. Card: "One sensor, one reading. Nothing yet to trust." Data grid: instrument, provider, timestamp, raw confidence value as delivered by the source (uncorrected).

**Stage II — Validation.** Camera pans to where 3–5 more independent readings cluster spatially. Card explains anomaly/contradiction flagging — if any of these readings genuinely contradict each other in the underlying data, that contradiction is shown as a real flagged pair, not staged.

**Stage III — The Trust Graph.** Camera pulls back to show the graph structure (as in the earlier plan's §2.6): nodes = sources, arcs = corroboration, seeded from real registry lat/lon. Card: "Agreement isn't proof."

**Stage IV — Collusion Discounting (the deceleration zone).** Scroll friction increases here per §1.1. Camera locks on a real dependency cluster; three nodes visually merge exactly as specified in the earlier plan's §2.7, driven by the actual clustering output, reversible on scroll-back.

**Stage V — Drift Detection.** Second friction zone. Real sensor with an active or historical CUSUM alert changes color olive→amber→oxide-red as its real historical deviation series plays out.

**Stage VI — Confidence Bounding & Fusion.** Abstract space, per the earlier plan's §2.9, using a real Bayesian LCB output pair (new vs. established source).

**Final Waypoint — The Verdict.** Same as the earlier plan's §2.10: real card, real confidence %, real evidence trail link, `GET /assessments/latest-featured`.

Each waypoint's card follows the same three-part layout discipline as Everest's stages: **title block** (stage name + key metric), **bullet hazard/insight summary** (what this stage catches), **data grid** (the specific real numbers for the specific real source/cluster/incident shown). This consistency is what let Everest's UI scale to 13 stages without becoming visually chaotic — keep it strict.

---

## 5. Rendering / Performance Settings Panel

Same categories as the reference, mapped to Veridion's actual shader/postprocessing budget — not a copy of Everest's toggle names, the Veridion-specific equivalents:

| Control | Veridion equivalent |
|---|---|
| Audio toggle (`M`) | Same — toggles Web Audio context |
| Auto / Manual performance mode | Same mechanism: FPS monitor disables Bloom first, then arc instancing density, then particle counts, in that fixed priority order (see §7.2 for why order matters) |
| Render scale slider | 0.75× / 1.0× / 1.25× / 1.5×, identical mechanism |
| Anti-aliasing | Off / 2× / 4× MSAA |
| "God rays" | Directional light shafts through the globe's atmosphere shader at the golden-hour waypoints |
| "Bloom / grade" | Gold glow on active nodes/arcs + overall color grade LUT |
| "Data fog" (Veridion's "Valley mist") | Low-opacity volumetric fog over regions with sparse/unreliable coverage — this is data-driven too: fog density scales with `1 - confidence` for that region, so it's a real uncertainty visualization, not atmosphere for its own sake |
| "Corroboration density" (Veridion's "Cloud sea") | Toggle for the ambient particle layer representing background sensor noise below the "verified" layer |
| "Frost / glass" | Epilogue blur — see §6.1 for the exact same occlusion-culling optimization Everest uses, implemented, not assumed |

---

## 6. Invisible UX: Typography, Audio, Lighting

### 6.1 Dynamic contrast text
- Same technique as the reference: sample the rendered scene's luminance behind each DOM text element's screen-space bounding box every frame (via a low-res offscreen render target, not full-res — sampling full resolution every frame is the actual performance killer here; see §7.3), and lerp the text color between two fixed endpoints — **ivory** (on dark background) and **near-black** (on bright gold-lit snow-equivalent/bloom areas) — never solving for arbitrary colors, only ever choosing between these two, which guarantees palette compliance (§ design tokens) can never be violated by the luminance system picking an off-palette color.

### 6.2 Spatial audio
- Web Audio API, one score, structured in acts matching the 6 pipeline stages, not scroll-position-only — bind act changes to `currentStage` (derived from `progress`), not raw scroll delta, so scrubbing quickly through a stage doesn't retrigger the same act repeatedly (a real bug class in scroll-linked audio; the fix is act transitions are triggered on stage boundary crossings only, debounced, not on every frame).
- Autoplay policy: the "Run the Trace" / first scroll-input click is the literal unlock gesture for `AudioContext.resume()`. A pulsing "best with sound" header notice, same as the reference.

### 6.3 Lighting
- One key light (directional, gold-tinted), scene lit per-waypoint with a small set of preset light-angle/color-grade values keyed to `waypointId`, interpolated the same way camera keyframes are (§2.4 of the earlier plan) — not a generic day-night cycle, since Veridion's "time of day" has no real-world meaning the way Everest's dawn-to-dusk climb does. Each waypoint simply has a designed lighting mood; consistency comes from interpolating between them smoothly, not from simulating physical time.
- UI cards fade out at any waypoint explicitly flagged `visualPriority: high` in the waypoint data (e.g., the collusion-collapse moment) — implemented as a simple opacity multiplier on the `TextOverlay` component keyed to the current waypoint, not a manual per-scene special case.

---

## 7. Failure Mode Register — the "no fallback, here's the fix" section

This is the part that matters most per your instruction. Each row: what breaks, the actual root cause, and the fix that gets implemented — not deferred to "add error handling."

### 7.1 Letterbox/cinematic mode causes layout thrash
- **Symptom:** entering "Run the Trace" causes a visible jump/flash as letterbox bars animate in.
- **Root cause:** if letterboxing is implemented by resizing the `<Canvas>` element itself, Three.js has to reallocate the WebGL context's render targets and recompute the camera aspect ratio mid-transition, which is expensive and visibly stutters.
- **Fix:** never resize the canvas. Keep the canvas full-viewport always; letterbox bars are two separate absolutely-positioned DOM `<div>`s animated in via `transform: scaleY()` on top of the canvas, with `pointer-events: none`. The 3D scene's camera aspect ratio never changes — only what's visually covered changes. This is the same trick real cinematic web experiences use and it costs zero GPU re-init.

### 7.2 Auto performance mode oscillates (drops Bloom, FPS recovers, re-enables Bloom, FPS drops again, repeat)
- **Root cause:** naive auto-quality systems toggle a setting the instant FPS crosses a threshold in either direction, causing visible flicker in a feedback loop.
- **Fix:** hysteresis, not a single threshold. Disable an effect when FPS < 45 sustained for 30 consecutive frames; only re-enable it when FPS > 55 sustained for 90 consecutive frames. Disable effects in a fixed priority order (Bloom → arc instance count → particle count → shadow resolution) one at a time, re-measuring between each, rather than dropping everything at once — this is also why the priority order in §5's table is specified explicitly rather than left to "whatever's easiest."

### 7.3 Dynamic-contrast text sampling tanks frame rate
- **Root cause:** sampling full-resolution pixel data from the WebGL canvas every frame for every text element (`gl.readPixels` is synchronous and blocking on most drivers) stalls the render pipeline — this is the single most common reason "luminance-sensing text" demos die in production.
- **Fix:** render a second, tiny (e.g., 64×36px) low-resolution copy of the scene to an offscreen render target every frame (cheap — it's a fraction of the main render's fragment count), and sample luminance from *that* target at the downscaled coordinates corresponding to each text element's screen position. Never call `readPixels` against the main framebuffer.

### 7.4 Free Flight mode (§2) drops to single-digit FPS when the full registry loads
- **Root cause:** the curated story snapshot (dozens of nodes) is cheap; the full source registry (potentially thousands of sources at scale) rendered as individual meshes is not — this is a straightforward instancing/LOD problem, not a "such is WebGL" problem.
- **Fix:** two concrete measures, both implemented, not optional: (1) all source nodes render as a single `InstancedMesh` with per-instance color/scale attributes updated via a `InstancedBufferAttribute`, never as individual `<mesh>` components — this is a hard requirement, not a nice-to-have, above roughly 200 nodes. (2) Frustum-based LOD: only sources within camera view frustum + a small margin are included in the instance buffer at full detail; sources outside it are excluded from the draw call entirely (recomputed on camera move, throttled to run at most every 100ms, not every frame).

### 7.5 Scroll-driven scene desyncs from real data after the backend recomputes overnight
- **Root cause:** if waypoint data is fetched once on page load and the trust engine reruns ingestion/clustering overnight, a user with a long-lived tab (or a cached page) sees numbers that no longer match the live dashboard — an honesty failure, not just a bug, given this whole plan's premise is that the story is data-true.
- **Fix:** the `/public/story-snapshot` endpoint (from the earlier plan) is versioned (`snapshot_version` field). On mount, the client checks the current version against a lightweight `HEAD`-style version-check endpoint polled every 5 minutes; if stale, show a small non-blocking "Updated data available — refresh" affordance rather than silently serving stale numbers or forcing a disruptive reload mid-scroll.

### 7.6 Bidirectional scroll breaks the collusion-collapse / drift animations
- **Root cause:** if any part of these animations is implemented as a GSAP `.timeline()` with `.play()`/`.reverse()` calls triggered by scroll direction, fast direction changes (flick up, flick down, flick up) queue conflicting tween instructions and the animation state desyncs from `progress`.
- **Fix:** zero timeline-based triggering anywhere in the story. Every animated value (arc merge interpolation, node color, particle spread) is a **pure function of `progress`**, recomputed from scratch every frame (`value = lerp(a, b, localT)`), never a stateful tween that "remembers" which direction it was last going. This was already specified in the earlier plan (§2.7) — restating it here because it is the rule that makes every other stage's reversibility work, and it must be enforced project-wide, not just in Stage IV.

### 7.7 Mobile/low-GPU devices get a broken half-loaded scene instead of a clean redirect
- **Root cause:** attempting to detect "is this device capable" via feature-testing alone (checking for WebGL2 support) is insufficient — a device can technically support WebGL2 and still be too weak to run the full scene, producing a technically-working-but-unusably-slow experience, which is worse than a clean redirect.
- **Fix:** two-stage gate, not one. (1) Hard gate: no WebGL2 context available → immediate DOM-only redirect to the statistical epilogue (§8), no canvas attempted. (2) Soft gate: WebGL2 available but `navigator.hardwareConcurrency <= 4` or viewport width < 768px → load the scene at forced 0.75× render scale, Bloom/god-rays/fog disabled by default (user can manually re-enable via settings, at their own risk, per §5's Manual mode), rather than attempting full fidelity and relying on the auto-quality system to claw it back after a bad first impression.

### 7.8 `prefers-reduced-motion` users still get the scroll-hijacking pin
- **Root cause:** ScrollTrigger's `pin: true` behavior itself — locking the viewport and remapping scroll to camera movement — is a motion pattern independent of whether any individual animation respects reduced-motion; disabling only the *particle/color* animations while leaving the pin active still produces vestibular-triggering camera motion.
- **Fix:** check `prefers-reduced-motion` before ScrollTrigger initializes at all. If set, never call `ScrollTrigger.create({pin: true, ...})` — instead render each waypoint as a normal, unpinned DOM section with a static framed screenshot-equivalent camera shot (camera snapped to that waypoint's keyframe, fully static, no `useFrame` camera updates) and let the page scroll normally between them. This is a structurally different code path, decided once at mount, not a set of conditionally-skipped animations layered on top of the pinned version.

---

## 8. Epilogue — "The Ledger of Trust"

Same structural role as Everest's Ledger: a DOM-heavy statistical close-out, using the frosted-glass occlusion-culling optimization from §7.6-adjacent logic — the moment the glass overlay reaches 100% opacity, the `useFrame` loop for the 3D scene is explicitly paused (`invalidate: false` / manual render-on-demand mode in R3F, or a simple boolean guard around the render call), not just visually obscured — this is the actual optimization the reference site claims, and it's a two-line guard, not something to leave implicit.

Contents, all sourced from real platform data (not placeholder stats):
- **Macro telemetry panel**: total incidents assessed, total sources onboarded, collusion clusters caught, drift events caught, published-vs-discounted ratio — real counts from the database, queried once at build/ISR time or cached per §7.5's versioning.
- **Dual-axis historical chart**: incidents assessed vs. false-discount rate over time, scrubbable tooltip, gold/oxide-red color coding for calibration-pass vs. calibration-fail periods — mirrors Everest's summits/deaths chart exactly in interaction pattern.
- **Attrition funnel**: "From Raw Signal to Published Incident" — raw hotspot detections → passed validation → survived dependency discounting → passed drift check → included in fusion → published — real per-stage counts, same visual grammar as Everest's "Permit to Summit" funnel.
- **Source spotlight carousel**: real source registry entries (provider, instrument, coverage, trust history) in place of Everest's biographical carousel — same left/right arrow interaction.
- **Global map**: real source geographic origins, same interaction pattern as "The Pull of the Mountain."
- **Footer**: data attributions (NASA FIRMS, NOAA, whichever real providers are actually integrated — do not list a provider here that Phase 2 hasn't actually wired up), "Back to the surface" as the back-to-top anchor, WebGL-unsupported fallback text, standard credits.

---

## 9. Build sequence (adds to, does not replace, the earlier plan's §5)

1. Build the six-stage waypoint data model and the `/public/story-snapshot` + version-check endpoints first — everything downstream depends on this being real and stable.
2. Build Trace Mode (manual scroll) end to end for all six stages before touching Cinematic Mode or Free Flight — get the core spine data-true and bidirectionally reversible (§7.6) first.
3. Build the Failure Mode Register fixes **as you build each corresponding feature**, not as a hardening pass afterward — e.g., §7.3's offscreen-luminance-sampling approach is how dynamic typography gets built the first time, not a later optimization.
4. Cinematic Mode (§1.2) next — it reuses the same `progress`-writing contract, so it should be close to free once Trace Mode is solid.
5. Free Flight (§2) after that, with §7.4's instancing/LOD work built in from the first commit, not retrofitted once it's already slow.
6. Settings panel (§5) and reduced-motion/mobile gating (§7.7, §7.8) — build these before considering the experience shippable, same discipline as the earlier plan.
7. Epilogue/Ledger (§8) last, since it depends on real aggregate stats that are more meaningful once the rest of the platform has real usage/data volume behind it.
