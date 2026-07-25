import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, index=True)
    instrument = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    trust_score = Column(Float, default=0.5)
    status = Column(String, default="active")
    # Provenance lineage — populated for sources sharing an upstream provider
    lineage = Column(String, nullable=True)
    # ── Data provenance fields ──
    data_url = Column(String, nullable=True)         # API endpoint this data came from
    fetched_at = Column(DateTime, nullable=True)      # When we pulled the data
    is_synthetic = Column(Boolean, default=False)     # True for injected demo sources
    data_family = Column(String, nullable=True)       # "fire", "weather", "air_quality", "event"
    observations = relationship("Observation", back_populates="source")


class Observation(Base):
    __tablename__ = "observations"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    # Real timestamp for time-series alignment
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    # Actual sensor reading (e.g. Fire Radiative Power in MW, temperature, PM2.5)
    raw_value = Column(Float, default=0.0)
    # Derived: True if reading is within calibrated normal range
    success = Column(Boolean, default=True)
    # Original API response fields (JSON blob for auditability)
    raw_metadata = Column(String, nullable=True)
    source = relationship("Source", back_populates="observations")


class TrustEdge(Base):
    __tablename__ = "trust_edges"
    id = Column(Integer, primary_key=True, index=True)
    source_a_id = Column(Integer, ForeignKey("sources.id"))
    source_b_id = Column(Integer, ForeignKey("sources.id"))
    weight = Column(Float, default=1.0)
    # "corroboration" | "collusion"
    edge_type = Column(String, default="corroboration")
