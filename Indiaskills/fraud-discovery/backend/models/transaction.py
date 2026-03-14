from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TransactionCreate(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    timestamp: datetime
    ip_address: str
    device_fingerprint: str
    location_lat: float
    location_lon: float
    payment_method: str
    is_international: bool
    velocity_1h: int
    velocity_24h: int
    time_since_last_tx: int
    amount_zscore: float
    fraud_label: bool = False

class Transaction(TransactionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    timestamp: datetime
    ip_address: str
    device_fingerprint: str
    location_lat: float
    location_lon: float
    payment_method: str
    is_international: bool
    velocity_1h: int
    velocity_24h: int
    time_since_last_tx: int
    amount_zscore: float
    fraud_label: bool
    created_at: datetime
