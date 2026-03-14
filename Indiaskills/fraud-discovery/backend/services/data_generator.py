import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np
from faker import Faker

fake = Faker()

def convert_numpy_types(obj):
    """Recursively convert all NumPy types to Python native types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj


class TransactionGenerator:
    def __init__(self, seed: int = 42):
        """Initialize generator with optional seed for reproducibility"""
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

        self.merchants = [
            {"id": f"M{i:04d}", "category": random.choice([
                "Electronics", "Groceries", "Travel", "Entertainment",
                "Healthcare", "Restaurants", "Utilities", "Retail"
            ])}
            for i in range(200)
        ]

        self.users = [f"U{i:05d}" for i in range(500)]
        self.payment_methods = ["credit_card", "debit_card", "paypal", "wire_transfer", "crypto"]
        self.currencies = ["USD", "EUR", "GBP", "INR"]

    def generate_transactions(self, count: int = 10000) -> List[Dict]:
        """Generate synthetic transactions with embedded fraud patterns"""
        transactions = []
        user_tx_history = {u: [] for u in self.users}

        base_time = datetime.now() - timedelta(days=30)

        fraud_count = int(count * 0.05)  # 5% fraud rate
        fraud_indices = random.sample(range(count), fraud_count)
        fraud_set = set(fraud_indices)

        for idx in range(count):
            tx_time = base_time + timedelta(
                days=random.randint(0, 29),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            user_id = random.choice(self.users)
            merchant = random.choice(self.merchants)

            # Get user history for velocity calculation
            user_recent = [t for t in user_tx_history[user_id]
                          if (tx_time - t['timestamp']).total_seconds() < 86400]  # 24h
            user_recent_1h = [t for t in user_recent
                             if (tx_time - t['timestamp']).total_seconds() < 3600]  # 1h

            time_since_last = (tx_time - user_tx_history[user_id][-1]['timestamp']).total_seconds() if user_tx_history[user_id] else 0

            # Generate fraud pattern
            is_fraud = idx in fraud_set
            fraud_pattern = None

            if is_fraud:
                fraud_pattern = random.choice([
                    "velocity_burst", "geo_anomaly", "dormant_account",
                    "round_trip", "merchant_collusion", "night_owl",
                    "device_swap", "micro_test_sweep"
                ])

            # Generate transaction based on pattern
            amount = self._generate_amount(fraud_pattern)

            # Calculate zscores
            user_amounts = [t['amount'] for t in user_tx_history[user_id]]
            if user_amounts:
                mean_amount = np.mean(user_amounts)
                std_amount = np.std(user_amounts) or 1
                amount_zscore = abs((amount - mean_amount) / std_amount)
            else:
                amount_zscore = 0

            velocity_zscore = len(user_recent_1h) if len(user_recent_1h) > 0 else 0

            # Geographic deviation
            is_international = random.random() < (0.3 if is_fraud and fraud_pattern == "geo_anomaly" else 0.1)

            # Device fingerprint
            num_devices = random.randint(1, 10)
            device_fp = f"DEV_{random.randint(0, 1000 if is_fraud and fraud_pattern == 'device_swap' else 100):04d}"

            tx = {
                "transaction_id": f"TX{idx:010d}",
                "user_id": user_id,
                "amount": round(amount, 2),
                "currency": random.choice(self.currencies),
                "merchant_id": merchant["id"],
                "merchant_category": merchant["category"],
                "timestamp": tx_time,
                "ip_address": fake.ipv4(),
                "device_fingerprint": device_fp,
                "location_lat": round(random.uniform(-90, 90), 4),
                "location_lon": round(random.uniform(-180, 180), 4),
                "payment_method": random.choice(self.payment_methods),
                "is_international": is_international,
                "velocity_1h": len(user_recent_1h),
                "velocity_24h": len(user_recent),
                "time_since_last_tx": int(time_since_last),
                "amount_zscore": round(amount_zscore, 3),
                "fraud_label": is_fraud,
                "fraud_pattern": fraud_pattern
            }

            transactions.append(tx)
            user_tx_history[user_id].append(tx)

        # Sort by timestamp
        transactions.sort(key=lambda x: x["timestamp"])

        return transactions

    def _generate_amount(self, fraud_pattern: str = None) -> float:
        """Generate transaction amount based on fraud pattern"""
        if fraud_pattern == "dormant_account":
            return float(random.uniform(1000, 5000))
        elif fraud_pattern == "night_owl":
            return float(random.uniform(500, 3000))
        elif fraud_pattern == "round_trip":
            return float(random.uniform(500, 2000))
        elif fraud_pattern == "merchant_collusion":
            return float(random.uniform(100, 500))
        elif fraud_pattern == "micro_test_sweep":
            amount = random.uniform(10, 100) if random.random() < 0.5 else random.uniform(2000, 5000)
            return float(amount)
        else:
            # Normal transaction with some skew
            amount = np.random.gamma(shape=2, scale=50)
            return float(min(amount, 5000))  # Cap at 5000

def generate_fraud_transactions(size: int = 10000) -> List[Dict]:
    """Public function to generate transactions"""
    generator = TransactionGenerator()
    transactions = generator.generate_transactions(size)

    # Convert all values: datetime to ISO string and NumPy types to Python native types
    result = []
    for tx in transactions:
        tx = convert_numpy_types(tx)
        tx['timestamp'] = tx['timestamp'].isoformat() if isinstance(tx['timestamp'], datetime) else tx['timestamp']
        result.append(tx)

    return result

if __name__ == "__main__":
    transactions = generate_fraud_transactions(100)
    print(f"Generated {len(transactions)} transactions")
    print(json.dumps(transactions[0], indent=2))
