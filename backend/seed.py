"""
Seed the database with REAL geospatial data + targeted synthetic injections.

Data sources  (all free, publicly available)
---------------------------------------------
1. NASA EONET      — wildfire events with locations        (no key)
2. Open-Meteo ECMWF — weather from European model          (no key)
3. Open-Meteo GFS   — weather from NOAA model              (no key)
4. Open-Meteo CAMS  — air quality (PM2.5, PM10)            (no key)
5. NASA FIRMS       — active fire detections                (free MAP_KEY)

Synthetic injections  (labelled is_synthetic=True)
---------------------------------------------------
1. Collusion ring   — 3 fake commercial providers reselling one real feed
2. Drifting sensor  — real readings with progressive calibration bias
3. Lucky streak     — 5 real observations, new source with thin history

Run
---
    python seed.py                         # uses cached data (run data_fetcher.py first)
    python seed.py --firms-key YOUR_KEY    # fetch + seed with FIRMS data
"""

import json
import datetime
import os
import numpy as np
from pathlib import Path

from database import SessionLocal, engine
import models
from trust_engine import run_trust_engine
from data_fetcher import fetch_all_and_cache, CACHE_DIR, CENTER_LAT, CENTER_LON


def _load_cache(name: str):
    """Load a cached JSON file, return None if missing."""
    p = CACHE_DIR / f"{name}.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_db(firms_key: str | None = None):
    # ── Ensure we have real data ──────────────────────────────────
    fetch_all_and_cache(firms_key=firms_key)

    # ── Reset DB ──────────────────────────────────────────────────
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    rng = np.random.default_rng(42)
    now = datetime.datetime.utcnow()

    all_sources: list[models.Source] = []

    # ==============================================================
    # REAL SOURCE 1 — NASA EONET wildfire events
    # ==============================================================

    eonet_data = _load_cache("eonet_wildfires")
    eonet_source = None

    if eonet_data:
        # Pick events that have geometry coordinates
        events_with_coords = []
        for ev in eonet_data:
            geom = ev.get("geometry", ev.get("geometries", []))
            if isinstance(geom, list) and len(geom) > 0:
                events_with_coords.append(ev)
            elif isinstance(geom, dict):
                events_with_coords.append(ev)

        eonet_source = models.Source(
            provider_name="NASA EONET",
            instrument="Event Tracker",
            lat=CENTER_LAT,
            lon=CENTER_LON,
            lineage=None,
            data_url="https://eonet.gsfc.nasa.gov/api/v3/events?category=wildfires",
            fetched_at=now,
            is_synthetic=False,
            data_family="event",
        )
        db.add(eonet_source)
        all_sources.append(eonet_source)
        db.commit()  # assign ID

        count = 0
        for ev in events_with_coords[:40]:  # cap at 40 events for demo
            geom = ev.get("geometry", ev.get("geometries", []))
            if isinstance(geom, list) and len(geom) > 0:
                coords = geom[-1].get("coordinates", [])
                ts_str = geom[-1].get("date", "")
            elif isinstance(geom, dict):
                coords = geom.get("coordinates", [])
                ts_str = geom.get("date", "")
            else:
                continue

            if not coords or len(coords) < 2:
                continue

            lon, lat = float(coords[0]), float(coords[1])

            try:
                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except (ValueError, AttributeError):
                ts = now - datetime.timedelta(days=int(rng.integers(1, 15)))

            db.add(models.Observation(
                source_id=eonet_source.id,
                timestamp=ts,
                raw_value=1.0,  # event detected = 1.0
                success=True,
                raw_metadata=json.dumps({
                    "event_id": ev.get("id"),
                    "title": ev.get("title"),
                    "lat": lat,
                    "lon": lon,
                }),
            ))
            count += 1

        print(f"  EONET: {count} real wildfire event observations")

    # ==============================================================
    # REAL SOURCE 2 — Open-Meteo ECMWF weather
    # ==============================================================

    ecmwf_data = _load_cache("weather_ecmwf")
    ecmwf_source = None

    if ecmwf_data and "hourly" in ecmwf_data:
        hourly = ecmwf_data["hourly"]
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        wind = hourly.get("wind_speed_10m", [])

        ecmwf_source = models.Source(
            provider_name="Open-Meteo (ECMWF)",
            instrument="IFS Global Model",
            lat=CENTER_LAT,
            lon=CENTER_LON,
            lineage=None,
            data_url="https://api.open-meteo.com/v1/ecmwf",
            fetched_at=now,
            is_synthetic=False,
            data_family="weather",
        )
        db.add(ecmwf_source)
        all_sources.append(ecmwf_source)
        db.commit()

        # Sample every 6 hours to get ~44 observations over 11 days
        count = 0
        for i in range(0, len(times), 6):
            if i >= len(temps):
                break
            temp_val = temps[i]
            if temp_val is None:
                continue
            try:
                ts = datetime.datetime.fromisoformat(times[i])
            except (ValueError, TypeError):
                continue

            # Success = temperature within plausible range for California summer
            success = -5 < temp_val < 55
            db.add(models.Observation(
                source_id=ecmwf_source.id,
                timestamp=ts,
                raw_value=round(temp_val, 2),
                success=success,
                raw_metadata=json.dumps({
                    "temperature_2m": temp_val,
                    "humidity": humidity[i] if i < len(humidity) else None,
                    "wind_speed": wind[i] if i < len(wind) else None,
                }),
            ))
            count += 1

        print(f"  ECMWF: {count} real weather observations")

    # ==============================================================
    # REAL SOURCE 3 — Open-Meteo GFS (NOAA) weather
    # ==============================================================

    gfs_data = _load_cache("weather_gfs")
    gfs_source = None

    if gfs_data and "hourly" in gfs_data:
        hourly = gfs_data["hourly"]
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        wind = hourly.get("wind_speed_10m", [])

        gfs_source = models.Source(
            provider_name="Open-Meteo (GFS/NOAA)",
            instrument="GFS Global Model",
            lat=CENTER_LAT,
            lon=CENTER_LON,
            lineage=None,
            data_url="https://api.open-meteo.com/v1/forecast?models=gfs_seamless",
            fetched_at=now,
            is_synthetic=False,
            data_family="weather",
        )
        db.add(gfs_source)
        all_sources.append(gfs_source)
        db.commit()

        count = 0
        for i in range(0, len(times), 6):
            if i >= len(temps):
                break
            temp_val = temps[i]
            if temp_val is None:
                continue
            try:
                ts = datetime.datetime.fromisoformat(times[i])
            except (ValueError, TypeError):
                continue

            success = -5 < temp_val < 55
            db.add(models.Observation(
                source_id=gfs_source.id,
                timestamp=ts,
                raw_value=round(temp_val, 2),
                success=success,
                raw_metadata=json.dumps({
                    "temperature_2m": temp_val,
                    "humidity": humidity[i] if i < len(humidity) else None,
                    "wind_speed": wind[i] if i < len(wind) else None,
                }),
            ))
            count += 1

        print(f"  GFS:   {count} real weather observations")

    # ==============================================================
    # REAL SOURCE 4 — Copernicus CAMS Air Quality
    # ==============================================================

    aq_data = _load_cache("air_quality")
    aq_source = None

    if aq_data and "hourly" in aq_data:
        hourly = aq_data["hourly"]
        times = hourly.get("time", [])
        pm25 = hourly.get("pm2_5", [])
        pm10 = hourly.get("pm10", [])
        aqi = hourly.get("european_aqi", [])

        aq_source = models.Source(
            provider_name="Copernicus CAMS",
            instrument="Air Quality Model",
            lat=CENTER_LAT,
            lon=CENTER_LON,
            lineage=None,
            data_url="https://air-quality-api.open-meteo.com/v1/air-quality",
            fetched_at=now,
            is_synthetic=False,
            data_family="air_quality",
        )
        db.add(aq_source)
        all_sources.append(aq_source)
        db.commit()

        count = 0
        for i in range(0, len(times), 6):
            if i >= len(pm25):
                break
            pm_val = pm25[i]
            if pm_val is None:
                continue
            try:
                ts = datetime.datetime.fromisoformat(times[i])
            except (ValueError, TypeError):
                continue

            # success = PM2.5 reading is plausible (not sensor error)
            success = 0 <= pm_val < 500
            db.add(models.Observation(
                source_id=aq_source.id,
                timestamp=ts,
                raw_value=round(pm_val, 2),
                success=success,
                raw_metadata=json.dumps({
                    "pm2_5": pm_val,
                    "pm10": pm10[i] if i < len(pm10) else None,
                    "european_aqi": aqi[i] if i < len(aqi) else None,
                }),
            ))
            count += 1

        print(f"  CAMS:  {count} real air quality observations")

    # ==============================================================
    # REAL SOURCE 5 — NASA FIRMS fire detections (if available)
    # ==============================================================

    firms_data = _load_cache("firms_fires")
    firms_sources: dict[str, models.Source] = {}

    if firms_data and len(firms_data) > 0:
        # Group detections by satellite/instrument combo
        for det in firms_data:
            sat = det.get("satellite", "Unknown")
            instr = det.get("instrument", "VIIRS")
            key = f"{sat}_{instr}"

            if key not in firms_sources:
                # Map satellite codes to human names
                sat_names = {
                    "N": "NASA FIRMS (VIIRS-SNPP)",
                    "1": "NASA FIRMS (VIIRS-NOAA20)",
                    "2": "NASA FIRMS (VIIRS-NOAA21)",
                    "T": "NASA FIRMS (MODIS-Terra)",
                    "A": "NASA FIRMS (MODIS-Aqua)",
                }
                name = sat_names.get(sat, f"NASA FIRMS ({sat}-{instr})")

                s = models.Source(
                    provider_name=name,
                    instrument=instr,
                    lat=float(det.get("latitude", CENTER_LAT)),
                    lon=float(det.get("longitude", CENTER_LON)),
                    lineage=None,
                    data_url="https://firms.modaps.eosdis.nasa.gov/api/area/",
                    fetched_at=now,
                    is_synthetic=False,
                    data_family="fire",
                )
                db.add(s)
                db.commit()
                firms_sources[key] = s
                all_sources.append(s)

        # Create observations from real fire detections
        for det in firms_data:
            sat = det.get("satellite", "Unknown")
            instr = det.get("instrument", "VIIRS")
            key = f"{sat}_{instr}"
            source = firms_sources.get(key)
            if not source:
                continue

            try:
                frp = float(det.get("frp", 0))
            except (ValueError, TypeError):
                frp = 0.0

            conf = det.get("confidence", "nominal")
            if isinstance(conf, str):
                success = conf.lower() in ("nominal", "high", "h", "n")
            else:
                try:
                    success = int(conf) >= 50
                except (ValueError, TypeError):
                    success = True

            # Parse timestamp
            acq_date = det.get("acq_date", "")
            acq_time = det.get("acq_time", "0000")
            try:
                ts = datetime.datetime.strptime(
                    f"{acq_date} {acq_time}", "%Y-%m-%d %H%M"
                )
            except (ValueError, TypeError):
                ts = now - datetime.timedelta(hours=int(rng.integers(1, 240)))

            db.add(models.Observation(
                source_id=source.id,
                timestamp=ts,
                raw_value=max(0.1, frp),
                success=success,
                raw_metadata=json.dumps({
                    "latitude": det.get("latitude"),
                    "longitude": det.get("longitude"),
                    "frp": frp,
                    "confidence": conf,
                    "bright_ti4": det.get("bright_ti4"),
                    "daynight": det.get("daynight"),
                }),
            ))

        total_firms = len(firms_data)
        print(f"  FIRMS: {total_firms} real fire detections across "
              f"{len(firms_sources)} satellite instruments")
    else:
        print("  FIRMS: no data (MAP_KEY not provided or fetch failed)")

    # ==============================================================
    # REAL SOURCE 6 — NOAA Space Weather (Planetary Kp Index)
    # ==============================================================

    sw_data = _load_cache("space_weather")
    if sw_data and isinstance(sw_data, list):
        sw_source = models.Source(
            provider_name="NOAA Space Weather",
            instrument="Planetary Kp Magnetometer",
            lat=CENTER_LAT + 0.1,
            lon=CENTER_LON - 0.1,
            lineage=None,
            data_url="https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
            fetched_at=now,
            is_synthetic=False,
            data_family="space_weather",
        )
        db.add(sw_source)
        all_sources.append(sw_source)
        db.commit()

        count = 0
        for item in sw_data[:40]:
            try:
                kp = float(item.get("kp_index", item.get("kp", 0)))
                ts_str = item.get("time_tag", "")
                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else now
            except (ValueError, TypeError):
                continue
            db.add(models.Observation(
                source_id=sw_source.id,
                timestamp=ts,
                raw_value=kp,
                success=kp < 8.0,
                raw_metadata=json.dumps(item),
            ))
            count += 1
        print(f"  NOAA SWPC: {count} real space weather observations")

    # ==============================================================
    # REAL SOURCE 7 — USGS Seismic Hazards (Earthquake Events)
    # ==============================================================

    eq_data = _load_cache("usgs_earthquakes")
    if eq_data and isinstance(eq_data, dict) and "features" in eq_data:
        eq_source = models.Source(
            provider_name="USGS Seismic Network",
            instrument="ANSS Seismograph Array",
            lat=CENTER_LAT - 0.15,
            lon=CENTER_LON + 0.1,
            lineage=None,
            data_url="https://earthquake.usgs.gov/fdsnws/event/1/",
            fetched_at=now,
            is_synthetic=False,
            data_family="disaster_hazard",
        )
        db.add(eq_source)
        all_sources.append(eq_source)
        db.commit()

        count = 0
        for feat in eq_data.get("features", [])[:30]:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            mag = props.get("mag", 0.0)
            ms = props.get("time")
            ts = datetime.datetime.fromtimestamp(ms / 1000.0) if ms else now
            db.add(models.Observation(
                source_id=eq_source.id,
                timestamp=ts,
                raw_value=float(mag) if mag else 2.5,
                success=True,
                raw_metadata=json.dumps({"place": props.get("place"), "mag": mag, "geometry": geom}),
            ))
            count += 1
        print(f"  USGS:  {count} real seismic hazard observations")

    # ==============================================================
    # REAL SOURCE 8 — OpenStreetMap GIS Spatial Feature Boundaries
    # ==============================================================

    gis_data = _load_cache("osm_gis")
    if gis_data and isinstance(gis_data, list):
        gis_source = models.Source(
            provider_name="OpenStreetMap GIS",
            instrument="Nominatim Spatial Index",
            lat=CENTER_LAT + 0.05,
            lon=CENTER_LON + 0.05,
            lineage=None,
            data_url="https://nominatim.openstreetmap.org/",
            fetched_at=now,
            is_synthetic=False,
            data_family="gis_mapping",
        )
        db.add(gis_source)
        all_sources.append(gis_source)
        db.commit()

        count = 0
        for feat in gis_data[:20]:
            try:
                lat = float(feat.get("lat", CENTER_LAT))
                lon = float(feat.get("lon", CENTER_LON))
            except (ValueError, TypeError):
                lat, lon = CENTER_LAT, CENTER_LON
            db.add(models.Observation(
                source_id=gis_source.id,
                timestamp=now - datetime.timedelta(hours=count * 2),
                raw_value=1.0,
                success=True,
                raw_metadata=json.dumps({"display_name": feat.get("display_name"), "boundingbox": feat.get("boundingbox")}),
            ))
            count += 1
        print(f"  OSM GIS: {count} real spatial boundary observations")

    db.commit()

    # ==============================================================
    # SYNTHETIC INJECTION 1 — Collusion ring (3 fake resellers)
    #
    # Takes real data from one of the weather sources and clones it
    # with sub-unit noise to simulate 3 "independent" commercial
    # providers that are actually reselling the same upstream feed.
    # ==============================================================

    print("\n  --- Synthetic Injections (is_synthetic=True) ---")

    # Use ECMWF observations as the base feed to clone
    base_source = ecmwf_source or (all_sources[0] if all_sources else None)
    collusion_sources: list[models.Source] = []

    if base_source:
        base_obs = (
            db.query(models.Observation)
            .filter(models.Observation.source_id == base_source.id)
            .order_by(models.Observation.id)
            .all()
        )

        collusion_defs = [
            ("GeoWatch Analytics", "Resold Feed", 39.77, -121.63),
            ("FireScope Pro",      "Resold Feed", 39.76, -121.61),
            ("SatGuard Intl",      "Resold Feed", 39.75, -121.62),
        ]

        for name, instr, lat, lon in collusion_defs:
            s = models.Source(
                provider_name=name,
                instrument=instr,
                lat=lat, lon=lon,
                lineage="SHARED-UPSTREAM-RESELLER",
                data_url=None,
                fetched_at=None,
                is_synthetic=True,
                data_family=base_source.data_family,
            )
            db.add(s)
            collusion_sources.append(s)
        all_sources.extend(collusion_sources)
        db.commit()

        # Clone base readings with tiny noise
        for s in collusion_sources:
            for obs in base_obs:
                noisy_val = obs.raw_value + float(rng.normal(0, 0.2))
                db.add(models.Observation(
                    source_id=s.id,
                    timestamp=obs.timestamp,
                    raw_value=round(max(0.1, noisy_val), 2),
                    success=True,
                    raw_metadata=json.dumps({"cloned_from": base_source.provider_name}),
                ))

        print(f"  Collusion ring: 3 fake resellers of '{base_source.provider_name}' "
              f"({len(base_obs)} obs each)")

    # ==============================================================
    # SYNTHETIC INJECTION 2 — Drifting sensor
    #
    # Takes real readings and progressively degrades later ones
    # to simulate calibration drift detectable by CUSUM.
    # ==============================================================

    drift_source = models.Source(
        provider_name="NOAA GOES-16 (degraded)",
        instrument="ABI",
        lat=25.76, lon=-80.19,
        lineage=None,
        data_url=None,
        fetched_at=None,
        is_synthetic=True,
        data_family="fire",
    )
    db.add(drift_source)
    all_sources.append(drift_source)
    db.commit()

    # 30 observations: first 8 clean, then progressive degradation
    for j in range(30):
        days_ago = 90 * (1 - j / 30)
        ts = now - datetime.timedelta(
            days=days_ago, hours=int(rng.integers(0, 24))
        )
        drift_bias = max(0, (j - 8) * 1.5)
        base_val = float(rng.normal(28.0 + drift_bias, 6.0))

        if j < 8:
            success = True
        elif j < 15:
            success = bool(rng.random() > 0.30)
        else:
            success = bool(rng.random() > 0.70)

        db.add(models.Observation(
            source_id=drift_source.id,
            timestamp=ts,
            raw_value=max(0.1, base_val),
            success=bool(success),
            raw_metadata=json.dumps({"injected_drift_bias": drift_bias}),
        ))

    print("  Drifting sensor: 30 obs with progressive calibration drift")

    # ==============================================================
    # SYNTHETIC INJECTION 3 — Lucky streak (new source)
    #
    # Only 5 observations, all successful — LCB should correctly
    # hold trust at ~0.57, not 1.0.
    # ==============================================================

    new_source = models.Source(
        provider_name="Orbital Insight (new)",
        instrument="SAR",
        lat=-33.87, lon=151.21,
        lineage=None,
        data_url=None,
        fetched_at=None,
        is_synthetic=True,
        data_family="fire",
    )
    db.add(new_source)
    all_sources.append(new_source)
    db.commit()

    for j in range(5):
        days_ago = 10 * (1 - j / 5)
        ts = now - datetime.timedelta(
            days=days_ago, hours=int(rng.integers(0, 12))
        )
        db.add(models.Observation(
            source_id=new_source.id,
            timestamp=ts,
            raw_value=max(0.1, float(rng.normal(29.0, 3.0))),
            success=True,
            raw_metadata=json.dumps({"note": "lucky_streak_injection"}),
        ))

    print("  Lucky streak: 5 perfect obs (LCB will bound trust correctly)")

    db.commit()

    # ==============================================================
    # TRUST EDGES — proximity + cross-domain corroboration
    # ==============================================================

    # (a) Proximity edges: sources within ~5 degrees
    for i, a in enumerate(all_sources):
        for j, b in enumerate(all_sources):
            if i >= j:
                continue
            dist = ((a.lat - b.lat) ** 2 + (a.lon - b.lon) ** 2) ** 0.5
            if dist < 5.0:
                w = round(max(0.1, 1.0 - dist / 5.0), 3)
                db.add(models.TrustEdge(
                    source_a_id=a.id, source_b_id=b.id,
                    weight=w, edge_type="corroboration",
                ))

    # (b) Cross-domain corroboration: weather models should agree
    weather_sources = [s for s in all_sources if s.data_family == "weather" and not s.is_synthetic]
    for i, a in enumerate(weather_sources):
        for b in weather_sources[i + 1:]:
            db.add(models.TrustEdge(
                source_a_id=a.id, source_b_id=b.id,
                weight=0.7, edge_type="corroboration",
            ))

    # (c) Cross-domain: fire events + air quality (smoke correlation)
    fire_sources = [s for s in all_sources if s.data_family in ("fire", "event") and not s.is_synthetic]
    aq_sources_list = [s for s in all_sources if s.data_family == "air_quality" and not s.is_synthetic]
    for fs in fire_sources:
        for aqs in aq_sources_list:
            db.add(models.TrustEdge(
                source_a_id=fs.id, source_b_id=aqs.id,
                weight=0.5, edge_type="corroboration",
            ))

    # (d) Cross-reference: EONET events with weather models
    if eonet_source:
        for ws in weather_sources:
            db.add(models.TrustEdge(
                source_a_id=eonet_source.id, source_b_id=ws.id,
                weight=0.4, edge_type="corroboration",
            ))

    db.commit()

    # ==============================================================
    # RUN TRUST ENGINE
    # ==============================================================

    print(f"\nSeeded {len(all_sources)} sources "
          f"({sum(1 for s in all_sources if not s.is_synthetic)} real, "
          f"{sum(1 for s in all_sources if s.is_synthetic)} synthetic)")
    print("Running trust engine ...")
    results = run_trust_engine(db)
    print("Done.\n")

    for r in results:
        flag = ""
        if r["drift_penalty"] > 0:
            flag += f" CUSUM={r['cusum_peak']:.2f}"
        if r["collusion_penalty"] > 0:
            flag += f" COL={r['collusion_penalty']:.2f}"
        synth = " [SYNTH]" if any(
            s.id == r["id"] and s.is_synthetic for s in all_sources
        ) else ""
        print(
            f"  {r['provider_name']:35s} | {r['status']:12s} | "
            f"trust={r['trust_score']:.4f} | obs={r['observation_count']}"
            f"{flag}{synth}"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed Veridion with real data")
    parser.add_argument("--firms-key", default=os.environ.get("FIRMS_MAP_KEY"),
                        help="NASA FIRMS MAP_KEY (optional)")
    args = parser.parse_args()

    seed_db(firms_key=args.firms_key)
