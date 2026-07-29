# 🌌 Veridion — Trust Engine & Ledger for Space & Geospatial Intelligence

> **XOVIAN AEROSPACE | Hackathon Problem Statement 7**  
> *Building AI systems that can judge not just what geospatial data says, but how much it should be trusted.*

---

## 📌 Overview

**Veridion** is an AI-driven trust scoring framework that sits between raw multi-source space/geospatial datasets and decision-makers. In critical operations—such as wildfire tracking, earthquake response, atmospheric monitoring, and defense multi-INT fusion—data from independent satellite, remote sensing, and weather feeds is often delayed, inconsistent, or resold under different names.

Standard data fusion approaches (like simple averaging or majority voting) fail when multiple "independent" providers actually share a single upstream supplier. Veridion solves this by using **graph-based trust propagation with collusion discounting**, **CUSUM calibration drift detection**, and **Bayesian lower confidence bounds**.

---

## ⚡ Key Capabilities & Engine Layers

| Layer | Module | Method / Algorithm | Problem Solved |
|---|---|---|---|
| **1** | **Confidence Bounding** | Bayesian Lower Confidence Bound (Wilson-style Beta PPF) | Prevents low-sample sources from earning high trust off short lucky streaks. |
| **2** | **Trust Graph** | Personalized PageRank over spatial corroboration graph (`NetworkX`) | Prevents unearned reputation gaming through circular network relationships. |
| **3** | **Drift Detection** | CUSUM / Page-Hinkley cumulative deviation algorithm | Catches progressive sensor degradation and calibration drift before obvious failure. |
| **4** | **Collusion Discounting** | Pearson co-movement ($r > 0.95$) + Lineage clustering | Identifies commercial resellers sharing an upstream supplier and collapses their weight. |
| **Fusion** | **Independent Family Fusion** | Conservative multi-family aggregation | Fuses multi-source evidence into a single, bounded confidence percentage. |

---

## 📡 Supported Real Data Sources

Veridion ingests and processes live data from 8 public APIs across 7 core geospatial categories:

1. **Earth Observation (EO)**: NASA FIRMS (VIIRS + MODIS active fire detections with Fire Radiative Power).
2. **Satellite & Remote Sensing**: NASA EONET v3 (real-time wildfire event geometries).
3. **Weather & Atmospheric**: Open-Meteo ECMWF (IFS Global Model) & GFS (NOAA Seamless Model).
4. **Air Quality & Environmental**: Copernicus CAMS Air Quality (PM2.5, PM10, European AQI).
5. **Space Weather**: NOAA Space Weather Prediction Center (Planetary Kp Magnetometer index).
6. **Disaster & Hazard Monitoring**: USGS Seismic Hazards (Earthquake GeoJSON events).
7. **GIS & Mapping**: OpenStreetMap GIS (Nominatim spatial boundary features).

---

## 🏗 System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Data Ingestion Layer                            │
│  NASA EONET · ECMWF · GFS · Copernicus CAMS · NOAA SWPC · USGS · OSM   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Trust Engine                           │
│   Layer 1: Bayesian LCB   │  Layer 2: Trust Graph (Personalized PageRank)│
│   Layer 3: CUSUM Drift    │  Layer 4: Collusion & Co-Movement Discount │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Decision-Maker Dashboard                        │
│   • 3D WebGL Earth Globe      • Interactive Engine Stage Narrative     │
│   • What-If Simulator         • Evidence Trail & Provenance Modal      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Three.js / React Three Fiber (3D Globe), Framer Motion, Lucide Icons, Tailwind / Custom Vanilla CSS
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, SQLite, NetworkX, NumPy, SciPy
- **Data Protocols**: RESTful APIs, GeoJSON, Caching Layer

---

## 🚀 Getting Started

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python seed.py
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
# In the root directory:
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to launch the Veridion Dashboard.

---

## 📜 Deliverables Included

- `PS7_Trust_Ledger_Summary.md`: Detailed problem understanding, AI/ML methodology, and trust engine formulation.
- `Commercialization_Roadmap.md`: Target verticals, 4-phase technical scaling path, revenue model, and competitive moat.

---

## 📄 License

MIT License © 2026 Veridion Team
