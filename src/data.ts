export const stages = [
  { id: '01', eyebrow: 'RAW DETECTION', title: 'A signal is not yet a fact.', copy: 'Every trace begins as an uncorroborated observation — an early indication, deliberately held at low confidence.', metric: '12%', label: 'INITIAL CONFIDENCE', detail: 'NASA EONET · ECMWF · GFS · CAMS' },
  { id: '02', eyebrow: 'INDEPENDENT VALIDATION', title: 'Reality is seen from more than one angle.', copy: 'Independent readings arrive, tighten the spatial picture, and surface the contradictions worth investigating.', metric: '04', label: 'INDEPENDENT SOURCES', detail: 'SATELLITE · WEATHER · AIR QUALITY' },
  { id: '03', eyebrow: 'THE TRUST GRAPH', title: 'Agreement alone is not proof.', copy: 'Veridion maps how evidence travels. The visible network reveals which signals share a lineage — and which do not.', metric: '12', label: 'ACTIVE EVIDENCE LINKS', detail: 'PROVENANCE · 4 DATA FAMILIES' },
  { id: '04', eyebrow: 'DEPENDENCY ANALYSIS', title: 'Three voices. One origin.', copy: 'Correlation can disguise a shared dependency. We collapse the cluster before it can inflate the evidence.', metric: '05 → 02', label: 'DISCOUNTED WEIGHT', detail: 'DEPENDENCY CLUSTER · FLAGGED' },
  { id: '05', eyebrow: 'DRIFT DETECTION', title: 'Trust has a memory.', copy: 'Historical behavior exposes the slow changes a single reading cannot. Drift is measured, attributed, and bounded.', metric: '01', label: 'DRIFT FLAG', detail: 'CUSUM EVENT · ACTIVE REVIEW' },
  { id: '06', eyebrow: 'CONFIDENCE FUSION', title: 'Certainty, with its limits visible.', copy: 'Evidence families fuse into one conservative assessment. Precision grows — never faster than the data allows.', metric: '89%', label: 'BOUNDED CONFIDENCE', detail: '4 DATA FAMILIES' },
]

export const nodes = [
  [39.75, -121.62], [39.78, -121.60], [39.72, -121.65], [39.80, -121.58], [39.70, -121.70], [39.76, -121.61], [37.77, -122.42], [34.05, -118.24], [40.71, -74.0], [51.51, -0.13], [48.86, 2.35], [35.68, 139.69], [28.61, 77.21], [1.35, 103.82]
] as const

