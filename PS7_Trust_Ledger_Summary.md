# Trust Ledger for Earth Intelligence
### PS7 — Trusted Intelligence from Space & Geospatial Data | Xovian Aerospace
### Emerging Technologies Hackathon 2026

---

## 1. Problem Understanding

Decision-makers relying on geospatial/EO data today don't lack access to data — they lack a way to know which data to believe. Standard fusion approaches (averaging, majority voting) implicitly assume sources are independent and equally reliable. In practice:

- Sources often **share upstream providers** (three "independent" weather APIs may all resell the same model output), so agreement is not evidence of truth — it's evidence of shared origin.
- Sensors **degrade silently** (calibration drift, biofouling) long before they fail obviously.
- New sources can look perfectly reliable on a **small, lucky sample** and get over-trusted.

The core insight this idea is built on: **trust should be relational, not intrinsic.** A source is credible only if it is *independently* corroborated — not merely *repeated*.

---

## 2. The Idea

**One-liner:** A trust-scoring layer that sits between raw multi-source geospatial data and the decision-maker, showing not just what the data says but *why it should be believed* — using graph-based trust propagation instead of naive consensus.

**The differentiator:** Every competing team will build a system that outputs a confidence score. This system is built to answer the counterintuitive question: *why should two agreeing sources sometimes be trusted **less** than one disagreeing source?* That's the collusion-discounting insight, and it's the moment this stands out from a room of confidence-score dashboards.

---

## 3. System Architecture

### Four-Layer Trust Engine (backend)

| Layer | Function | Method | Failure it catches |
|---|---|---|---|
| **1. Trust Graph** | Models sources as nodes, corroboration as edges. Credibility is computed from the network, not claimed in isolation. | Personalized PageRank-style propagation, seeded with a small set of verified/ground-truth anchor sources (to avoid circularity/bootstrapping failure) | Sources gaming reputation through unearned association |
| **2. Collusion Discounting** | Detects sources that move together statistically (shared upstream provider) and discounts their *combined* voting weight instead of rewarding "consensus." | Dependency/clique detection over historical co-movement | Fake confidence from non-independent agreement ("copycat" sources) |
| **3. Drift Detection** | Tracks cumulative deviation from a source's running mean over time to catch slow degradation before it corrupts output. | CUSUM / Page-Hinkley test | Silent sensor failure, calibration drift, biofouling |
| **4. Confidence Bounding** | Prevents new/low-sample sources from earning high trust off a short lucky streak. | Bayesian lower-confidence-bound (Wilson-style interval) | "Lucky streak" over-trust on sparse data |

### Full Pipeline

```
[Data Ingestion Layer]
   Cached real dataset (e.g., NASA FIRMS / Sentinel / NOAA / OpenAQ)
   + synthetic injections (collusion cluster, drift, new-source streak, noise)
        │
        ▼
[Trust Engine — 4 layers above, run offline/pre-computed for demo reliability]
        │
        ▼
[Intelligence Generation Layer]
   Insight + recommendation + confidence band + risk flags
        │
        ▼
[Explainability Module]
   Evidence trail: which sources fed the conclusion, which were discounted and why
        │
        ▼
[Decision-Maker Dashboard] ← the primary demo surface
```

### Dashboard (frontend) — this is what carries the "Explainability" + "Demo" + "Practical Utility" scoring weight (35% combined)

- **Trust graph visualization** — nodes colored by trust score, edges show corroboration, clickable
- **"Why was this source discounted"** drill-down — tagged explicitly as collusion / drift / low-sample
- **Trust-over-time view** — click a source, see its score evolve
- **What-if simulator** — remove a source, watch confidence recompute live, in-memory (no live API calls — cached/precomputed state only, for demo reliability)
- **Final recommendation panel** — confidence band + evidence trail, in plain language

---

## 4. Tech Stack

| Layer | Suggested stack | Notes |
|---|---|---|
| Data ingestion / preprocessing | Python (pandas, xarray for geospatial), cached snapshots (no live calls during demo) | Pull once, store static — protects demo from API downtime/rate limits |
| Trust engine | Python — NetworkX (graph/PageRank), NumPy/SciPy (Bayesian bounds, CUSUM), scikit-learn (clustering for collusion detection) | This is largely a domain port of already-validated trust-scoring methodology |
| Backend/API | FastAPI or Node/Express | Serves precomputed graph + scores to frontend; what-if recompute can run server-side or client-side depending on graph size |
| Frontend | React/Next.js | Matches existing stack experience |
| Graph visualization | D3.js, or React Flow / Cytoscape.js | Needs to support click-to-drill-down and live re-render for what-if |
| Charts (trust-over-time, drift) | Recharts or Chart.js | |
| Hosting/demo | Vercel (frontend) + DigitalOcean or Render (backend) | Familiar deploy path |
| Dataset | One real EO/geospatial dataset for texture + credibility, layered with deliberate synthetic injections for the four failure modes | State this hybrid approach explicitly and honestly in the deliverable — it's a strength if disclosed, a weakness if discovered |

---

## 5. Data Strategy

### Real Data Sources (Implemented)

| Source | API | Data Family | Key Required? | Observations |
|---|---|---|---|---|
| **NASA EONET** | `eonet.gsfc.nasa.gov/api/v3/events` | Wildfire events | No | ~40 real wildfire event detections |
| **Open-Meteo (ECMWF)** | `api.open-meteo.com/v1/ecmwf` | Weather (European model) | No | ~44 hourly temperature/humidity/wind readings |
| **Open-Meteo (GFS/NOAA)** | `api.open-meteo.com/v1/forecast?models=gfs_seamless` | Weather (US model) | No | ~44 hourly readings from independent model |
| **Copernicus CAMS** | `air-quality-api.open-meteo.com/v1/air-quality` | Air quality | No | ~44 PM2.5/PM10 hourly readings |
| **NASA FIRMS** | `firms.modaps.eosdis.nasa.gov/api/area/` | Active fire detections | Free MAP_KEY | FRP data per satellite instrument (optional) |

### Synthetic Injections (Disclosed Honestly, Labelled `is_synthetic=True`)

1. **Collusion ring** — 3 fake commercial providers ("GeoWatch Analytics", "FireScope Pro", "SatGuard Intl") cloning real ECMWF readings with sub-unit noise → demonstrates collusion discounting
2. **Drifting sensor** — "NOAA GOES-16 (degraded)" with progressive calibration bias injection → demonstrates CUSUM drift detection
3. **Lucky streak** — "Orbital Insight (new)" with only 5 perfect observations → demonstrates Wilson LCB bounding

### Honest Disclosure

*"This demonstration harness uses real data from NASA EONET, Open-Meteo (ECMWF + GFS), and Copernicus CAMS Air Quality. Five synthetic sources are deliberately injected to demonstrate the trust engine's failure-mode detection capabilities (collusion, drift, low-sample bounding). All synthetic sources are explicitly flagged in the UI. The architecture is data-source-agnostic and production-portable to live feeds."*

---

## 6. Demo Narrative

Open with the failure mode, not the architecture:

> "Three satellite feeds agree on a wildfire boundary. A naive system says 99% confidence. We show you they're all reselling the same upstream imagery provider — it's one opinion wearing three hats."

Then walk the dashboard live: graph → drill-down → what-if removal → final recommendation with evidence trail. Show the Data Provenance panel — every real data source with its API URL, fetch timestamp, and observation count. Show the "What Would Increase Trust" recommendations. Close by referencing that this class of graph-based, adversarially-aware trust propagation has been stress-tested in a related trust-scoring domain against coordinated attacks, and holds up meaningfully better than naive consensus or unmodified reputation-propagation approaches — which is exactly the failure mode (collusion) this system is built to catch.

---

## 7. Explicit Scope Boundaries (5-day MVP)

**In scope:**
- All four trust-engine layers, functioning correctly on real + synthetic dataset
- Interactive dashboard: graph, drill-down, what-if, recommendation panel
- Data Provenance panel showing real API sources with URLs and timestamps
- "What Would Increase Trust" recommendation panel
- One clear, honest slide on the hybrid real+synthetic data approach

**Out of scope (do not attempt in 5 days):**
- Arbitrary live data source ingestion — cache everything, no live API calls during demo
- Fully configurable/tunable layer parameters in the UI — hardcode good defaults, only expose source-removal as the interactive lever
- User accounts, auth, multi-tenancy — this is a proof of methodology, not a product launch

---

## 8. Deliverables Checklist (per PS7 requirements)

- [x] Problem understanding note (Section 1 above)
- [x] System architecture (Section 3)
- [x] AI/ML methodology (Section 3, layer-by-layer)
- [x] Trust scoring methodology (Section 3 + math detail for each layer)
- [x] Working prototype / proof of concept (dashboard + engine with real data)
- [ ] Demo video (narrative per Section 6)
- [x] Commercialization & scalability roadmap (see `Commercialization_Roadmap.md`)

---

## 9. Honest Risk Assessment

**Strengths:** Methodology is not improvised under time pressure — each layer maps to an established, validated technique. The what-if interactivity is a genuine differentiator most competing teams won't attempt. The counterintuitive collusion-discounting framing gives judges something memorable to latch onto. **Real data from 4+ independent public APIs** (NASA, ECMWF, NOAA, Copernicus) flows through the trust engine, with synthetic injections disclosed honestly.

**Risks:** Execution, not concept. Main failure modes to guard against — (1) demo instability if live API calls fail during presentation (mitigated: all data is cached), (2) the what-if interactivity getting cut under time pressure, since it's carrying a disproportionate share of the scoring weight (Explainability + Demo + Practical Utility = 35%). Protect that feature above all else if time runs short.

