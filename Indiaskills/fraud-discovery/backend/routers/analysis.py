from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
import numpy as np
import json
import time
from database import get_db, TransactionModel, FraudResultModel, PatternModel, ChainModel
from services.data_generator import generate_fraud_transactions
from services.feature_engine import FeatureEngine
from services.anomaly_detector import AnomalyDetector
from services.pattern_miner import PatternMiner
from services.chain_analyzer import ChainAnalyzer

router = APIRouter(prefix="/api", tags=["analysis"])


# ─────────────────────────────────────────────
# POST /api/generate
# ─────────────────────────────────────────────
@router.post("/generate")
async def generate_data(size: int = 10000, db: Session = Depends(get_db)):
    """Generate synthetic transaction data"""
    start_time = time.time()

    try:
        # Clear existing data
        db.query(TransactionModel).delete()
        db.commit()

        # Generate transactions
        transactions = generate_fraud_transactions(min(size, 100000))

        # Insert into database
        valid_cols = {c.name for c in TransactionModel.__table__.columns}
        for tx in transactions:
            tx['timestamp'] = datetime.fromisoformat(tx['timestamp'])
            clean = {k: v for k, v in tx.items() if k in valid_cols}
            db.add(TransactionModel(**clean))

        db.commit()

        fraud_count = sum(1 for t in transactions if t.get('fraud_label', False))
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "data": {
                "generated_count": len(transactions),
                "fraud_count": fraud_count,
                "fraud_rate": round(fraud_count / max(len(transactions), 1), 4),
            },
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": processing_time
        }

    except Exception as e:
        db.rollback()
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }


# ─────────────────────────────────────────────
# POST /api/analyze
# ─────────────────────────────────────────────
@router.post("/analyze")
async def run_analysis(db: Session = Depends(get_db)):
    """Run full fraud detection analysis pipeline"""
    start_time = time.time()

    try:
        # ── 1. Load transactions ──
        transactions = db.query(TransactionModel).all()

        if not transactions:
            return {
                "success": False,
                "error": "No transactions found. Run /api/generate first.",
                "timestamp": datetime.utcnow().isoformat(),
                "processing_time_ms": 0
            }

        # ── 2. Build DataFrame ──
        tx_data = []
        for t in transactions:
            tx_data.append({
                'id':                 t.id,
                'transaction_id':     t.transaction_id,
                'user_id':            t.user_id,
                'amount':             float(t.amount) if t.amount else 0.0,
                'currency':           t.currency or 'USD',
                'merchant_id':        t.merchant_id or '',
                'merchant_category':  t.merchant_category or 'unknown',
                'timestamp':          t.timestamp.isoformat() if isinstance(t.timestamp, datetime) else str(t.timestamp),
                'ip_address':         t.ip_address or '',
                'device_fingerprint': t.device_fingerprint or '',
                'location_lat':       float(t.location_lat) if t.location_lat else 0.0,
                'location_lon':       float(t.location_lon) if t.location_lon else 0.0,
                'payment_method':     t.payment_method or 'unknown',
                'is_international':   bool(t.is_international),
                'velocity_1h':        int(t.velocity_1h) if t.velocity_1h else 0,
                'velocity_24h':       int(t.velocity_24h) if t.velocity_24h else 0,
                'time_since_last_tx': float(t.time_since_last_tx) if t.time_since_last_tx else 0.0,
                'amount_zscore':      float(t.amount_zscore) if t.amount_zscore else 0.0,
                'fraud_label':        bool(t.fraud_label),
            })

        df = pd.DataFrame(tx_data)

        # ── 3. Feature engineering ──
        feature_engine = FeatureEngine()
        features, metadata = feature_engine.fit_transform(df)
        # features is now a clean (n_samples, n_features) float64 array

        # ── 4. Anomaly detection ──
        detector = AnomalyDetector(contamination=0.05)
        detector.fit(features)
        # predictions = 1D int array (1=anomaly), risk_scores = 1D float array
        predictions, risk_scores, anomaly_results = detector.predict_ensemble(features)

        # ── 5. Update transactions with risk scores ──
        for result in anomaly_results:
            idx = result['index']
            tx  = transactions[idx]
            tx.risk_score = float(result['risk_score'])
            tx.risk_tier  = result['risk_tier']
            tx.is_flagged = bool(result['ensemble_consensus'])

        db.commit()

        # ── 6. Store fraud results ──
        db.query(FraudResultModel).delete()
        for result in anomaly_results:
            idx = result['index']
            tx  = transactions[idx]
            db.add(FraudResultModel(
                transaction_id    = tx.transaction_id,
                risk_score        = float(result['risk_score']),
                risk_tier         = result['risk_tier'],
                is_anomaly_if     = bool(result['is_anomaly_if']),
                is_anomaly_dbscan = bool(result['is_anomaly_dbscan']),
                is_anomaly_zscore = bool(result['is_anomaly_zscore']),
                ensemble_consensus= bool(result['ensemble_consensus']),
                flagged_by_count  = int(result['flagged_by_count']),
                anomaly_explanation = result.get('anomaly_explanation', ''),
            ))
        db.commit()

        # ── 7. Pattern mining ──
        # ✅ FIX: pass predictions (1D int array) and risk_scores (1D float array)
        # NOT anomaly_results (list of dicts) and NOT features (2D matrix)
        pattern_miner = PatternMiner()
        patterns = pattern_miner.discover_patterns(
            transactions_df = df,
            flagged_indices = predictions,    # 1D array: 1=flagged, 0=normal
            risk_scores     = risk_scores,    # 1D array: 0.0–1.0
        )

        # Store patterns
        db.query(PatternModel).delete()
        for pattern in patterns:
            db.add(PatternModel(
                pattern_id        = pattern['pattern_id'],
                name              = pattern['name'],
                description       = pattern['description'],
                pattern_type      = pattern.get('pattern_type', 'unknown'),
                transaction_count = int(pattern['transaction_count']),
                affected_users    = int(pattern.get('affected_users', 0)),
                risk_tier         = pattern['risk_tier'],
                severity_score    = float(pattern.get('severity_score', 0.0)),
                # sample_transaction_ids is a list — store as JSON string
                sample_transactions = json.dumps(pattern.get('sample_transaction_ids', [])),
                indicators          = json.dumps(pattern.get('indicators', {})),
                first_seen          = datetime.utcnow(),
                is_new              = bool(pattern.get('is_new', True)),
            ))
        db.commit()

        # ── 8. Chain analysis ──
        chain_analyzer = ChainAnalyzer()
        chains, graph_data = chain_analyzer.analyze_chains(df, anomaly_results)

        db.query(ChainModel).delete()
        for chain in chains:
            db.add(ChainModel(
                chain_id          = chain['chain_id'],
                chain_type        = chain['chain_type'],
                nodes             = json.dumps(chain.get('nodes', [])),
                edges             = json.dumps(chain.get('edges', [])),
                total_amount      = float(chain.get('total_amount', 0.0)),
                transaction_count = int(chain.get('transaction_count', 0)),
                risk_score        = float(chain.get('risk_score', 0.0)),
                description       = chain.get('description', ''),
            ))
        db.commit()

        processing_time = int((time.time() - start_time) * 1000)

        # Compute summary stats
        flagged_count  = int(predictions.sum())
        total          = len(transactions)
        risk_breakdown = {
            'CRITICAL': int(sum(1 for r in anomaly_results if r['risk_tier'] == 'CRITICAL')),
            'HIGH':     int(sum(1 for r in anomaly_results if r['risk_tier'] == 'HIGH')),
            'MEDIUM':   int(sum(1 for r in anomaly_results if r['risk_tier'] == 'MEDIUM')),
            'LOW':      int(sum(1 for r in anomaly_results if r['risk_tier'] == 'LOW')),
        }

        return {
            "success": True,
            "data": {
                "total_transactions":  total,
                "flagged_count":       flagged_count,
                "detection_rate":      round(flagged_count / max(total, 1), 4),
                "risk_breakdown":      risk_breakdown,
                "detected_patterns":   len(patterns),
                "detected_chains":     len(chains),
                "feature_count":       metadata.get('feature_count', 0),
                "processing_time_ms":  processing_time,
            },
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": processing_time
        }

    except Exception as e:
        db.rollback()
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }