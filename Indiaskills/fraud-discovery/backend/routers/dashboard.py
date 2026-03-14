from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db, TransactionModel, FraudResultModel, PatternModel, ChainModel
import time

router = APIRouter(prefix="/api", tags=["dashboard"])

@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard summary statistics"""
    start_time = time.time()

    try:
        total_transactions = db.query(func.count(TransactionModel.id)).scalar() or 0

        # Fraud statistics
        fraud_results = db.query(FraudResultModel).all()
        flagged_count = len(fraud_results)

        critical_count = len([f for f in fraud_results if f.risk_tier == "CRITICAL"])
        high_count = len([f for f in fraud_results if f.risk_tier == "HIGH"])
        medium_count = len([f for f in fraud_results if f.risk_tier == "MEDIUM"])
        low_count = len([f for f in fraud_results if f.risk_tier == "LOW"])

        detection_rate = (flagged_count / total_transactions * 100) if total_transactions > 0 else 0

        # Ground truth comparison (if fraud_label available)
        actual_fraud = db.query(func.count(TransactionModel.id)).filter(
            TransactionModel.fraud_label == True
        ).scalar() or 0

        false_positive_estimate = max(0, (flagged_count - actual_fraud) / flagged_count * 100) if flagged_count > 0 else 0

        # Top fraud types
        top_patterns = db.query(PatternModel).order_by(PatternModel.severity_score.desc()).limit(5).all()
        top_fraud_types = [
            {
                "name": p.name,
                "count": p.transaction_count,
                "risk_tier": p.risk_tier,
                "severity": p.severity_score
            }
            for p in top_patterns
        ]

        # Newly discovered patterns (last 24h)
        yesterday = datetime.utcnow() - timedelta(days=1)
        new_patterns = db.query(func.count(PatternModel.id)).filter(
            PatternModel.created_at >= yesterday
        ).scalar() or 0

        processing_time = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "data": {
                "total_transactions": total_transactions,
                "flagged_count": flagged_count,
                "critical_count": critical_count,
                "high_count": high_count,
                "medium_count": medium_count,
                "low_count": low_count,
                "detection_rate": round(detection_rate, 2),
                "false_positive_estimate": round(false_positive_estimate, 2),
                "top_fraud_types": top_fraud_types,
                "newly_discovered_patterns": new_patterns,
                "actual_fraud_count": actual_fraud
            },
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": processing_time
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }

@router.get("/dashboard/risk-breakdown")
async def get_risk_breakdown(db: Session = Depends(get_db)):
    """Get risk tier breakdown"""
    try:
        fraud_results = db.query(FraudResultModel).all()

        risk_tiers = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }

        for fr in fraud_results:
            risk_tiers[fr.risk_tier] += 1

        return {
            "success": True,
            "data": risk_tiers,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

@router.get("/alerts")
async def get_recent_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent CRITICAL and HIGH alerts"""
    try:
        critical_alerts = db.query(FraudResultModel).filter(
            FraudResultModel.risk_tier == "CRITICAL"
        ).order_by(FraudResultModel.created_at.desc()).limit(limit).all()

        high_alerts = db.query(FraudResultModel).filter(
            FraudResultModel.risk_tier == "HIGH"
        ).order_by(FraudResultModel.created_at.desc()).limit(limit - len(critical_alerts)).all()

        alerts = []
        for alert in critical_alerts + high_alerts:
            tx = db.query(TransactionModel).filter(
                TransactionModel.transaction_id == alert.transaction_id
            ).first()

            if tx:
                alerts.append({
                    "transaction_id": alert.transaction_id,
                    "risk_tier": alert.risk_tier,
                    "risk_score": alert.risk_score,
                    "amount": tx.amount,
                    "user_id": tx.user_id,
                    "merchant_id": tx.merchant_id,
                    "timestamp": tx.timestamp.isoformat() if isinstance(tx.timestamp, datetime) else tx.timestamp,
                    "explanation": alert.anomaly_explanation,
                    "created_at": alert.created_at.isoformat() if isinstance(alert.created_at, datetime) else alert.created_at
                })

        return {
            "success": True,
            "data": alerts[:limit],
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

@router.get("/patterns")
async def get_patterns(db: Session = Depends(get_db)):
    """Get discovered fraud patterns"""
    try:
        patterns = db.query(PatternModel).order_by(
            PatternModel.severity_score.desc()
        ).limit(10).all()

        pattern_data = []
        for p in patterns:
            pattern_data.append({
                "pattern_id": p.pattern_id,
                "name": p.name,
                "description": p.description,
                "transaction_count": p.transaction_count,
                "first_seen": p.first_seen.isoformat() if isinstance(p.first_seen, datetime) else p.first_seen,
                "last_seen": p.last_seen.isoformat() if isinstance(p.last_seen, datetime) else p.last_seen,
                "risk_tier": p.risk_tier,
                "feature_signature": p.feature_signature,
                "sample_transactions": p.sample_transactions,
                "novelty_score": p.novelty_score,
                "severity_score": p.severity_score
            })

        return {
            "success": True,
            "data": pattern_data,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

@router.get("/chains")
async def get_chains(db: Session = Depends(get_db)):
    """Get suspicious transaction chains"""
    try:
        chains = db.query(ChainModel).order_by(
            ChainModel.risk_score.desc()
        ).limit(20).all()

        chain_data = []
        for c in chains:
            chain_data.append({
                "chain_id": c.chain_id,
                "chain_type": c.chain_type,
                "nodes": c.nodes,
                "edges": c.edges,
                "total_amount": c.total_amount,
                "transaction_count": c.transaction_count,
                "risk_score": c.risk_score,
                "description": c.description,
                "created_at": c.created_at.isoformat() if isinstance(c.created_at, datetime) else c.created_at
            })

        return {
            "success": True,
            "data": chain_data,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "processing_time_ms": 0
    }
