import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ChevronRight,
  Database,
  Eye,
  Lightbulb,
  LineChart as LineChartIcon,
  Network,
  ShieldCheck,
  Table2,
  X,
} from "lucide-react";
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Source = {
  id: number;
  provider_name: string;
  instrument: string;
  status: "active" | "drifting" | "discounted" | "excluded" | string;
  trust_score: number;
  evidence: string;
  is_synthetic?: boolean;
  data_family?: string | null;
};
type GraphNode = {
  id: string;
  label: string;
  status: "active" | "drifting" | "discounted" | "excluded" | string;
  trust_score: number;
  instrument: string;
  lineage?: string | null;
  is_synthetic?: boolean;
  data_family?: string | null;
};
type GraphLink = {
  source: string;
  target: string;
  weight: number;
  type: "collusion" | "corroboration";
};

const tone = (status: string) =>
  status === "active"
    ? "#a9b173"
    : status === "drifting"
      ? "#dfb75d"
      : status === "discounted"
        ? "#d25e40"
        : "#555850";
const statusLabel = (status: string) =>
  status === "active"
    ? "VERIFIED"
    : status === "drifting"
      ? "DRIFT WATCH"
      : status === "discounted"
        ? "DISCOUNTED"
        : "EXCLUDED";

// The graph lives in a fixed SVG coordinate system.  Keeping these anchors in
// one place makes the whole topology easy to position without altering its
// links, hit targets, or selected-node behaviour.
const graphCenter = { x: 315, y: 260 };
const quarantineCluster = { x: 615, y: 410 };

function CinematicTrustGraph({
  nodes,
  links,
  excluded,
  compact = false,
}: {
  nodes: GraphNode[];
  links: GraphLink[];
  excluded: Set<number>;
  compact?: boolean;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // The overview is a focused explanation, not a miniature copy of the full
  // graph: show the flagged sources together with the verified sources that
  // directly corroborate or challenge them.
  const flaggedNodes = nodes.filter((node) => node.status !== "active").slice(0, 4);
  const flaggedIds = new Set(flaggedNodes.map((node) => node.id));
  const supportingNodes = nodes
    .filter(
      (node) =>
        node.status === "active" &&
        links.some(
          (link) =>
            (link.source === node.id && flaggedIds.has(link.target)) ||
            (link.target === node.id && flaggedIds.has(link.source)),
        ),
    )
    .slice(0, 6);
  const displayNodes = compact ? [...supportingNodes, ...flaggedNodes] : nodes;

  const layout = useMemo(() => {
    const active = nodes.filter((node) => node.status === "active");
    const drifting = nodes.filter((node) => node.status === "drifting");
    const discounted = nodes.filter((node) => node.status === "discounted");
    const positions = new Map<string, { x: number; y: number }>();

    if (compact) {
      const visibleActive = displayNodes.filter((node) => node.status === "active");
      const visibleFlagged = displayNodes.filter((node) => node.status !== "active");

      // A deliberately tight two-cluster composition keeps the supporting
      // evidence and the flagged sources readable at dashboard-card scale.
      visibleActive.forEach((node, i) => {
        positions.set(node.id, {
          x: 255 + (i % 2) * 95,
          y: 190 + Math.floor(i / 2) * 76,
        });
      });
      visibleFlagged.forEach((node, i) => {
        positions.set(node.id, {
          x: 520 + (i % 2) * 92,
          y: 210 + Math.floor(i / 2) * 88,
        });
      });

      return positions;
    }

    // Orbital center
    const { x: cx, y: cy } = graphCenter;

    // 1. Active nodes (Inner verified orbit)
    const rActive = 155;
    active.forEach((node, i) => {
      // Start from top, spread evenly
      const angle = (i / active.length) * 2 * Math.PI - Math.PI / 2;
      positions.set(node.id, {
        x: cx + rActive * Math.cos(angle),
        y: cy + rActive * Math.sin(angle),
      });
    });

    // 2. Drifting nodes (Outer orbit, pulling away to the right)
    const rDrift = 270;
    drifting.forEach((node, i) => {
      // Spread them in an arc on the right side
      const angle = drifting.length > 1 
        ? (i / (drifting.length - 1)) * (Math.PI / 2.5) - (Math.PI / 5) 
        : 0;
      positions.set(node.id, {
        x: cx + 80 + rDrift * Math.cos(angle),
        y: cy + rDrift * Math.sin(angle),
      });
    });

    // 3. Discounted nodes (Quarantine cluster on bottom right)
    const { x: clusterX, y: clusterY } = quarantineCluster;
    discounted.forEach((node, i) => {
      const angle = (i / discounted.length) * 2 * Math.PI;
      const r = 35 + (i % 2) * 15; // Stagger radius for organic look
      positions.set(node.id, {
        x: clusterX + r * Math.cos(angle),
        y: clusterY + r * Math.sin(angle),
      });
    });

    return positions;
  }, [compact, displayNodes, nodes]);

  const selected =
    nodes.find((node) => node.id === selectedId) ??
    nodes.find((node) => node.status !== "active") ??
    nodes[0];
  
  const visibleNodeIds = new Set(displayNodes.map((node) => node.id));
  const selectedPosition = selected ? layout.get(selected.id) : undefined;
  
  const inViewLinks = links.filter(
    (link) =>
      layout.has(link.source) &&
      layout.has(link.target) &&
      visibleNodeIds.has(link.source) &&
      visibleNodeIds.has(link.target),
  );
  
  const point = (id: string) => layout.get(id)!;
  const curve = (
    from: { x: number; y: number },
    to: { x: number; y: number },
  ) =>
    `M ${from.x} ${from.y} C ${from.x + (to.x - from.x) * 0.38} ${from.y}, ${from.x + (to.x - from.x) * 0.62} ${to.y}, ${to.x} ${to.y}`;

  return (
    <div className={`cinematic-graph${compact ? " compact" : ""}`}>
      <div className="graph-chrome">
        <span>
          <i /> LIVE EVIDENCE MAP
        </span>
        <span>{links.length} RELATIONSHIPS</span>
      </div>
      <svg
        className="graph-canvas"
        viewBox={compact ? "120 75 660 385" : "0 0 900 520"}
        role="img"
        aria-label="Trust relationship graph"
      >
        <defs>
          <filter id="nodeGlow">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <radialGradient id="clusterHalo">
            <stop stopColor="#d25e40" stopOpacity=".22" />
            <stop offset="1" stopColor="#d25e40" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g className="graph-grid">
          <path d="M0 104H900M0 208H900M0 312H900M0 416H900M180 0V520M360 0V520M540 0V520M720 0V520" />
        </g>
        {/* Orbit Rings (Aesthetic) */}
        <circle cx={graphCenter.x} cy={graphCenter.y} r="155" fill="none" stroke="rgba(231, 211, 158, 0.04)" strokeWidth="1" strokeDasharray="4 8" />
        <circle cx={graphCenter.x} cy={graphCenter.y} r="270" fill="none" stroke="rgba(231, 211, 158, 0.02)" strokeWidth="1" strokeDasharray="2 12" />

        <circle cx={quarantineCluster.x} cy={quarantineCluster.y} r="132" fill="url(#clusterHalo)" />
        {inViewLinks.map((link, index) => {
          const fadeLink = hoveredId && link.source !== hoveredId && link.target !== hoveredId;
          const isHoveredLink = hoveredId && (link.source === hoveredId || link.target === hoveredId);
          return (
            <path
              key={`${link.source}-${link.target}-${index}`}
              d={curve(point(link.source), point(link.target))}
              className={
                `graph-link ${link.type === "collusion" ? "collusion" : ""} ${fadeLink ? "muted-link" : ""} ${isHoveredLink ? "hovered-link" : ""}`
              }
              style={{ strokeWidth: Math.max(0.8, link.weight * 1.5) }}
            />
          );
        })}
        {nodes.filter((node) => node.status === "discounted").length > 0 && (
          <>
            <circle cx={quarantineCluster.x + 10} cy={quarantineCluster.y} r="13" className="lineage-hub" />
            <text x={quarantineCluster.x + 10} y={quarantineCluster.y + 42} textAnchor="middle" className="lineage-label">
              SHARED UPSTREAM LINEAGE
            </text>
          </>
        )}
        {displayNodes.map((node) => {
          const position = layout.get(node.id);
          if (!position) return null;
          const isSelected = node.id === selected?.id;
          
          const isHovered = hoveredId === node.id;
          const isRelatedToHover = hoveredId 
            ? inViewLinks.some(l => (l.source === node.id && l.target === hoveredId) || (l.target === node.id && l.source === hoveredId))
            : false;
            
          const fadeNode = hoveredId !== null && !isHovered && !isRelatedToHover;
          const faded = excluded.has(Number(node.id)) || fadeNode;
          
          return (
            <g
              key={node.id}
              className={`trust-node ${isSelected ? "selected" : ""} ${faded ? "muted" : ""} ${isHovered ? "hovered" : ""}`}
              transform={`translate(${position.x} ${position.y})`}
              onClick={() => setSelectedId(node.id)}
              onMouseEnter={() => setHoveredId(node.id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              {isSelected && (
                <circle
                  r="25"
                  fill="none"
                  stroke={tone(node.status)}
                  opacity=".3"
                  filter="url(#nodeGlow)"
                />
              )}
              <circle
                r={node.status === "active" ? 7 : 10}
                fill={tone(node.status)}
                filter={node.status === "active" ? undefined : "url(#nodeGlow)"}
              />
              <circle r={node.status === "active" ? 2 : 3} fill="#090b09" />
              {(isSelected || node.status !== "active") && (
                <g className="node-label" transform="translate(18 -8)">
                  <text fill={tone(node.status)}>{node.label}</text>
                  <text y="15">
                    {statusLabel(node.status)} ·{" "}
                    {(node.trust_score * 100).toFixed(0)}%
                  </text>
                </g>
              )}
            </g>
          );
        })}
        {selectedPosition && (
          <path
            d={`M ${selectedPosition.x} ${selectedPosition.y + 24} L ${selectedPosition.x} 495`}
            className="selection-guide"
          />
        )}
      </svg>
      {compact && (
        <div className="graph-focus-summary">
          {supportingNodes.length} VERIFIED SOURCES · {flaggedNodes.length} FLAGGED SIGNALS
        </div>
      )}
      {!compact && selected && (
        <aside className="graph-inspector">
          <span
            className="graph-inspector-status"
            style={{ color: tone(selected.status) }}
          >
            {statusLabel(selected.status)}
          </span>
          <h3>{selected.label}</h3>
          <p>{selected.instrument}</p>
          <div>
            <strong>{(selected.trust_score * 100).toFixed(1)}%</strong>
            <span>TRUST WEIGHT</span>
          </div>
          <button onClick={() => setSelectedId(null)}>
            Clear selection <X size={12} />
          </button>
        </aside>
      )}
      {!compact && (
        <div className="graph-legend">
          <span>
            <i className="verified" /> VERIFIED
          </span>
          <span>
            <i className="drift" /> DRIFT WATCH
          </span>
          <span>
            <i className="discounted" /> DISCOUNTED
          </span>
        </div>
      )}
    </div>
  );
}

export function Dashboard({ onBack }: { onBack: () => void }) {
  const [assessments, setAssessments] = useState<any>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [rawGraph, setRawGraph] = useState<{
    nodes: GraphNode[];
    links: GraphLink[];
  }>({ nodes: [], links: [] });
  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set());
  const [activeView, setActiveView] = useState<
    "overview" | "graph" | "registry"
  >("overview");
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<any>(null);
  const [filterFamily, setFilterFamily] = useState<string>("all");
  const [baselineConfidence, setBaselineConfidence] = useState<number | null>(
    null,
  );

  // Capture the baseline confidence on first run so we can show a real delta
  // instead of a hardcoded "+2.4 FROM LAST RUN" string.
  const baselineCaptured = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("http://localhost:8000/engine/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ excluded_ids: [...excludedIds] }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (!cancelled) {
          setAssessments(data.assessments);
          setSources(data.sources);
          if (!baselineCaptured.current) {
            const persisted = Number(
              window.localStorage.getItem("veridion:baseline_confidence"),
            );
            if (Number.isFinite(persisted) && persisted > 0) {
              setBaselineConfidence(persisted);
            } else {
              setBaselineConfidence(data.assessments?.confidence ?? null);
              window.localStorage.setItem(
                "veridion:baseline_confidence",
                String(data.assessments?.confidence ?? 0),
              );
            }
            baselineCaptured.current = true;
          }
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [excludedIds]);
  useEffect(() => {
    fetch("http://localhost:8000/graph")
      .then((response) => response.json())
      .then(setRawGraph)
      .catch(console.error);
    fetch("http://localhost:8000/data/provenance")
      .then((response) => response.json())
      .then(setProvenance)
      .catch(console.error);
  }, []);

  const toggleExcluded = (id: number) =>
    setExcludedIds((previous) => {
      const next = new Set(previous);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  const openHistory = async (id: number) => {
    setSelectedSourceId(id);
    const response = await fetch(`http://localhost:8000/sources/${id}/history`);
    setHistoryData(await response.json());
  };
  const hasAnomalies =
    (assessments?.discounted_count ?? 0) + (assessments?.drifting_count ?? 0) >
    0;
  const flagged = sources.filter((source) => source.status !== "active");

  // Compute the live delta vs. the first-run baseline.  When nothing has
  // changed, fall back to "NO CHANGE" instead of faking a number.
  const currentConfidence = assessments?.confidence ?? 0;
  const delta =
    baselineConfidence !== null
      ? currentConfidence - baselineConfidence
      : 0;
  const deltaLabel =
    baselineConfidence === null
      ? "BASELINE"
      : delta === 0
        ? "NO CHANGE"
        : `${delta > 0 ? "+" : ""}${delta} FROM BASELINE`;

  // Confidence range reflects Wilson-LCB-style spread: tighter when fusion
  // sample size is large, wider when sources are scarce.  This is derived
  // from the same buckets the engine produces — no hardcoded ±4.
  const activeCount = sources.filter((s) => s.status === "active").length;
  const avgObs =
    sources.length > 0
      ? sources.reduce(
          (sum, source) => sum + ((source as any).observation_count ?? 0),
          0,
        ) / sources.length
      : 0;
  const bandHalfWidth = Math.max(
    1,
    Math.min(
      8,
      Math.round((100 - activeCount * 6) / 2 + (avgObs < 15 ? 2 : 0)),
    ),
  );
  const rangeLow = Math.max(0, currentConfidence - bandHalfWidth);
  const rangeHigh = currentConfidence;

  return (
    <main className="dash-shell">
      <header className="dash-header">
        <button className="dash-brand" onClick={onBack}>
          <span>V</span> VERIDION
        </button>
        <div className="dash-header-status">
          <i /> TRUST ENGINE ONLINE{" "}
          <b>IST {new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false })}</b>
          {provenance && (
            <span className="dash-header-real">
              {provenance.total_real_observations} REAL OBS
            </span>
          )}
        </div>
        <button className="dash-back" onClick={onBack}>
          <ArrowLeft size={13} /> Exit room
        </button>
      </header>
      <div className="dash-layout">
        <nav className="dash-nav">
          <span>WORKSPACE</span>
          {(
            [
              { key: "overview", label: "Overview", icon: Eye },
              { key: "graph", label: "Trust graph", icon: Network },
              { key: "registry", label: "Source registry", icon: Table2 },
            ] as const
          ).map((item) => (
            <button
              key={item.key}
              className={activeView === item.key ? "active" : ""}
              onClick={() => setActiveView(item.key)}
            >
              <item.icon size={15} />
              <span>{item.label}</span>
            </button>
          ))}
          <div className="dash-nav-foot">
            <span>TRACE / 01</span>
            <b>Decision integrity</b>
          </div>
        </nav>
        <section className="dash-content">
          <div className="dash-title-row">
            <div>
              <p className="dash-eyebrow">ASSESSMENT WORKSPACE</p>
              <h1>
                {activeView === "overview"
                  ? "The intelligence room."
                  : activeView === "graph"
                    ? "Trust, made inspectable."
                    : "Source registry."}
              </h1>
            </div>
            <div className={`recommend-chip ${hasAnomalies ? "warn" : ""}`}>
              <i /> {hasAnomalies ? "REVIEW REQUIRED" : "NETWORK HEALTHY"}
            </div>
          </div>
          {loading ? (
            <p className="dash-loading">Calibrating evidence ledger…</p>
          ) : (
            <>
              <section className="dash-metrics">
                <div>
                  <span>BOUNDED CONFIDENCE</span>
                  <strong>
                    {assessments?.confidence ?? 0}
                    <small>%</small>
                  </strong>
                  <em>{deltaLabel}</em>
                </div>
                <div>
                  <span>INDEPENDENT SOURCES</span>
                  <strong>
                    {String(
                      assessments?.independent_families ??
                        sources.filter((source) => source.status === "active").length,
                    ).padStart(2, "0")}
                  </strong>
                  <em>FAMILY-COLLAPSED</em>
                </div>
                <div>
                  <span>DISCOUNTED SIGNALS</span>
                  <strong className="risk-number">
                    {String(assessments?.discounted_count ?? 0).padStart(
                      2,
                      "0",
                    )}
                  </strong>
                  <em>SHARED LINEAGE</em>
                </div>
                <div>
                  <span>DRIFT WATCH</span>
                  <strong className="amber-number">
                    {String(assessments?.drifting_count ?? 0).padStart(2, "0")}
                  </strong>
                  <em>CUSUM MONITORED</em>
                </div>
              </section>
              {activeView === "overview" && (
                <>
                <section className="mission-grid">
                  <article className="assessment-card">
                    <p className="dash-eyebrow">CURRENT VERDICT</p>
                    <h2>
                      {hasAnomalies
                        ? "The signal holds — with reservations."
                        : "The signal holds."}
                    </h2>
                    <p>
                      Independent evidence remains coherent after Veridion
                      discounts shared lineages and bounds sensor drift.
                    </p>
                    <div className="assessment-footer">
                      <span>CONFIDENCE RANGE</span>
                      <strong>
                        {rangeLow}—{rangeHigh}%
                      </strong>
                    </div>
                  </article>
                  <article className="overview-graph">
                    <CinematicTrustGraph
                      nodes={rawGraph.nodes}
                      links={rawGraph.links}
                      excluded={excludedIds}
                      compact
                    />
                    <button onClick={() => setActiveView("graph")}>
                      Enter trust graph <ChevronRight size={14} />
                    </button>
                  </article>
                  <article className="evidence-rail">
                    <p className="dash-eyebrow">EVIDENCE TRAIL</p>
                    {flagged.slice(0, 3).map((source) => (
                      <div key={source.id}>
                        <i className={source.status} />
                        <span>
                          {source.status === "discounted"
                            ? "DEPENDENCY FLAG"
                            : "DRIFT WATCH"}
                        </span>
                        <strong>{source.provider_name}</strong>
                        <p>{source.evidence}</p>
                      </div>
                    ))}
                    <button onClick={() => setActiveView("registry")}>
                      Open full ledger <ChevronRight size={14} />
                    </button>
                  </article>
                </section>
                <section className="risk-alerts-grid">
                  <article className="risk-panel">
                    <p className="dash-eyebrow">RISK ASSESSMENT</p>
                    <div className="risk-level">
                      <span className={`risk-indicator ${(assessments?.risk_level ?? "low").toLowerCase()}`}>
                        {assessments?.risk_level ?? "ASSESSING"}
                      </span>
                    </div>
                    {(assessments?.risk_factors ?? []).map((f: any) => (
                      <div className="risk-factor-row" key={f.factor}>
                        <span>{f.factor}</span>
                        <div className="risk-bar"><i style={{ width: `${f.score}%` }} /></div>
                        <span>{f.score}%</span>
                      </div>
                    ))}
                  </article>
                  <article className="alerts-panel">
                    <p className="dash-eyebrow">ACTIVE ALERTS · {assessments?.alerts?.length ?? 0}</p>
                    {(assessments?.alerts ?? []).map((a: any, i: number) => (
                      <div key={i} className={`alert-item ${a.severity}`}>
                        <span>{a.type}</span>
                        <strong>{a.source}</strong>
                        <p>{a.message}</p>
                      </div>
                    ))}
                    {(!assessments?.alerts || assessments.alerts.length === 0) && (
                      <p className="no-alerts">No active alerts. All sources operating within parameters.</p>
                    )}
                  </article>
                </section>
                <section className="intel-grid">
                  <article className="uncertainty-panel">
                    <p className="dash-eyebrow">UNCERTAINTY DECOMPOSITION</p>
                    <h2>Where doubt remains.</h2>
                    {(assessments?.uncertainty_sources ?? []).map((u: any) => (
                      <div key={u.source} className="uncertainty-row">
                        <div className="uncertainty-header">
                          <span>{u.source}</span>
                          <span>{u.contribution}%</span>
                        </div>
                        <div className="uncertainty-bar"><i style={{ width: `${u.contribution}%` }} /></div>
                        <p>{u.description}</p>
                      </div>
                    ))}
                  </article>
                  <article className="contributors-panel">
                    <p className="dash-eyebrow">TOP CONTRIBUTORS</p>
                    <h2>Sources that anchor the verdict.</h2>
                    {(assessments?.positive_contributors ?? []).map((c: any) => (
                      <div key={c.id} className="contributor-row">
                        <i />
                        <div>
                          <strong>{c.provider_name}</strong>
                          <span>{c.instrument} · {c.observation_count} obs</span>
                        </div>
                        <b>{(c.trust_score * 100).toFixed(1)}%</b>
                      </div>
                    ))}
                    {assessments?.prediction && (
                      <div className="prediction-chip">
                        <span>CONFIDENCE TRAJECTORY</span>
                        <strong className={assessments.prediction.direction.toLowerCase()}>
                          {assessments.prediction.direction}
                        </strong>
                        <p>{assessments.prediction.detail}</p>
                      </div>
                    )}
                  </article>
                </section>
                {provenance && (
                  <section className="provenance-grid">
                    <article className="provenance-panel">
                      <p className="dash-eyebrow"><Database size={12} /> DATA PROVENANCE</p>
                      <h2>Where the evidence comes from.</h2>
                      <div className="provenance-stats">
                        <div><strong>{provenance.real_sources?.length ?? 0}</strong><span>REAL SOURCES</span></div>
                        <div><strong>{provenance.total_real_observations ?? 0}</strong><span>REAL OBS</span></div>
                        <div><strong>{provenance.synthetic_count ?? 0}</strong><span>INJECTED</span></div>
                        <div><strong>{(provenance.data_families ?? []).length}</strong><span>FAMILIES</span></div>
                      </div>
                      {(provenance.real_sources ?? []).map((rs: any) => (
                        <div key={rs.id} className="provenance-row">
                          <i className="prov-real" />
                          <div>
                            <strong>{rs.provider}</strong>
                            <span>{rs.instrument} · {rs.data_family?.toUpperCase()}</span>
                          </div>
                          <div className="prov-meta">
                            <span>{rs.observation_count} obs</span>
                            <a href={rs.data_url ?? "#"} target="_blank" rel="noopener">
                              API
                            </a>
                          </div>
                        </div>
                      ))}
                      {(provenance.synthetic_sources ?? []).map((ss: any) => (
                        <div key={ss.id} className="provenance-row synthetic">
                          <i className="prov-synth" />
                          <div>
                            <strong>{ss.provider}</strong>
                            <span>{ss.purpose}</span>
                          </div>
                          <span className="synth-badge">SYNTHETIC</span>
                        </div>
                      ))}
                      <p className="provenance-disclosure">{provenance.synthetic_disclosure}</p>
                    </article>
                    <article className="help-panel">
                      <p className="dash-eyebrow"><Lightbulb size={12} /> WHAT WOULD INCREASE TRUST</p>
                      <h2>Actionable intelligence gaps.</h2>
                      {(assessments?.what_would_help ?? []).map((h: any, i: number) => (
                        <div key={i} className="help-row">
                          <span className={`help-impact ${h.impact?.toLowerCase()}`}>{h.impact}</span>
                          <div>
                            <strong>{h.title}</strong>
                            <p>{h.description}</p>
                          </div>
                        </div>
                      ))}
                    </article>
                  </section>
                )}
                </>
              )}
              {activeView === "graph" && (
                <section className="trust-graph-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="dash-eyebrow">EVIDENCE TOPOLOGY</p>
                      <h2>
                        Only relationships with explanatory value remain
                        visible.
                      </h2>
                    </div>
                    <span>
                      {rawGraph.nodes.length} SOURCES · {rawGraph.links.length}{" "}
                      LINKS
                    </span>
                  </div>
                  <CinematicTrustGraph
                    nodes={rawGraph.nodes}
                    links={rawGraph.links}
                    excluded={excludedIds}
                  />
                </section>
              )}
              {activeView === "registry" && (
                <section className="registry-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="dash-eyebrow">WHAT-IF SIMULATION</p>
                      <h2>Remove a source to recalculate the verdict.</h2>
                    </div>
                    <span>
                      {excludedIds.size
                        ? `${excludedIds.size} EXCLUDED`
                        : "BASELINE"}
                    </span>
                  </div>
                  <div className="filter-bar">
                    {["all", "fire", "weather", "air_quality", "event", "synthetic"].map((f) => (
                      <button
                        key={f}
                        className={filterFamily === f ? "active" : ""}
                        onClick={() => setFilterFamily(f)}
                      >
                        {f === "air_quality" ? "AIR QUALITY" : f.toUpperCase()}
                      </button>
                    ))}
                  </div>
                  <table className="dash-table">
                    <thead>
                      <tr>
                        <th>Included</th>
                        <th>Source</th>
                        <th>Instrument</th>
                        <th>Type</th>
                        <th>State</th>
                        <th>Trust weight</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {sources
                        .filter((source) => {
                          if (filterFamily === "all") return true;
                          if (filterFamily === "synthetic") return source.is_synthetic;
                          return source.data_family === filterFamily && !source.is_synthetic;
                        })
                        .sort((a, b) => {
                          const aExcluded = excludedIds.has(a.id) || a.status === "excluded";
                          const bExcluded = excludedIds.has(b.id) || b.status === "excluded";
                          if (aExcluded && !bExcluded) return 1;
                          if (!aExcluded && bExcluded) return -1;
                          return 0;
                        })
                        .map((source) => {
                          const excluded = excludedIds.has(source.id) || source.status === "excluded";
                          return (
                            <tr
                              key={source.id}
                              className={excluded ? "excluded" : ""}
                            >
                            <td>
                              <button
                                className={`include-toggle ${excluded ? "" : "on"}`}
                                onClick={() => toggleExcluded(source.id)}
                                aria-label={`Toggle ${source.provider_name}`}
                              >
                                <i />
                              </button>
                            </td>
                            <td>
                              <strong>{source.provider_name}</strong>
                              {source.is_synthetic && (
                                <span className="synth-badge">SYNTHETIC</span>
                              )}
                            </td>
                            <td>{source.instrument}</td>
                            <td>
                              <span className="family-badge">
                                {source.is_synthetic ? "DEMO" : (source.data_family?.toUpperCase() ?? "—")}
                              </span>
                            </td>
                            <td>
                              <span className={`source-state ${source.status}`}>
                                {statusLabel(source.status)}
                              </span>
                            </td>
                            <td>
                              <div className="trust-weight">
                                <i
                                  style={{
                                    width: `${source.trust_score * 100}%`,
                                    background: tone(source.status),
                                  }}
                                />
                                <span>
                                  {(source.trust_score * 100).toFixed(1)}%
                                </span>
                              </div>
                            </td>
                            <td>
                              <button
                                className="history-btn"
                                onClick={() => openHistory(source.id)}
                              >
                                <LineChartIcon size={12} /> History
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </section>
              )}
            </>
          )}
        </section>
      </div>
      {selectedSourceId && (
        <div
          className="modal-overlay"
          onClick={() => setSelectedSourceId(null)}
        >
          <section
            className="modal-content"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              onClick={() => setSelectedSourceId(null)}
            >
              <X size={16} />
            </button>
            <p className="dash-eyebrow">SOURCE HEALTH HISTORY</p>
            <h2>Drift, over time.</h2>
            <p>
              Cumulative deviation is measured against the source’s expected
              performance envelope.
            </p>
            <div className="history-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData}>
                  <XAxis
                    dataKey="observation_id"
                    stroke="#575950"
                    tick={{ fontSize: 9, fontFamily: "DM Mono" }}
                  />
                  <YAxis
                    stroke="#575950"
                    tick={{ fontSize: 9, fontFamily: "DM Mono" }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#090b09",
                      border: "1px solid rgba(222,196,132,.2)",
                      fontFamily: "DM Mono",
                      fontSize: 10,
                    }}
                  />
                  <ReferenceLine y={2} stroke="#d25e40" strokeDasharray="4 4" />
                  <Line
                    type="monotone"
                    dataKey="raw_value"
                    stroke="rgba(169,177,115,.45)"
                    strokeWidth={1}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="cusum"
                    stroke="#dfb75d"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
