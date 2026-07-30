# 🌌 Veridion — Trust Engine & Ledger for Space & Geospatial Intelligence

A trust-scoring engine for geospatial observations — combines Bayesian statistics, graph-based reputation, drift detection, and collusion discounting into an explainable trust score.

<p align="center">
  <img src="https://img.shields.io/badge/XOVIAN%20AEROSPACE-Problem%20Statement%207-00f2fe?style=for-the-badge&logo=nasa&logoColor=white" alt="XOVIAN PS7"/>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-18.2-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/TypeScript-5.2-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/Three.js-WebGL-black?style=for-the-badge&logo=three.js&logoColor=white" alt="Three.js"/>
  <img src="https://img.shields.io/badge/License-MIT-green.style=for-the-badge" alt="License"/>
</p>

> **XOVIAN AEROSPACE | Hackathon Problem Statement 7**  
> *Building AI frameworks that judge not just what geospatial data says, but how much it should be trusted.*

---

## Table of Contents

- [Executive Summary](#-executive-summary)
- [Mathematical Engine Architecture](#-mathematical-engine-architecture)
- [Live Ingested Public Datasets](#-live-ingested-public-datasets)
- [Tech Stack](#-tech-stack)
- [Installation & Setup Guide](#-step-by-step-installation--setup-guide)
- [Backend REST API Reference](#-backend-rest-api-reference)
- [Project Repository Structure](#-project-repository-structure)
- [Troubleshooting](#-troubleshooting)
- [Included Documentation Artifacts](#-included-documentation-artifacts)
- [License](#-license)

---

## 📌 Executive Summary

Modern decision-makers in defense, disaster response, environmental monitoring, and climate insurance depend heavily on satellite imagery, atmospheric feeds, and geospatial intelligence. However, [...]

Standard data fusion models (such as naive averaging or majority voting) suffer from a critical flaw: **they assume all sources are independent**. If three "independent" commercial providers are a[...]

**Veridion** is an AI-driven trust-scoring framework that sits between raw geospatial datasets and executive decision-makers. It computes dynamic, explainable trust metrics by combining **graph-ba[...]

---

## ⚙️ Mathematical Engine Architecture

The Veridion Trust Engine consists of **4 complementary analytical layers** followed by **Independent Family Fusion**:

```
[Raw Multi-Source Geospatial Observations]
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│ Layer 1: Bayesian Lower Confidence Bound (Wilson Beta) │
│ Prevents new/low-sample feeds from lucky-streak bias   │
└───────────────────┬────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│ Layer 2: Trust Graph (Personalized PageRank)           │
│ Propagates credibility over spatial proximity network  │
└───────────────────┬────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│ Layer 3: Calibration Drift Detection (CUSUM)           │
│ Detects progressive degradation before sudden failure  │
└───────────────────┬────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│ Layer 4: Collusion & Co-Movement Discounting           │
│ Collapses reseller rings via lineage & correlation     │
└───────────────────┬────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│           Independent Family Fusion                    │
│ Fuses independent evidence families into 0-100% Score  │
└────────────────────────────────────────────────────────┘
```

### 1. Layer 1 — Bayesian Lower Confidence Bound (LCB)
To prevent sparse, low-sample sources from achieving unearned 100% trust off a short lucky streak, Veridion calculates the 5th percentile lower bound of the posterior Beta distribution:
$$\text{LCB} = \text{Beta}^{-1}(0.05;\, 1 + \text{successes},\, 1 + \text{failures})$$
*Result:* A new feed with $5/5$ perfect readings is bounded to $\approx 0.57$ trust, whereas an established feed with $27/30$ reaches $\approx 0.78$.

### 2. Layer 2 — Trust Graph (Personalized PageRank)
Sources are modeled as nodes in a directional graph ($G$), where edges represent spatial and domain corroboration. To prevent circular bootstrapping attacks, PageRank is personalized toward verifi[...]
$$\mathbf{pr} = \alpha \mathbf{M} \mathbf{pr} + (1 - \alpha) \mathbf{p}$$
where $\mathbf{p}$ is biased proportional to established observation counts and historical success rates.

### 3. Layer 3 — Drift Detection (CUSUM / Page-Hinkley)
Cumulative deviation tracking detects progressive sensor degradation (e.g., optical lens degradation, thermal sensor drift):
$$S_t = \max(0,\, S_{t-1} + (\mu_0 - x_t - k))$$
When peak $S_t$ exceeds threshold $\tau$, a smooth penalty factor is applied to reduce the source trust score.

### 4. Layer 4 — Collusion & Dependency Discounting
Detects reseller rings where commercial providers re-package the same upstream satellite imagery.
- **Declared Lineage**: Grouped immediately ($N$ dependent sources count as $\approx 1$ independent source).
- **Behavioral Co-Movement**: Pearson correlation ($r > 0.95$) across independent data families flags undeclared dependencies.

### 5. Independent Family Fusion
Discounted sources sharing lineage are collapsed into a single evidence family. Fused system confidence represents the conservative mean across distinct independent families:
$$\text{Fused Confidence} = \frac{1}{|F|} \sum_{f \in F} \max_{s \in f} (\text{Trust}_s)$$

---

## 📡 Live Ingested Public Datasets

Veridion ingests and validates real observations from **8 public APIs** across 7 core geospatial domains:

| Category | Dataset / Provider | API Source Endpoint | Data Family | Key Required? |
| :--- | :--- | :--- | :--- | :---: |
| **Earth Observation (EO)** | **NASA FIRMS** | `firms.modaps.eosdis.nasa.gov/api/area/` | `fire` | Free MAP_KEY |
| **Satellite & Remote Sensing**| **NASA EONET v3** | `eonet.gsfc.nasa.gov/api/v3/events` | `event` | No |
| **Weather & Atmospheric (EU)**| **Open-Meteo ECMWF** | `api.open-meteo.com/v1/ecmwf` | `weather` | No |
| **Weather & Atmospheric (US)**| **Open-Meteo GFS (NOAA)**| `api.open-meteo.com/v1/forecast?models=gfs_seamless` | `weather` | No |
| **Air Quality & Environmental**| **Copernicus CAMS** | `air-quality-api.open-meteo.com/v1/air-quality` | `air_quality` | No |
| **Space Weather** | **NOAA SWPC** | `services.swpc.noaa.gov/json/planetary_k_index_1m.json` | `space_weather` | No |
| **Disaster & Hazard** | **USGS Seismic Network**| `earthquake.usgs.gov/fdsnws/event/1/` | `disaster_hazard` | No |
| **GIS & Mapping** | **OpenStreetMap GIS** | `nominatim.openstreetmap.org/search` | `gis_mapping` | No |

---

## 🛠 Tech Stack

### Backend
- **Framework**: Python 3.11, FastAPI, Uvicorn
- **Database**: SQLite (local single-file database `backend/trace.db`), SQLAlchemy ORM
- **Algorithms**: NetworkX (Graph/PageRank), SciPy (`scipy.stats.beta`), NumPy

### Frontend
- **Framework**: React 18, TypeScript, Vite
- **3D WebGL Visualization**: Three.js, React Three Fiber, `@react-three/drei`
- **UI & Animations**: Tailwind CSS / Custom CSS, Framer Motion, Lucide React Icons

---

## 🚀 Step-by-Step Installation & Setup Guide

### Prerequisites
Make sure you have the following installed on your machine:
- **Node.js**: `v18.0.0` or higher ([Download Node.js](https://nodejs.org/))
- **Python**: `v3.10` or higher ([Download Python](https://www.python.org/))
- **Git**: Installed and configured

---

### 1. Clone the Repository
```bash
git clone https://github.com/NikunjKaushik20/Veridion.git
cd Veridion
```

---

### 2. Backend Setup & Local Database Seeding

Open a terminal window and navigate to the `backend/` directory:

```bash
cd backend
```

#### Create and activate a Virtual Environment
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### Install Backend Dependencies
```bash
pip install -r requirements.txt
```

#### Seed Database with Real Geospatial Feeds
Run the data fetcher and database seed script:
```bash
# Uses cached data or fetches live free APIs automatically:
python seed.py

# Optional: If you have a free NASA FIRMS MAP_KEY:
python seed.py --firms-key YOUR_NASA_FIRMS_KEY
```

#### Start FastAPI Development Server
```bash
uvicorn main:app --reload --port 8000
```
The backend API will now be running live at **`http://localhost:8000`**.  
*Interactive Swagger Documentation*: Visit [`http://localhost:8000/docs`](http://localhost:8000/docs).

---

### 3. Frontend Setup & Application Launch

Open a second terminal window in the root `Veridion/` folder:

#### Install Node Dependencies
```bash
npm install
```

#### Launch Vite Development Server
```bash
npm run dev
```

The frontend will start and print the local URL:
```text
  VITE v5.4.14  ready in 420 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

Open **`http://localhost:5173`** in any modern web browser (Chrome, Edge, Firefox, Safari).

---

## 🔌 Backend REST API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/public/story-snapshot` | `GET` | Curated snapshot for 3D Earth landing page (source counts, active status, fused confidence). |
| `/data/provenance` | `GET` | Complete data lineage listing real API URLs, fetch timestamps, and synthetic disclosures. |
| `/graph` | `GET` | Full node & edge graph payload for network visualizer. |
| `/engine/simulate` | `POST` | Interactive **What-If Simulator**. Accepts `{ "excluded_ids": [8, 9] }` and recomputes trust scores. |
| `/sources/{id}/history` | `GET` | Retrieves observation history and CUSUM drift timeline for a specific source. |

---

## 📂 Project Repository Structure

```text
Veridion/
├── README.md                           # Main Project Overview & Setup Guide
├── PS7_Trust_Ledger_Summary.md          # Problem Understanding & Math Methodology
├── Commercialization_Roadmap.md        # Target Verticals & 4-Phase Scale Strategy
├── package.json                        # Frontend Dependencies & Scripts
├── vite.config.ts                      # Vite Bundler Configuration
├── index.html                          # Entry HTML
├── backend/                            # Python FastAPI Backend
│   ├── main.py                         # REST API Endpoints & Routes
│   ├── trust_engine.py                 # 4-Layer Math Engine Implementation
│   ├── data_fetcher.py                 # Live API Fetcher & Local Disk Cache
│   ├── seed.py                         # Database Seeder & Injector
│   ├── models.py                       # SQLAlchemy ORM Models
│   ├── database.py                     # SQLite Connection & Session Manager
│   ├── trace.db                        # SQLite Database File
│   └── requirements.txt                # Backend Dependencies (FastAPI, SciPy, etc.)
└── src/                                # React Frontend Application
    ├── App.tsx                         # 3D WebGL Earth Landing Page & Stage Narrative
    ├── Dashboard.tsx                   # Decision-Maker Dashboard & What-If Simulator
    ├── data.ts                         # Stage Narratives & Coordinates Constants
    ├── styles.css                      # Custom Cinematic Dark Aesthetics
    └── main.tsx                        # React DOM Entry Point
```

---

## ❓ Troubleshooting

### Port 8000 or 5173 is already in use
If port `8000` is occupied, start Uvicorn on another port (e.g. `8001`) and update the backend URL in `src/Dashboard.tsx` and `src/App.tsx`.

### Missing virtual environment permissions (Windows)
If PowerShell blocks script execution when activating `venv`:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Running without live internet access
The backend includes cached responses in `backend/data_cache/`. If offline, `python seed.py` will automatically load local cached JSON datasets without throwing HTTP errors.

---

## 📜 Included Documentation Artifacts

- **[PS7_Trust_Ledger_Summary.md](file:///d:/Hacks/Emerging_Tech/PS7_Trust_Ledger_Summary.md)**: In-depth technical breakdown of all 4 trust layers, mathematical formulations, and evaluation chec[...]
- **[Commercialization_Roadmap.md](file:///d:/Hacks/Emerging_Tech/Commercialization_Roadmap.md)**: Go-to-market strategy across 5 enterprise verticals (Disaster Response, Defense Multi-INT, Insur[...]

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details. Built for the **Emerging Technologies Hackathon 2026** for **XOVIAN AEROSPACE Problem Statement[...]