from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class FraudDetectionResult(BaseModel):
    transaction_id: str
    risk_score: float
    risk_tier: str  # CRITICAL, HIGH, MEDIUM, LOW
    is_anomaly_if: bool
    is_anomaly_dbscan: bool
    is_anomaly_zscore: bool
    ensemble_consensus: bool
    flagged_by_count: int
    anomaly_explanation: str

class FraudResult(FraudDetectionResult):
    id: int
    transaction_id: str
    risk_score: float
    risk_tier: str
    is_anomaly_if: bool
    is_anomaly_dbscan: bool
    is_anomaly_zscore: bool
    ensemble_consensus: bool
    flagged_by_count: int
    anomaly_explanation: str
    created_at: datetime

    class Config:
        from_attributes = True

class DiscoveredPattern(BaseModel):
    pattern_id: str
    name: str
    description: str
    transaction_count: int
    first_seen: datetime
    last_seen: datetime
    risk_tier: str
    feature_signature: Dict[str, Any]
    sample_transactions: List[str]
    novelty_score: float
    severity_score: float

class TransactionChain(BaseModel):
    chain_id: str
    chain_type: str  # CYCLE, STAR, FUNNEL
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    total_amount: float
    transaction_count: int
    risk_score: float
    description: str

class DashboardStats(BaseModel):
    total_transactions: int
    flagged_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    detection_rate: float
    false_positive_estimate: float
    top_fraud_types: List[Dict[str, Any]]
    newly_discovered_patterns: int

class ApiResponse(BaseModel):
    success: bool
    data: Any
    timestamp: str
    processing_time_ms: int
    error: Optional[str] = None
