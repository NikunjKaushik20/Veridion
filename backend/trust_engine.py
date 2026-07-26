import numpy as np
from scipy.stats import beta as beta_dist
import networkx as nx
from sqlalchemy.orm import Session
from models import Source, Observation, TrustEdge
from collections import defaultdict


def compute_fused_confidence(results):
    """
    Independent-family fusion.

    Collusion-discounted sources sharing a lineage are collapsed into one
    family.  Every un-discounted source is its own family.  Returns the
    mean of the best trust score per family — conservative and explainable.
    """
    families: dict[str, float] = {}

    for r in results:
        if r.get("status") == "excluded":
            continue

        if r["collusion_penalty"] > 0.3 and r.get("lineage"):
            key = f"dep_{r['lineage']}"
        elif r["collusion_penalty"] > 0.3:
            key = f"dep_co_{r['id']}"
        else:
            key = f"ind_{r['id']}"

        families[key] = max(families.get(key, 0.0), r["trust_score"])

    if not families:
        return 0.0

    return sum(families.values()) / len(families)


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def run_trust_engine(db: Session, excluded_source_ids=None, simulate=False):
    if excluded_source_ids is None:
        excluded_source_ids = []

    all_sources = db.query(Source).all()
    if not all_sources:
        return []

    sources = [s for s in all_sources if s.id not in excluded_source_ids]
    if not sources:
        return []

    source_ids = {s.id for s in sources}

    # Pre-fetch observations once per source
    obs_cache: dict[int, list[Observation]] = {}
    for s in sources:
        obs_cache[s.id] = (
            db.query(Observation)
            .filter(Observation.source_id == s.id)
            .order_by(Observation.id)
            .all()
        )

    # ==================================================================
    # LAYER 1 — Bayesian Lower Confidence Bound (Wilson-style)
    #
    # Prevents new / low-sample sources from earning high trust off a
    # short lucky streak.  A source with 5/5 successes gets LCB ≈ 0.57,
    # not 1.0.  One with 27/30 gets ≈ 0.78.
    # ==================================================================

    lcb_scores: dict[int, float] = {}
    obs_rates: dict[int, float] = {}

    for s in sources:
        obs = obs_cache[s.id]
        n = len(obs)
        successes = sum(1 for o in obs if o.success)
        failures = n - successes

        # Uninformative Beta(1,1) prior
        a_post = 1 + successes
        b_post = 1 + failures

        lcb = float(beta_dist.ppf(0.05, a_post, b_post))
        lcb_scores[s.id] = lcb
        obs_rates[s.id] = successes / n if n > 0 else 0.0

    # ==================================================================
    # LAYER 2 — Trust Graph (Personalized PageRank)
    #
    # Sources as nodes, corroboration edges weighted by spatial overlap.
    # Personalized toward high-observation, high-success anchors to avoid
    # the circularity / bootstrapping failure of vanilla PageRank.
    # ==================================================================

    edges = db.query(TrustEdge).all()
    G = nx.DiGraph()
    for s in sources:
        G.add_node(s.id)
    for e in edges:
        if e.source_a_id in source_ids and e.source_b_id in source_ids:
            G.add_edge(e.source_a_id, e.source_b_id, weight=e.weight)
            G.add_edge(e.source_b_id, e.source_a_id, weight=e.weight)

    # Personalization vector — bias toward established, reliable sources
    obs_counts = {s.id: len(obs_cache[s.id]) for s in sources}
    max_obs = max(obs_counts.values()) if obs_counts else 1
    personalization = {
        s.id: (obs_counts[s.id] / max_obs) * obs_rates.get(s.id, 0.5)
        for s in sources
    }
    p_total = sum(personalization.values())
    if p_total > 0:
        personalization = {k: v / p_total for k, v in personalization.items()}

    try:
        ppr = nx.pagerank(
            G, alpha=0.85, personalization=personalization, weight="weight"
        )
    except Exception:
        ppr = {s.id: 1.0 / len(sources) for s in sources}

    # Normalize to [0, 1]
    ppr_vals = list(ppr.values())
    ppr_max, ppr_min = max(ppr_vals), min(ppr_vals)
    if ppr_max != ppr_min:
        norm_ppr = {k: (v - ppr_min) / (ppr_max - ppr_min) for k, v in ppr.items()}
    else:
        norm_ppr = {k: 0.5 for k in ppr}

    # ==================================================================
    # LAYER 3 — Drift Detection (CUSUM / Page-Hinkley)
    #
    # Cumulative-sum control chart on binary success with a one-sided
    # upward test.  target = 0.85, allowance k = 0.15.  Penalty ramps
    # smoothly between a detection threshold and a severe level.
    # ==================================================================

    drift_scores: dict[int, float] = {}
    cusum_peaks: dict[int, float] = {}

    for s in sources:
        obs = obs_cache[s.id]
        if len(obs) < 5:
            drift_scores[s.id] = 0.0
            cusum_peaks[s.id] = 0.0
            continue

        target = 0.85
        allowance = 0.15
        cusum = 0.0
        peak = 0.0

        for o in obs:
            val = 1.0 if o.success else 0.0
            cusum = max(0.0, cusum + (target - val - allowance))
            peak = max(peak, cusum)

        cusum_peaks[s.id] = round(peak, 4)

        threshold = 2.0
        severe = 5.0
        if peak > threshold:
            drift_scores[s.id] = min(1.0, (peak - threshold) / (severe - threshold))
        else:
            drift_scores[s.id] = 0.0

    # ==================================================================
    # LAYER 4 — Collusion / Dependency Discounting
    #
    # Two detection methods:
    #   (a) Declared lineage — sources that share a non-null `lineage`
    #       value are immediately grouped.
    #   (b) Observation co-movement — for undeclared dependencies,
    #       pairwise Pearson correlation on raw_value time series.
    #       r > 0.95 → suspiciously high → moderate penalty.
    # ==================================================================

    collusion_penalties: dict[int, float] = {s.id: 0.0 for s in sources}
    source_map = {s.id: s for s in sources}

    # (a) Lineage-based grouping
    lineage_groups: dict[str, list[int]] = defaultdict(list)
    for s in sources:
        if s.lineage:
            lineage_groups[s.lineage].append(s.id)

    for _lineage, members in lineage_groups.items():
        if len(members) >= 2:
            # N dependent sources should count as ≈1 independent source
            penalty = 1.0 - (1.0 / len(members))
            for sid in members:
                collusion_penalties[sid] = max(collusion_penalties[sid], penalty)

    # (b) Behavioural co-movement (for undeclared dependencies)
    ts_vectors: dict[int, np.ndarray] = {}
    for s in sources:
        obs = obs_cache[s.id]
        if len(obs) >= 10 and collusion_penalties[s.id] == 0:
            ts_vectors[s.id] = np.array([o.raw_value for o in obs])

    checked = list(ts_vectors.keys())
    for i, a_id in enumerate(checked):
        for b_id in checked[i + 1:]:
            # Same data_family = expected agreement, not collusion
            a_fam = getattr(source_map[a_id], "data_family", None)
            b_fam = getattr(source_map[b_id], "data_family", None)
            if a_fam and b_fam and a_fam == b_fam:
                continue
            min_len = min(len(ts_vectors[a_id]), len(ts_vectors[b_id]))
            if min_len < 8:
                continue
            arr_a = ts_vectors[a_id][:min_len]
            arr_b = ts_vectors[b_id][:min_len]
            if np.std(arr_a) > 1e-6 and np.std(arr_b) > 1e-6:
                corr = float(np.corrcoef(arr_a, arr_b)[0, 1])
                if corr > 0.95:
                    for sid in (a_id, b_id):
                        collusion_penalties[sid] = max(collusion_penalties[sid], 0.5)

    # ==================================================================
    # FUSION — multiplicative penalty model
    #
    #   base  = LCB × 0.45  +  PPR × 0.30  +  obs_rate × 0.25
    #   final = base  ×  (1 − drift × 0.70)  ×  (1 − collusion × 0.60)
    #
    # Multiplicative so a 0.6 collusion penalty reduces the base by 36 %,
    # not by a fixed 0.36 subtracted from a number that might already be
    # small.  Keeps scores in a meaningful range for every source type.
    # ==================================================================

    results = []
    for s in sources:
        lcb       = lcb_scores.get(s.id, 0.5)
        ppr_s     = norm_ppr.get(s.id, 0.5)
        drift     = drift_scores.get(s.id, 0.0)
        collusion = collusion_penalties.get(s.id, 0.0)
        rate      = obs_rates.get(s.id, 0.5)
        n_obs     = len(obs_cache.get(s.id, []))

        base = lcb * 0.45 + ppr_s * 0.30 + rate * 0.25

        drift_mult     = 1.0 - drift * 0.70       # max 70 % reduction
        collusion_mult = 1.0 - collusion * 0.60    # max 60 % reduction

        score = max(0.01, min(0.99, base * drift_mult * collusion_mult))

        # Status — collusion overrides drift if both present
        status = "active"
        if drift > 0.3:
            status = "drifting"
        if collusion > 0.3:
            status = "discounted"

        # Persist only in non-simulation mode
        if not simulate:
            s.trust_score = score
            s.status = status

        # Human-readable evidence trail
        parts = [f"LCB({n_obs} obs)={lcb:.3f}"]
        parts.append(f"PPR={ppr_s:.3f}")
        if drift > 0:
            parts.append(f"CUSUM={cusum_peaks.get(s.id, 0):.2f}")
        if collusion > 0:
            tag = s.lineage or "co-movement"
            parts.append(f"DEP={tag}")

        if status == "discounted":
            evidence = (
                f"{s.provider_name} discounted — shares upstream dependency "
                f"({s.lineage or 'behavioral correlation'}). "
                + " | ".join(parts)
            )
        elif status == "drifting":
            evidence = (
                f"{s.provider_name} flagged — calibration drift detected "
                f"(CUSUM alert). " + " | ".join(parts)
            )
        else:
            evidence = (
                f"{s.provider_name} active — trust {score * 100:.1f}%. "
                + " | ".join(parts)
            )

        results.append({
            "id": s.id,
            "provider_name": s.provider_name,
            "instrument": s.instrument,
            "lat": s.lat,
            "lon": s.lon,
            "status": status,
            "trust_score": score,
            "evidence": evidence,
            "lineage": s.lineage,
            "is_synthetic": s.is_synthetic if hasattr(s, 'is_synthetic') else False,
            "data_family": s.data_family if hasattr(s, 'data_family') else None,
            "lcb": round(lcb, 4),
            "ppr": round(ppr_s, 4),
            "drift_penalty": round(drift, 4),
            "collusion_penalty": round(collusion, 4),
            "observation_count": n_obs,
            "cusum_peak": cusum_peaks.get(s.id, 0.0),
        })

    if not simulate:
        db.commit()

    return results
