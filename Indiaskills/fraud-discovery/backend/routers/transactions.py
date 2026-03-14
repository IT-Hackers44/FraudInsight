from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime
from typing import List, Optional
from database import get_db, TransactionModel

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


# ─────────────────────────────────────────────
# Helper: SQLAlchemy row → plain dict
# Avoids from_orm / from_attributes issues entirely
# ─────────────────────────────────────────────
def tx_to_dict(t: TransactionModel) -> dict:
    return {
        "id":                 t.id,
        "transaction_id":     t.transaction_id,
        "user_id":            t.user_id,
        "amount":             float(t.amount) if t.amount is not None else 0.0,
        "currency":           t.currency,
        "merchant_id":        t.merchant_id,
        "merchant_category":  t.merchant_category,
        "timestamp":          t.timestamp.isoformat() if t.timestamp else None,
        "ip_address":         t.ip_address,
        "device_fingerprint": t.device_fingerprint,
        "location_lat":       float(t.location_lat) if t.location_lat is not None else None,
        "location_lon":       float(t.location_lon) if t.location_lon is not None else None,
        "payment_method":     t.payment_method,
        "is_international":   bool(t.is_international),
        "velocity_1h":        int(t.velocity_1h) if t.velocity_1h is not None else 0,
        "velocity_24h":       int(t.velocity_24h) if t.velocity_24h is not None else 0,
        "time_since_last_tx": float(t.time_since_last_tx) if t.time_since_last_tx is not None else 0.0,
        "amount_zscore":      float(t.amount_zscore) if t.amount_zscore is not None else 0.0,
        "fraud_label":        bool(t.fraud_label),
        "fraud_pattern":      t.fraud_pattern,
        "risk_score":         float(t.risk_score) if t.risk_score is not None else None,
        "risk_tier":          t.risk_tier,
        "is_flagged":         bool(t.is_flagged),
    }


# ─────────────────────────────────────────────
# POST /api/transactions/bulk-upload
# ─────────────────────────────────────────────
@router.post("/bulk-upload")
async def bulk_upload(transactions: List[dict], db: Session = Depends(get_db)):
    """Upload transactions in bulk"""
    try:
        added = 0
        skipped = 0
        for tx_data in transactions:
            existing = db.query(TransactionModel).filter(
                TransactionModel.transaction_id == tx_data.get('transaction_id')
            ).first()

            if not existing:
                # Strip unknown keys to prevent invalid keyword argument errors
                valid_cols = {c.name for c in TransactionModel.__table__.columns}
                clean_data = {k: v for k, v in tx_data.items() if k in valid_cols}
                tx = TransactionModel(**clean_data)
                db.add(tx)
                added += 1
            else:
                skipped += 1

        db.commit()
        return {
            "success": True,
            "message": f"Uploaded {added} new transactions ({skipped} skipped as duplicates)",
            "total_uploaded": added,
            "total_skipped": skipped,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": str(e),
            "error": "Bulk upload failed",
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }


# ─────────────────────────────────────────────
# GET /api/transactions
# ─────────────────────────────────────────────
@router.get("")
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    risk_tier: Optional[str] = Query(None, description="Filter by risk tier: LOW, MEDIUM, HIGH, CRITICAL"),
    is_flagged: Optional[bool] = Query(None, description="Filter flagged transactions only"),
    min_amount: Optional[float] = Query(None, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, description="Maximum transaction amount"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db)
):
    """Get paginated transactions with optional filtering"""
    try:
        query = db.query(TransactionModel)

        # ── Filters ──
        if risk_tier:
            query = query.filter(TransactionModel.risk_tier == risk_tier.upper())
        if is_flagged is not None:
            query = query.filter(TransactionModel.is_flagged == is_flagged)
        if min_amount is not None:
            query = query.filter(TransactionModel.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(TransactionModel.amount <= max_amount)
        if user_id:
            query = query.filter(TransactionModel.user_id == user_id)

        total = query.count()

        # ── Pagination ──
        skip = (page - 1) * limit
        transactions = (
            query
            .order_by(desc(TransactionModel.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

        return {
            "success": True,
            "data": [tx_to_dict(t) for t in transactions],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, (total + limit - 1) // limit)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "error": str(e),
            "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0},
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }


# ─────────────────────────────────────────────
# GET /api/transactions/flagged/all
# IMPORTANT: defined BEFORE /{transaction_id}
# so FastAPI does not treat "flagged" as a path param
# ─────────────────────────────────────────────
@router.get("/flagged/all")
async def get_flagged_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    min_risk_score: float = Query(0.0, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """Get all flagged / anomalous transactions sorted by risk score"""
    try:
        query = db.query(TransactionModel).filter(
            and_(
                TransactionModel.is_flagged == True,
                TransactionModel.risk_score >= min_risk_score
            )
        )

        total = query.count()
        skip = (page - 1) * limit
        transactions = (
            query
            .order_by(desc(TransactionModel.risk_score))
            .offset(skip)
            .limit(limit)
            .all()
        )

        return {
            "success": True,
            "data": [tx_to_dict(t) for t in transactions],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, (total + limit - 1) // limit)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# ─────────────────────────────────────────────
# GET /api/transactions/user/{user_id}
# IMPORTANT: defined BEFORE /{transaction_id}
# ─────────────────────────────────────────────
@router.get("/user/{user_id}")
async def get_transactions_by_user(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get all transactions for a specific user"""
    try:
        query = db.query(TransactionModel).filter(
            TransactionModel.user_id == user_id
        )

        total = query.count()
        skip = (page - 1) * limit
        transactions = (
            query
            .order_by(desc(TransactionModel.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

        if total == 0:
            return {
                "success": False,
                "data": [],
                "error": f"No transactions found for user '{user_id}'",
                "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0},
                "timestamp": datetime.utcnow().isoformat()
            }

        return {
            "success": True,
            "data": [tx_to_dict(t) for t in transactions],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, (total + limit - 1) // limit)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# ─────────────────────────────────────────────
# GET /api/transactions/{transaction_id}
# ─────────────────────────────────────────────
@router.get("/{transaction_id}")
async def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Get single transaction detail by transaction_id"""
    try:
        transaction = db.query(TransactionModel).filter(
            TransactionModel.transaction_id == transaction_id
        ).first()

        if not transaction:
            return {
                "success": False,
                "data": None,
                "error": f"Transaction '{transaction_id}' not found",
                "timestamp": datetime.utcnow().isoformat(),
                "processing_time_ms": 0
            }

        return {
            "success": True,
            "data": tx_to_dict(transaction),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 0
        }


# ─────────────────────────────────────────────
# DELETE /api/transactions/{transaction_id}
# ─────────────────────────────────────────────
@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Delete a single transaction by transaction_id"""
    try:
        transaction = db.query(TransactionModel).filter(
            TransactionModel.transaction_id == transaction_id
        ).first()

        if not transaction:
            return {
                "success": False,
                "error": f"Transaction '{transaction_id}' not found",
                "timestamp": datetime.utcnow().isoformat()
            }

        db.delete(transaction)
        db.commit()

        return {
            "success": True,
            "message": f"Transaction '{transaction_id}' deleted successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# ─────────────────────────────────────────────
# DELETE /api/transactions
# ─────────────────────────────────────────────
@router.delete("")
async def delete_all_transactions(db: Session = Depends(get_db)):
    """Delete ALL transactions — admin/reset endpoint"""
    try:
        deleted_count = db.query(TransactionModel).count()
        db.query(TransactionModel).delete()
        db.commit()

        return {
            "success": True,
            "message": f"Deleted {deleted_count} transactions successfully",
            "deleted_count": deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }