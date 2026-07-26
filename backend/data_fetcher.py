"""
Real data fetcher for Veridion trust engine.

Pulls from 5 publicly available APIs and caches responses to disk.
All sources are free.  NASA FIRMS requires a free MAP_KEY (instant
registration); the other four need no key at all.

Usage
-----
    python data_fetcher.py                 # fetch all, cache to data_cache/
    python data_fetcher.py --force         # ignore cache freshness, re-fetch
    python data_fetcher.py --firms-key XYZ # supply FIRMS key on CLI
"""

import json
import os
import sys
import time
import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CACHE_DIR = Path(__file__).parent / "data_cache"
CACHE_MAX_AGE_S = 6 * 3600  # 6 hours

# ── California wildfire region bounding box ───────────────────────
# Covers Northern California where fires are common
BBOX = {
    "west": -123.0,
    "south": 38.5,
    "east": -120.5,
    "north": 41.0,
}
CENTER_LAT = 39.76
CENTER_LON = -121.62


def _cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.json"


def _is_fresh(name: str) -> bool:
    p = _cache_path(name)
    if not p.exists():
        return False
    age = time.time() - p.stat().st_mtime
    return age < CACHE_MAX_AGE_S


def _save(name: str, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_cache_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  ✓ Cached → {_cache_path(name).name}  ({_size(data)} records)")


def _load(name: str):
    with open(_cache_path(name), "r", encoding="utf-8") as f:
        return json.load(f)


def _size(data) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return len(v)
    return 1


def _http_get(url: str, timeout: int = 30) -> str:
    """Simple HTTP GET with a User-Agent header."""
    req = Request(url, headers={"User-Agent": "Veridion-TrustEngine/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


# ==================================================================
# 1.  NASA FIRMS  —  Active fire detections (CSV)
# ==================================================================

def fetch_firms_data(map_key: str | None = None, days: int = 10):
    """
    Download VIIRS + MODIS fire detections for the California bbox.

    Returns list of dicts with keys:
        latitude, longitude, bright_ti4, scan, track, acq_date, acq_time,
        satellite, instrument, confidence, version, bright_ti5, frp, daynight
    """
    if not map_key:
        print("  ⚠ No FIRMS MAP_KEY supplied — skipping NASA FIRMS.")
        return None

    # FIRMS Area API:  /api/area/csv/{key}/{source}/{bbox}/{days}
    # bbox format: west,south,east,north
    bbox_str = f"{BBOX['west']},{BBOX['south']},{BBOX['east']},{BBOX['north']}"
    sources = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]
    all_detections = []

    for source in sources:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{map_key}/{source}/{bbox_str}/{days}"
        )
        try:
            print(f"  Fetching FIRMS {source} …")
            raw = _http_get(url, timeout=60)
            lines = raw.strip().split("\n")
            if len(lines) < 2:
                print(f"    → 0 detections for {source}")
                continue
            headers = [h.strip() for h in lines[0].split(",")]
            for line in lines[1:]:
                vals = line.split(",")
                row = dict(zip(headers, vals))
                row["_firms_source"] = source
                all_detections.append(row)
            print(f"    → {len(lines) - 1} detections")
        except (URLError, HTTPError) as e:
            print(f"    ✗ FIRMS {source} failed: {e}")

    return all_detections if all_detections else None


# ==================================================================
# 2.  NASA EONET  —  Natural event tracker (wildfires)
# ==================================================================

def fetch_eonet_events(days: int = 30):
    """
    Fetch recent wildfire events from NASA EONET v3.
    No API key required.

    Returns list of event dicts with id, title, geometry, sources.
    """
    url = (
        f"https://eonet.gsfc.nasa.gov/api/v3/events"
        f"?category=wildfires&days={days}&status=open"
    )
    print("  Fetching NASA EONET wildfires …")
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        events = data.get("events", [])
        print(f"    → {len(events)} wildfire events")
        return events
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"    ✗ EONET failed: {e}")
        return []


# ==================================================================
# 3.  Open-Meteo  —  ECMWF weather model
# ==================================================================

def fetch_weather_ecmwf(
    lat: float = CENTER_LAT,
    lon: float = CENTER_LON,
    past_days: int = 10,
):
    """
    Fetch hourly weather from the ECMWF (IFS) model via Open-Meteo.
    No API key required.

    Returns dict with "hourly" containing time, temperature_2m,
    relative_humidity_2m, wind_speed_10m.
    """
    url = (
        f"https://api.open-meteo.com/v1/ecmwf"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
        f"&past_days={past_days}&forecast_days=1"
        f"&timezone=America/Los_Angeles"
    )
    print("  Fetching Open-Meteo ECMWF weather …")
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        n = len(data.get("hourly", {}).get("time", []))
        print(f"    → {n} hourly readings")
        return data
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"    ✗ ECMWF weather failed: {e}")
        return None


# ==================================================================
# 4.  Open-Meteo  —  GFS (NOAA) weather model
# ==================================================================

def fetch_weather_gfs(
    lat: float = CENTER_LAT,
    lon: float = CENTER_LON,
    past_days: int = 10,
):
    """
    Fetch hourly weather from the NOAA GFS model via Open-Meteo.
    No API key required.

    Returns same structure as ECMWF fetch — allows direct comparison.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
        f"&models=gfs_seamless"
        f"&past_days={past_days}&forecast_days=1"
        f"&timezone=America/Los_Angeles"
    )
    print("  Fetching Open-Meteo GFS/NOAA weather …")
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        n = len(data.get("hourly", {}).get("time", []))
        print(f"    → {n} hourly readings")
        return data
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"    ✗ GFS weather failed: {e}")
        return None


# ==================================================================
# 5.  Open-Meteo  —  Air Quality (Copernicus CAMS)
# ==================================================================

def fetch_air_quality(
    lat: float = CENTER_LAT,
    lon: float = CENTER_LON,
    past_days: int = 10,
):
    """
    Fetch PM2.5, PM10, and European AQI from the Copernicus CAMS model.
    No API key required.

    Returns dict with "hourly" containing time, pm2_5, pm10,
    european_aqi.
    """
    url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=pm2_5,pm10,european_aqi"
        f"&past_days={past_days}&forecast_days=1"
        f"&timezone=America/Los_Angeles"
    )
    print("  Fetching Open-Meteo Air Quality (CAMS) …")
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        n = len(data.get("hourly", {}).get("time", []))
        print(f"    → {n} hourly readings")
        return data
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"    ✗ Air quality failed: {e}")
        return None


# ==================================================================
# 6.  NOAA Space Weather  — Planetary K-Index
# ==================================================================

def fetch_space_weather():
    """Download NOAA Space Weather Prediction Center Planetary Kp index."""
    print("  Fetching NOAA Space Weather (Kp index) …")
    url = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        n = len(data) if isinstance(data, list) else 0
        print(f"    → {n} space weather observations")
        return data
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"    ✗ Space weather failed: {e}")
        return None


# ==================================================================
# 7.  USGS Seismic Hazards  — Earthquake Events
# ==================================================================

def fetch_usgs_earthquakes():
    """Download USGS Earthquakes min mag 2.5."""
    print("  Fetching USGS Seismic Hazards …")
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=2.5&limit=30"
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        n = len(data.get("features", [])) if isinstance(data, dict) else 0
        print(f"    → {n} seismic hazard events")
        return data
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"    ✗ USGS Earthquakes failed: {e}")
        return None


# ==================================================================
# 8.  OpenStreetMap GIS  — Feature boundaries
# ==================================================================

def fetch_osm_gis():
    """Download OpenStreetMap GIS features."""
    print("  Fetching OpenStreetMap GIS feature boundary data …")
    url = "https://nominatim.openstreetmap.org/search?q=Plumas+National+Forest&format=json"
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        n = len(data) if isinstance(data, list) else 0
        print(f"    → {n} GIS spatial features")
        return data
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"    ✗ OSM GIS failed: {e}")
        return None


# ==================================================================
# Master fetch-and-cache
# ==================================================================

def fetch_all_and_cache(
    firms_key: str | None = None,
    force: bool = False,
):
    """
    Fetch all real data sources and cache to data_cache/.
    """
    print("=" * 60)
    print("VERIDION DATA FETCHER — Real geospatial data ingestion")
    print("=" * 60)
    print()

    results = {}

    # 1. NASA FIRMS
    name = "firms_fires"
    if force or not _is_fresh(name):
        data = fetch_firms_data(firms_key)
        if data:
            _save(name, data)
            results[name] = len(data)
        else:
            results[name] = 0
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # 2. NASA EONET
    name = "eonet_wildfires"
    if force or not _is_fresh(name):
        data = fetch_eonet_events()
        _save(name, data)
        results[name] = len(data)
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # 3. ECMWF weather
    name = "weather_ecmwf"
    if force or not _is_fresh(name):
        data = fetch_weather_ecmwf()
        if data:
            _save(name, data)
            results[name] = len(data.get("hourly", {}).get("time", []))
        else:
            results[name] = 0
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # 4. GFS weather
    name = "weather_gfs"
    if force or not _is_fresh(name):
        data = fetch_weather_gfs()
        if data:
            _save(name, data)
            results[name] = len(data.get("hourly", {}).get("time", []))
        else:
            results[name] = 0
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # 5. Air quality
    name = "air_quality"
    if force or not _is_fresh(name):
        data = fetch_air_quality()
        if data:
            _save(name, data)
            results[name] = len(data.get("hourly", {}).get("time", []))
        else:
            results[name] = 0
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # 6. Space weather
    name = "space_weather"
    if force or not _is_fresh(name):
        data = fetch_space_weather()
        if data:
            _save(name, data)
            results[name] = len(data) if isinstance(data, list) else 1
        else:
            results[name] = 0
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # 7. USGS Earthquakes
    name = "usgs_earthquakes"
    if force or not _is_fresh(name):
        data = fetch_usgs_earthquakes()
        if data:
            _save(name, data)
            results[name] = len(data.get("features", [])) if isinstance(data, dict) else 1
        else:
            results[name] = 0
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # 8. OSM GIS
    name = "osm_gis"
    if force or not _is_fresh(name):
        data = fetch_osm_gis()
        if data:
            _save(name, data)
            results[name] = len(data) if isinstance(data, list) else 1
        else:
            results[name] = 0
    else:
        print(f"  ✓ {name} — cache is fresh, skipping fetch")
        results[name] = _size(_load(name))

    # Summary
    print()
    print("─" * 40)
    print("FETCH SUMMARY")
    print("─" * 40)
    total = 0
    for src, count in results.items():
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {src:25s} {count:>5} records")
        total += count
    print(f"\n  TOTAL: {total} real observations cached")
    print(f"  Cache dir: {CACHE_DIR.resolve()}")
    print()

    return results


# ==================================================================
# CLI
# ==================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Veridion real data fetcher")
    parser.add_argument("--firms-key", default=os.environ.get("FIRMS_MAP_KEY"),
                        help="NASA FIRMS MAP_KEY (or set FIRMS_MAP_KEY env var)")
    parser.add_argument("--force", action="store_true",
                        help="Ignore cache freshness, re-fetch all")
    args = parser.parse_args()

    fetch_all_and_cache(firms_key=args.firms_key, force=args.force)

