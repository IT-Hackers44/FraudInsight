import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# SQLite for dev, PostgreSQL for prod
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_WhG3EcMw2Pvf@ep-cold-cherry-am62wycn-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String, default="USD")
    merchant_id = Column(String)
    merchant_category = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    device_fingerprint = Column(String)
    location_lat = Column(Float)
    location_lon = Column(Float)
    payment_method = Column(String)
    is_international = Column(Boolean, default=False)
    velocity_1h = Column(Integer, default=0)
    velocity_24h = Column(Integer, default=0)
    time_since_last_tx = Column(Float, default=0.0)
    amount_zscore = Column(Float, default=0.0)
    fraud_label = Column(Boolean, default=False)
    fraud_pattern = Column(String, nullable=True)

    # Risk/anomaly fields (added after analysis)
    risk_score = Column(Float, nullable=True)
    risk_tier = Column(String, nullable=True)
    is_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_merchant_timestamp", "merchant_id", "timestamp"),
    )

class FraudResultModel(Base):
    __tablename__ = "fraud_results"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    risk_score = Column(Float)
    risk_tier = Column(String, index=True)
    is_anomaly_if = Column(Boolean)
    is_anomaly_dbscan = Column(Boolean)
    is_anomaly_zscore = Column(Boolean)
    ensemble_consensus = Column(Boolean, index=True)
    flagged_by_count = Column(Integer)
    anomaly_explanation = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_risk_tier_created", "risk_tier", "created_at"),
    )

class PatternModel(Base):
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_id = Column(String, unique=True, index=True)
    name = Column(String)
    description = Column(String)
    pattern_type = Column(String, nullable=True)
    transaction_count = Column(Integer)
    affected_users = Column(Integer, nullable=True)
    first_seen = Column(DateTime)
    last_seen = Column(DateTime, nullable=True)
    risk_tier = Column(String)
    feature_signature = Column(JSON, nullable=True)
    sample_transactions = Column(JSON, nullable=True)
    indicators = Column(JSON, nullable=True)
    novelty_score = Column(Float, nullable=True)
    severity_score = Column(Float)
    is_new = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class ChainModel(Base):
    __tablename__ = "chains"

    id = Column(Integer, primary_key=True, index=True)
    chain_id = Column(String, unique=True, index=True)
    chain_type = Column(String)  # CYCLE, STAR, FUNNEL
    nodes = Column(JSON)
    edges = Column(JSON)
    total_amount = Column(Float)
    transaction_count = Column(Integer)
    risk_score = Column(Float)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")

if __name__ == "__main__":
    init_db()
