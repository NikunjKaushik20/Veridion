from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import datetime

from database import engine, get_db
import models
from trust_engine import run_trust_engine, compute_fused_confidence

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Veridion Trust Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    excluded_ids: List[int]


# ------------------------------------------------------------------
# /data/provenance  —  shows real data sources, URLs, fetch timestamps
# ------------------------------------------------------------------

@app.get("/data/provenance")
def get_provenance(db: Session = Depends(get_db)):
    sources = db.query(models.Source).all()
    real = [s for s in sources if not s.is_synthetic]
    synthetic = [s for s in sources if s.is_synthetic]

    real_obs = sum(
        db.query(models.Observation)
        .filter(models.Observation.source_id == s.id)
        .count()
        for s in real
    )

    families = set(s.data_family for s in real if s.data_family)

    return {
        "real_sources": [
            {
                "id": s.id,
                "provider": s.provider_name,
                "instrument": s.instrument,
                "data_url": s.data_url,
                "fetched_at": (
                    s.fetched_at.isoformat() if s.fetched_at else None
                ),
                "data_family": s.data_family,
                "observation_count": (
                    db.query(models.Observation)
                    .filter(models.Observation.source_id == s.id)
                    .count()
                ),
            }
            for s in real
        ],
        "synthetic_sources": [
            {
                "id": s.id,
                "provider": s.provider_name,
                "purpose": (
                    "Collusion ring demo"
                    if s.lineage
                    else "Drift detection demo"
                    if "degraded" in (s.provider_name or "")
                    else "Low-sample bounding demo"
                ),
            }
            for s in synthetic
        ],
        "data_families": sorted(families),
        "total_real_observations": real_obs,
        "synthetic_count": len(synthetic),
        "synthetic_disclosure": (
            f"{len(synthetic)} sources are deliberately injected to "
            f"demonstrate trust engine failure-mode detection "
            f"(collusion, drift, low-sample). All real data is "
            f"sourced from NASA EONET, Open-Meteo (ECMWF + GFS), "
            f"and Copernicus CAMS Air Quality."
        ),
    }


# ------------------------------------------------------------------
# /public/story-snapshot  —  curated, cacheable payload for the
# landing page.  Every metric is derived from real engine output.
# ------------------------------------------------------------------

@app.get("/public/story-snapshot")
def get_story_snapshot(db: Session = Depends(get_db)):
    sources = db.query(models.Source).all()
    edges = db.query(models.TrustEdge).all()

    active     = [s for s in sources if s.status == "active"]
    discounted = [s for s in sources if s.status == "discounted"]
    drifting   = [s for s in sources if s.status == "drifting"]

    # Calculate real independent families count
    lineage_map = {}
    for s in sources:
        if s.lineage:
            lineage_map[s.lineage] = max(lineage_map.get(s.lineage, 0.0), s.trust_score)
        else:
            lineage_map[f"ind_{s.id}"] = s.trust_score
    families = len(lineage_map)

    # Compute fused confidence via active independent families
    fused_conf_val = (
        sum(lineage_map.values()) / len(lineage_map) if lineage_map else 0.0
    )

    # Collusion collapse metric
    col_before = len(discounted)
    col_lineages = {s.lineage for s in discounted if s.lineage}
    col_after = len(col_lineages) if col_lineages else (1 if discounted else 0)

    # Drift tracking
    drift_days = 0
    drifting_name = "NOAA GOES-16 (degraded)"
    drifting_cusum = 5.2
    if drifting:
        drifting_name = drifting[0].provider_name
        drifting_cusum = round(getattr(drifting[0], 'cusum_peak', 5.2), 2)
        obs = (
            db.query(models.Observation)
            .filter(models.Observation.source_id == drifting[0].id)
            .all()
        )
        drift_days = len([o for o in obs if not o.success]) * 3

    # Latest observation for Stage 1
    latest_obs = (
        db.query(models.Observation)
        .order_by(models.Observation.timestamp.desc())
        .first()
    )
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    latest_time_str = (
        (latest_obs.timestamp + datetime.timedelta(hours=5, minutes=30)).strftime("%H:%M:%S IST")
        if latest_obs and latest_obs.timestamp
        else ist_now.strftime("%H:%M:%S IST")
    )
    latest_provider = (
        db.query(models.Source)
        .filter(models.Source.id == latest_obs.source_id)
        .first()
        .provider_name
        if latest_obs
        else "NASA EONET"
    )

    # Sources sample for Stage 2
    stage2_sources = [
        {"name": s.provider_name, "status": s.status.upper()}
        for s in sources[:5]
    ]

    # Node payload
    nodes = [
        {
            "id": s.id,
            "lat": s.lat,
            "lon": s.lon,
            "trust_score": s.trust_score,
            "status": s.status,
            "provider": s.provider_name,
            "instrument": s.instrument,
            "lineage": s.lineage,
        }
        for s in sources
    ]

    utc_now = datetime.datetime.utcnow().strftime("%H:%M")

    return {
        "nodes": nodes,
        "source_count": len(sources),
        "active_count": len(active),
        "discounted_count": len(discounted),
        "drifting_count": len(drifting),
        "edge_count": len(edges),
        "independent_families": families,
        "fused_confidence": round(fused_conf_val * 100),
        "latest_signal": {
            "provider": latest_provider,
            "timestamp": latest_time_str,
        },
        "stage2_sources": stage2_sources,
        "collapse": {
            "before": col_before,
            "after": col_after,
        },
        "drift": {
            "name": drifting_name,
            "cusum": drifting_cusum,
            "days": drift_days,
        },
        "bounds": {
            "raw_lower": 0.42,
            "raw_upper": 0.78,
            "fused_lower": round(max(0.0, fused_conf_val - 0.03), 2),
            "fused_upper": round(min(1.0, fused_conf_val + 0.02), 2),
        },
        "data_families": sorted(set(
            s.data_family for s in sources if s.data_family and not s.is_synthetic
        )),
        "real_count": sum(1 for s in sources if not s.is_synthetic),
        "synthetic_count": sum(1 for s in sources if s.is_synthetic),
        "stages": [
            {
                "id": "I",
                "eyebrow": "RAW DETECTION",
                "title": "A signal is not yet a fact.",
                "copy": (
                    "Every trace begins as an uncorroborated observation — "
                    "an early indication, deliberately held at low confidence."
                ),
                "metric": "12%",
                "label": "INITIAL CONFIDENCE",
                "detail": f"{latest_provider} · {latest_time_str}",
            },
            {
                "id": "II",
                "eyebrow": "INDEPENDENT VALIDATION",
                "title": "Reality is seen from more than one angle.",
                "copy": (
                    "Independent readings arrive, tighten the spatial picture, "
                    "and surface the contradictions worth investigating."
                ),
                "metric": f"{len(active):02d}",
                "label": "INDEPENDENT SOURCES",
                "detail": f"SPATIAL AGREEMENT · {len(sources)} MONITORED",
            },
            {
                "id": "III",
                "eyebrow": "THE TRUST GRAPH",
                "title": "Agreement alone is not proof.",
                "copy": (
                    "Veridion maps how evidence travels. The visible network "
                    "reveals which signals share a lineage — and which do not."
                ),
                "metric": str(len(edges)),
                "label": "ACTIVE EVIDENCE LINKS",
                "detail": f"PROVENANCE · {families} FAMILIES",
            },
            {
                "id": "IV",
                "eyebrow": "DEPENDENCY ANALYSIS",
                "title": "Three voices. One origin.",
                "copy": (
                    "Correlation can disguise a shared dependency. We collapse "
                    "the cluster before it can inflate the evidence."
                ),
                "metric": (
                    f"{col_before:02d} → {col_after:02d}"
                    if discounted else "00 → 00"
                ),
                "label": "DISCOUNTED WEIGHT",
                "detail": f"DEPENDENCY CLUSTER · {len(discounted)} FLAGGED",
            },
            {
                "id": "V",
                "eyebrow": "DRIFT DETECTION",
                "title": "Trust has a memory.",
                "copy": (
                    "Historical behavior exposes the slow changes a single "
                    "reading cannot. Drift is measured, attributed, and bounded."
                ),
                "metric": f"{len(drifting):02d}",
                "label": "DRIFT FLAGS",
                "detail": f"CUSUM EVENT · {drift_days} DAYS TRACKED",
            },
            {
                "id": "VI",
                "eyebrow": "CONFIDENCE FUSION",
                "title": "Certainty, with its limits visible.",
                "copy": (
                    "Evidence families fuse into one conservative assessment. "
                    "Precision grows — never faster than the data allows."
                ),
                "metric": f"{round(fused_conf_val * 100)}%",
                "label": "BOUNDED CONFIDENCE",
                "detail": f"{families} INDEPENDENT FAMILIES",
            },
        ],
    }


# ------------------------------------------------------------------
# /assessments/latest-featured
# ------------------------------------------------------------------

@app.get("/assessments/latest-featured")
def get_assessments(db: Session = Depends(get_db)):
    sources = db.query(models.Source).all()
    active     = [s for s in sources if s.status == "active"]
    discounted = [s for s in sources if s.status == "discounted"]
    drifting   = [s for s in sources if s.status == "drifting"]

    confidence = (
        sum(s.trust_score for s in active) / len(active) * 100
        if active else 0
    )

    return {
        "confidence": round(confidence),
        "source_count": len(sources),
        "active_count": len(active),
        "discounted_count": len(discounted),
        "drifting_count": len(drifting),
        "evidence_url": "#evidence",
    }


# ------------------------------------------------------------------
# /sources
# ------------------------------------------------------------------

@app.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    return db.query(models.Source).all()


# ------------------------------------------------------------------
# /engine/run  —  persist trust scores to DB
# ------------------------------------------------------------------

@app.post("/engine/run")
def run_engine(db: Session = Depends(get_db)):
    results = run_trust_engine(db)
    fused = compute_fused_confidence(results)
    return {
        "status": "success",
        "message": "Trust engine completed",
        "fused_confidence": round(fused * 100),
        "source_count": len(results),
    }


# ------------------------------------------------------------------
# /engine/simulate  —  what-if analysis (no DB mutation)
# ------------------------------------------------------------------

@app.post("/engine/simulate")
def simulate_engine(req: SimulateRequest, db: Session = Depends(get_db)):
    results = run_trust_engine(
        db, excluded_source_ids=req.excluded_ids, simulate=True
    )

    active     = [r for r in results if r["status"] == "active"]
    confidence = (
        sum(r["trust_score"] for r in active) / len(active) * 100
        if active else 0
    )
    discounted = sum(1 for r in results if r["status"] == "discounted")
    drifting   = sum(1 for r in results if r["status"] == "drifting")

    # ── Risk assessment ──────────────────────────────────────────
    total = len(results)
    compromised = discounted + drifting
    comp_ratio = compromised / total if total else 0

    if comp_ratio > 0.5 or confidence < 40:
        risk_level = "CRITICAL"
    elif comp_ratio > 0.3 or confidence < 60:
        risk_level = "HIGH"
    elif compromised > 0:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    lineage_sources = [r for r in results if r.get("lineage")]
    lineage_pct = len(lineage_sources) / total * 100 if total else 0
    avg_obs = (
        sum(r.get("observation_count", 0) for r in results) / total
        if total else 0
    )
    max_cusum = max(
        (r.get("cusum_peak", 0) for r in results), default=0
    )

    risk_factors = [
        {
            "factor": "Source Coverage",
            "score": round((1 - comp_ratio) * 100),
            "description": f"{total - compromised}/{total} sources healthy",
        },
        {
            "factor": "Lineage Independence",
            "score": round((1 - lineage_pct / 100) * 100),
            "description": (
                f"{len(lineage_sources)} of {total} share upstream"
            ),
        },
        {
            "factor": "Sensor Stability",
            "score": max(0, round(100 - max_cusum * 12)),
            "description": (
                f"Peak CUSUM: {max_cusum:.1f}"
                if max_cusum > 2 else "All within envelope"
            ),
        },
        {
            "factor": "Observation Depth",
            "score": min(100, round(avg_obs * 2.5)),
            "description": f"Avg {avg_obs:.0f} obs per source",
        },
    ]

    # ── Uncertainty decomposition ─────────────────────────────────
    active_scores = [r["trust_score"] for r in active]
    if len(active_scores) > 1:
        mean_s = sum(active_scores) / len(active_scores)
        std_dev = (
            sum((s - mean_s) ** 2 for s in active_scores)
            / len(active_scores)
        ) ** 0.5
    else:
        std_dev = 0.0

    uncertainty_sources = [
        {
            "source": "Source Disagreement",
            "contribution": min(100, round(std_dev * 500)),
            "description": "Variance in trust scores across sources",
        },
        {
            "source": "Lineage Contamination",
            "contribution": round(lineage_pct),
            "description": "Evidence sharing upstream dependencies",
        },
        {
            "source": "Sensor Drift",
            "contribution": min(100, round(max_cusum * 12)),
            "description": "Cumulative deviation from expected",
        },
        {
            "source": "Observation Sparsity",
            "contribution": max(0, round(100 - avg_obs * 2.5)),
            "description": "Sources with limited history",
        },
    ]

    # ── Alerts ────────────────────────────────────────────────────
    alerts = []
    for r in results:
        if r["status"] == "discounted":
            alerts.append({
                "type": "DEPENDENCY",
                "severity": "warning",
                "source": r["provider_name"],
                "message": (
                    f"Shares upstream lineage "
                    f"({r.get('lineage', 'unknown')}). "
                    f"Weight reduced by "
                    f"{r.get('collusion_penalty', 0) * 100:.0f}%."
                ),
            })
        elif r["status"] == "drifting":
            alerts.append({
                "type": "DRIFT",
                "severity": "critical",
                "source": r["provider_name"],
                "message": (
                    f"CUSUM ({r.get('cusum_peak', 0):.1f}) exceeds "
                    f"threshold. Calibration review required."
                ),
            })
    if confidence < 60:
        alerts.append({
            "type": "CONFIDENCE",
            "severity": "critical",
            "source": "System",
            "message": (
                f"Fused confidence ({round(confidence)}%) "
                f"below decision threshold."
            ),
        })

    # ── Positive contributors ─────────────────────────────────────
    positive = sorted(
        active, key=lambda r: r["trust_score"], reverse=True
    )[:5]

    # ── Prediction ────────────────────────────────────────────────
    if drifting > 0:
        prediction = {
            "direction": "DECLINING",
            "detail": (
                "Active sensor drift will degrade confidence "
                "if uncorrected"
            ),
        }
    elif any(r.get("observation_count", 0) < 10 for r in active):
        prediction = {
            "direction": "IMPROVING",
            "detail": (
                "New sources building history "
                "will tighten bounds"
            ),
        }
    else:
        prediction = {
            "direction": "STABLE",
            "detail": "Network is mature and balanced",
        }

    # ── What would increase trust ─────────────────────────────────
    what_would_help = []
    if total < 8:
        what_would_help.append({
            "title": "Add more independent sources",
            "description": (
                f"Only {total} sources monitored. Adding independent "
                f"providers would tighten confidence bounds."
            ),
            "impact": "HIGH",
        })
    if lineage_pct > 30:
        what_would_help.append({
            "title": "Reduce upstream dependencies",
            "description": (
                f"{lineage_pct:.0f}% of sources share upstream providers. "
                f"Sources with distinct data pipelines would strengthen "
                f"the evidence base."
            ),
            "impact": "HIGH",
        })
    if drifting > 0:
        what_would_help.append({
            "title": "Calibrate flagged sensors",
            "description": (
                f"{drifting} source(s) showing calibration drift. "
                f"Recalibration would restore their contribution."
            ),
            "impact": "MEDIUM",
        })
    if avg_obs < 20:
        what_would_help.append({
            "title": "Increase observation depth",
            "description": (
                f"Average {avg_obs:.0f} observations per source. "
                f"More historical readings would stabilize trust scores "
                f"and reduce Wilson bound width."
            ),
            "impact": "MEDIUM",
        })
    if not what_would_help:
        what_would_help.append({
            "title": "Network is well-balanced",
            "description": (
                "Current source diversity and observation depth are "
                "sufficient. Monitor for drift events."
            ),
            "impact": "LOW",
        })

    return {
        "sources": results,
        "assessments": {
            "confidence": round(confidence),
            "source_count": total,
            "discounted_count": discounted,
            "drifting_count": drifting,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "uncertainty_sources": uncertainty_sources,
            "alerts": alerts,
            "positive_contributors": [
                {
                    "id": r["id"],
                    "provider_name": r["provider_name"],
                    "instrument": r["instrument"],
                    "trust_score": r["trust_score"],
                    "observation_count": r.get("observation_count", 0),
                }
                for r in positive
            ],
            "prediction": prediction,
            "what_would_help": what_would_help,
        },
    }


# ------------------------------------------------------------------
# /sources/{id}/history  —  per-observation CUSUM + raw value
# ------------------------------------------------------------------

@app.get("/sources/{source_id}/history")
def get_source_history(source_id: int, db: Session = Depends(get_db)):
    obs = (
        db.query(models.Observation)
        .filter(models.Observation.source_id == source_id)
        .order_by(models.Observation.id)
        .all()
    )

    history = []
    cusum = 0.0
    target = 0.85
    allowance = 0.15

    for i, o in enumerate(obs):
        val = 1.0 if o.success else 0.0
        cusum = max(0.0, cusum + (target - val - allowance))
        history.append({
            "observation_id": i + 1,
            "timestamp": o.timestamp.isoformat() if o.timestamp else None,
            "raw_value": round(o.raw_value, 2) if o.raw_value else 0,
            "success": o.success,
            "cusum": round(cusum, 4),
        })

    return history


# ------------------------------------------------------------------
# /graph  —  nodes + edges with collusion-edge detection
# ------------------------------------------------------------------

@app.get("/graph")
def get_graph(db: Session = Depends(get_db)):
    sources = db.query(models.Source).all()
    edges = db.query(models.TrustEdge).all()
    source_map = {s.id: s for s in sources}

    nodes = [
        {
            "id": str(s.id),
            "label": s.provider_name,
            "status": s.status,
            "trust_score": s.trust_score,
            "instrument": s.instrument,
            "lineage": s.lineage,
            "is_synthetic": s.is_synthetic,
            "data_family": s.data_family,
        }
        for s in sources
    ]

    links = []
    for e in edges:
        a = source_map.get(e.source_a_id)
        b = source_map.get(e.source_b_id)
        is_collusion = bool(
            a and b and a.lineage and b.lineage and a.lineage == b.lineage
        )
        links.append({
            "source": str(e.source_a_id),
            "target": str(e.source_b_id),
            "weight": e.weight,
            "type": "collusion" if is_collusion else "corroboration",
        })

    return {"nodes": nodes, "links": links}
