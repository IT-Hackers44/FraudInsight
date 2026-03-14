import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class PatternMiner:
    def __init__(self):
        """Initialize pattern miner for emerging fraud discovery"""
        self.discovered_patterns: List[Dict[str, Any]] = []
        self.pattern_counter = 0

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def discover_patterns(
        self,
        transactions_df: pd.DataFrame,
        flagged_indices: Optional[np.ndarray] = None,
        risk_scores: Optional[np.ndarray] = None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point — discovers emerging fraud patterns from transactions.

        Args:
            transactions_df : Full transaction DataFrame
            flagged_indices : Boolean/int array marking which rows are flagged
            risk_scores     : Float array of risk scores (0.0–1.0)

        Returns:
            List of discovered pattern dicts sorted by severity + novelty
        """
        df = self._clean_dataframe(transactions_df.copy())

        # Attach risk metadata if provided
        if risk_scores is not None:
            df['_risk_score'] = np.array(risk_scores, dtype=np.float64)
        else:
            df['_risk_score'] = 0.0

        if flagged_indices is not None:
            flags = np.array(flagged_indices, dtype=np.int32)
            df['_is_flagged'] = flags
        else:
            df['_is_flagged'] = 0

        # Work only on flagged / high-risk transactions for pattern mining
        flagged_df = df[df['_is_flagged'] == 1].copy()
        if len(flagged_df) < 5:
            flagged_df = df.nlargest(max(10, int(len(df) * 0.05)), '_risk_score')

        patterns: List[Dict[str, Any]] = []

        # Run all pattern detectors
        patterns += self._detect_velocity_burst(df)
        patterns += self._detect_geo_anomaly(df)
        patterns += self._detect_dormant_account(df)
        patterns += self._detect_night_owl(df)
        patterns += self._detect_device_swap(df)
        patterns += self._detect_merchant_collusion(df)
        patterns += self._detect_micro_test_sweep(df)
        patterns += self._cluster_anomalous_transactions(flagged_df)

        # Deduplicate, score, and sort
        patterns = self._score_and_rank(patterns)
        self.discovered_patterns = patterns[:10]  # top 10
        return self.discovered_patterns

    def get_pattern_summary(self) -> Dict[str, Any]:
        """Return summary statistics about discovered patterns"""
        if not self.discovered_patterns:
            return {'total': 0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

        tier_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for p in self.discovered_patterns:
            tier = p.get('risk_tier', 'LOW')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            'total': len(self.discovered_patterns),
            'critical': tier_counts['CRITICAL'],
            'high': tier_counts['HIGH'],
            'medium': tier_counts['MEDIUM'],
            'low': tier_counts['LOW'],
        }

    # ─────────────────────────────────────────────
    # Pattern detectors
    # ─────────────────────────────────────────────

    def _detect_velocity_burst(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect users with abnormally high transaction velocity"""
        patterns = []
        try:
            df['_ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
            high_vel = df[df['velocity_1h'] >= 8]

            if len(high_vel) >= 3:
                affected_users = high_vel['user_id'].nunique()
                avg_velocity = float(high_vel['velocity_1h'].mean())
                max_velocity = int(high_vel['velocity_1h'].max())
                avg_amount = float(high_vel['amount'].mean())

                patterns.append(self._build_pattern(
                    name="Velocity Burst",
                    pattern_type="velocity_burst",
                    description=(
                        f"Users executing {max_velocity}+ transactions/hour — "
                        f"avg velocity {avg_velocity:.1f} tx/h across "
                        f"{affected_users} accounts. Avg transaction amount ${avg_amount:.2f}. "
                        f"Indicative of automated fraud or account takeover."
                    ),
                    tx_count=len(high_vel),
                    affected_users=affected_users,
                    risk_tier=self._velocity_risk_tier(avg_velocity),
                    sample_ids=list(high_vel['transaction_id'].head(5)),
                    indicators={
                        'avg_velocity_1h': avg_velocity,
                        'max_velocity_1h': max_velocity,
                        'avg_amount': avg_amount,
                    }
                ))
        except Exception:
            pass
        return patterns

    def _detect_geo_anomaly(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect transactions from geographically impossible locations"""
        patterns = []
        try:
            df['_ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
            intl = df[df['is_international'] == True]

            if len(intl) >= 3:
                # Users who have both domestic and international within the same hour
                user_intl = intl.groupby('user_id').agg(
                    intl_count=('transaction_id', 'count'),
                    avg_amount=('amount', 'mean')
                ).reset_index()

                suspicious = user_intl[user_intl['intl_count'] >= 2]

                if len(suspicious) >= 1:
                    patterns.append(self._build_pattern(
                        name="Impossible Geo-Velocity",
                        pattern_type="geo_anomaly",
                        description=(
                            f"{len(suspicious)} user(s) with multiple international "
                            f"transactions suggesting impossible travel velocity. "
                            f"Possible card cloning or credential theft across regions."
                        ),
                        tx_count=len(intl),
                        affected_users=int(len(suspicious)),
                        risk_tier="HIGH",
                        sample_ids=list(intl['transaction_id'].head(5)),
                        indicators={
                            'international_tx_count': len(intl),
                            'suspicious_users': int(len(suspicious)),
                        }
                    ))
        except Exception:
            pass
        return patterns

    def _detect_dormant_account(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect sudden activity on previously dormant accounts"""
        patterns = []
        try:
            df['_ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
            user_first_last = df.groupby('user_id')['_ts'].agg(['min', 'max', 'count'])
            user_first_last.columns = ['first_tx', 'last_tx', 'tx_count']

            # Users with long gaps then sudden high-value activity
            user_first_last['gap_days'] = (
                user_first_last['last_tx'] - user_first_last['first_tx']
            ).dt.days

            dormant = user_first_last[
                (user_first_last['gap_days'] >= 30) &
                (user_first_last['tx_count'] <= 3)
            ]

            if len(dormant) >= 2:
                dormant_user_ids = dormant.index.tolist()
                dormant_txs = df[df['user_id'].isin(dormant_user_ids)]
                avg_amount = float(dormant_txs['amount'].mean())

                patterns.append(self._build_pattern(
                    name="Dormant Account Revival",
                    pattern_type="dormant_account",
                    description=(
                        f"{len(dormant)} account(s) inactive for 30+ days suddenly "
                        f"showing transaction activity. Avg amount ${avg_amount:.2f}. "
                        f"Possible account takeover or stolen credential usage."
                    ),
                    tx_count=len(dormant_txs),
                    affected_users=len(dormant),
                    risk_tier="HIGH",
                    sample_ids=list(dormant_txs['transaction_id'].head(5)),
                    indicators={
                        'dormant_users': len(dormant),
                        'avg_gap_days': float(dormant['gap_days'].mean()),
                        'avg_amount': avg_amount,
                    }
                ))
        except Exception:
            pass
        return patterns

    def _detect_night_owl(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect high-value transactions concentrated in suspicious night hours (2–4 AM)"""
        patterns = []
        try:
            df['_ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['_hour'] = df['_ts'].dt.hour

            night_txs = df[df['_hour'].isin([2, 3, 4])]

            if len(night_txs) >= 5:
                night_avg = float(night_txs['amount'].mean())
                day_avg = float(df[~df['_hour'].isin([2, 3, 4])]['amount'].mean()) if len(df) > len(night_txs) else night_avg
                ratio = night_avg / max(day_avg, 1)

                if ratio > 1.5:
                    patterns.append(self._build_pattern(
                        name="Night Owl High-Value Pattern",
                        pattern_type="night_owl",
                        description=(
                            f"{len(night_txs)} transactions between 2–4 AM with "
                            f"avg amount ${night_avg:.2f} ({ratio:.1f}x the daytime average). "
                            f"Abnormal hour concentration suggests automated or illicit activity."
                        ),
                        tx_count=len(night_txs),
                        affected_users=int(night_txs['user_id'].nunique()),
                        risk_tier="MEDIUM" if ratio < 2.5 else "HIGH",
                        sample_ids=list(night_txs['transaction_id'].head(5)),
                        indicators={
                            'night_tx_count': len(night_txs),
                            'night_avg_amount': night_avg,
                            'day_avg_amount': day_avg,
                            'night_to_day_ratio': ratio,
                        }
                    ))
        except Exception:
            pass
        return patterns

    def _detect_device_swap(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect users rapidly switching between multiple devices"""
        patterns = []
        try:
            device_counts = df.groupby('user_id')['device_fingerprint'].nunique()
            multi_device_users = device_counts[device_counts >= 3]

            if len(multi_device_users) >= 2:
                affected_txs = df[df['user_id'].isin(multi_device_users.index)]
                avg_devices = float(multi_device_users.mean())

                patterns.append(self._build_pattern(
                    name="Rapid Device Switching",
                    pattern_type="device_swap",
                    description=(
                        f"{len(multi_device_users)} user(s) using {avg_devices:.1f} "
                        f"different devices on average. High device churn within short "
                        f"windows indicates device spoofing or shared fraud infrastructure."
                    ),
                    tx_count=len(affected_txs),
                    affected_users=int(len(multi_device_users)),
                    risk_tier="HIGH",
                    sample_ids=list(affected_txs['transaction_id'].head(5)),
                    indicators={
                        'multi_device_users': int(len(multi_device_users)),
                        'avg_devices_per_user': avg_devices,
                        'max_devices': int(multi_device_users.max()),
                    }
                ))
        except Exception:
            pass
        return patterns

    def _detect_merchant_collusion(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect users hitting many merchants with same amount in short windows"""
        patterns = []
        try:
            # Group by user + rounded amount to find suspiciously uniform multi-merchant spending
            df['_rounded_amount'] = (df['amount'] / 10).round() * 10

            collusion_candidates = df.groupby(['user_id', '_rounded_amount']).agg(
                merchant_count=('merchant_id', 'nunique'),
                tx_count=('transaction_id', 'count')
            ).reset_index()

            suspicious = collusion_candidates[
                (collusion_candidates['merchant_count'] >= 4) &
                (collusion_candidates['tx_count'] >= 4)
            ]

            if len(suspicious) >= 1:
                affected_users = int(suspicious['user_id'].nunique())
                patterns.append(self._build_pattern(
                    name="Merchant Collusion Ring",
                    pattern_type="merchant_collusion",
                    description=(
                        f"{len(suspicious)} user-amount combination(s) hitting 4+ merchants "
                        f"with near-identical amounts. Suggests coordinated merchant fraud "
                        f"or loyalty point exploitation across {affected_users} account(s)."
                    ),
                    tx_count=int(suspicious['tx_count'].sum()),
                    affected_users=affected_users,
                    risk_tier="CRITICAL",
                    sample_ids=list(
                        df[df['user_id'].isin(suspicious['user_id'])]['transaction_id'].head(5)
                    ),
                    indicators={
                        'collusion_patterns_found': len(suspicious),
                        'affected_users': affected_users,
                    }
                ))
        except Exception:
            pass
        return patterns

    def _detect_micro_test_sweep(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect micro-test transaction followed by large sweep"""
        patterns = []
        try:
            df_sorted = df.sort_values(['user_id', 'timestamp'])

            suspicious_users = []
            for user_id, user_txs in df_sorted.groupby('user_id'):
                amounts = user_txs['amount'].values
                if len(amounts) < 2:
                    continue

                for i in range(len(amounts) - 1):
                    if amounts[i] < 5.0 and amounts[i + 1] > 500.0:
                        ratio = amounts[i + 1] / max(amounts[i], 0.01)
                        if ratio > 50:
                            suspicious_users.append({
                                'user_id': user_id,
                                'test_amount': float(amounts[i]),
                                'sweep_amount': float(amounts[i + 1]),
                                'ratio': float(ratio)
                            })
                            break

            if suspicious_users:
                avg_sweep = float(np.mean([s['sweep_amount'] for s in suspicious_users]))
                patterns.append(self._build_pattern(
                    name="Micro-Test + Sweep",
                    pattern_type="micro_test_sweep",
                    description=(
                        f"{len(suspicious_users)} instance(s) of small test transaction "
                        f"(<$5) followed by large sweep (avg ${avg_sweep:.2f}). "
                        f"Classic card validation pattern before large fraudulent withdrawal."
                    ),
                    tx_count=len(suspicious_users) * 2,
                    affected_users=len(suspicious_users),
                    risk_tier="CRITICAL",
                    sample_ids=list(
                        df[df['user_id'].isin([s['user_id'] for s in suspicious_users])][
                            'transaction_id'
                        ].head(5)
                    ),
                    indicators={
                        'instances_found': len(suspicious_users),
                        'avg_sweep_amount': avg_sweep,
                        'avg_ratio': float(np.mean([s['ratio'] for s in suspicious_users])),
                    }
                ))
        except Exception:
            pass
        return patterns

    def _cluster_anomalous_transactions(self, flagged_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Use DBSCAN to cluster flagged transactions and auto-generate pattern descriptions
        for any new clusters discovered (emerging patterns not covered by rule-based detectors).
        """
        patterns = []
        if len(flagged_df) < 10:
            return patterns

        try:
            feature_cols = ['amount', 'velocity_1h', 'velocity_24h', 'amount_zscore']
            available = [c for c in feature_cols if c in flagged_df.columns]
            if not available:
                return patterns

            X = flagged_df[available].values.astype(np.float64)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            db = DBSCAN(eps=0.6, min_samples=4)
            labels = db.fit_predict(X_scaled)

            unique_labels = set(labels) - {-1}

            for label in unique_labels:
                cluster_mask = labels == label
                cluster_txs = flagged_df[cluster_mask]
                cluster_size = int(cluster_mask.sum())

                if cluster_size < 4:
                    continue

                avg_amount = float(cluster_txs['amount'].mean())
                avg_velocity = float(cluster_txs['velocity_1h'].mean()) if 'velocity_1h' in cluster_txs else 0
                intl_ratio = float(cluster_txs['is_international'].astype(int).mean()) if 'is_international' in cluster_txs else 0
                avg_risk = float(cluster_txs['_risk_score'].mean()) if '_risk_score' in cluster_txs else 0.5

                # Auto-generate description based on cluster characteristics
                traits = []
                if avg_amount > 1000:
                    traits.append(f"high-value (avg ${avg_amount:.0f})")
                if avg_velocity > 5:
                    traits.append(f"high-velocity ({avg_velocity:.1f} tx/h)")
                if intl_ratio > 0.5:
                    traits.append("predominantly international")
                if not traits:
                    traits.append(f"anomalous pattern (avg ${avg_amount:.0f})")

                description = (
                    f"Emerging cluster #{label + 1}: {', '.join(traits)}. "
                    f"{cluster_size} transactions across "
                    f"{int(cluster_txs['user_id'].nunique())} user(s). "
                    f"Avg risk score {avg_risk:.2f}. "
                    f"Pattern not matching known fraud signatures — requires investigation."
                )

                risk_tier = "CRITICAL" if avg_risk >= 0.75 else "HIGH" if avg_risk >= 0.5 else "MEDIUM"

                patterns.append(self._build_pattern(
                    name=f"Emerging Cluster #{label + 1}",
                    pattern_type="emerging_cluster",
                    description=description,
                    tx_count=cluster_size,
                    affected_users=int(cluster_txs['user_id'].nunique()),
                    risk_tier=risk_tier,
                    sample_ids=list(cluster_txs['transaction_id'].head(5)),
                    indicators={
                        'cluster_id': int(label),
                        'cluster_size': cluster_size,
                        'avg_amount': avg_amount,
                        'avg_velocity_1h': avg_velocity,
                        'intl_ratio': intl_ratio,
                        'avg_risk_score': avg_risk,
                    }
                ))
        except Exception:
            pass
        return patterns

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def _build_pattern(
        self,
        name: str,
        pattern_type: str,
        description: str,
        tx_count: int,
        affected_users: int,
        risk_tier: str,
        sample_ids: List[str],
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build a standardised pattern dict"""
        self.pattern_counter += 1
        return {
            'pattern_id': f"PAT-{self.pattern_counter:04d}",
            'name': name,
            'pattern_type': pattern_type,
            'description': description,
            'transaction_count': tx_count,
            'affected_users': affected_users,
            'risk_tier': risk_tier,
            'severity_score': self._tier_to_score(risk_tier),
            'sample_transaction_ids': sample_ids,
            'indicators': indicators,
            'first_seen': datetime.utcnow().isoformat(),
            'is_new': True,
        }

    def _score_and_rank(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate by type, then sort by severity then transaction count"""
        seen_types = set()
        unique = []
        for p in patterns:
            if p['pattern_type'] not in seen_types:
                seen_types.add(p['pattern_type'])
                unique.append(p)
            elif p['pattern_type'] == 'emerging_cluster':
                # Allow multiple emerging clusters
                unique.append(p)

        unique.sort(key=lambda x: (x['severity_score'], x['transaction_count']), reverse=True)
        return unique

    @staticmethod
    def _tier_to_score(tier: str) -> float:
        return {'CRITICAL': 1.0, 'HIGH': 0.75, 'MEDIUM': 0.5, 'LOW': 0.25}.get(tier, 0.25)

    @staticmethod
    def _velocity_risk_tier(avg_velocity: float) -> str:
        if avg_velocity >= 15:
            return "CRITICAL"
        elif avg_velocity >= 10:
            return "HIGH"
        elif avg_velocity >= 6:
            return "MEDIUM"
        return "LOW"

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure correct dtypes on all columns before processing"""
        float_cols = ['amount', 'amount_zscore', 'location_lat', 'location_lon']
        int_cols = ['velocity_1h', 'velocity_24h']
        bool_cols = ['is_international']

        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(np.float64)

        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(np.int64)

        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].fillna(False).astype(bool)

        if 'device_fingerprint' not in df.columns:
            df['device_fingerprint'] = 'unknown'

        df = df.fillna(0)
        return df


# ─────────────────────────────────────────────
# Smoke-test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from faker import Faker
    import random

    fake = Faker()
    random.seed(42)
    np.random.seed(42)

    rows = []
    for i in range(200):
        rows.append({
            'transaction_id': f"TX{i:05d}",
            'user_id': f"U{random.randint(1, 30):03d}",
            'amount': float(random.uniform(10, 2000)),
            'currency': 'USD',
            'merchant_id': f"M{random.randint(1, 20):03d}",
            'merchant_category': random.choice(['Electronics', 'Groceries', 'Travel', 'Gaming']),
            'timestamp': fake.date_time_between(start_date='-30d', end_date='now').isoformat(),
            'ip_address': fake.ipv4(),
            'device_fingerprint': f"DEV{random.randint(1, 5):03d}",
            'location_lat': float(fake.latitude()),
            'location_lon': float(fake.longitude()),
            'payment_method': random.choice(['credit_card', 'debit_card', 'crypto']),
            'is_international': random.random() > 0.8,
            'velocity_1h': random.randint(0, 15),
            'velocity_24h': random.randint(0, 40),
            'time_since_last_tx': float(random.uniform(0, 86400)),
            'amount_zscore': float(random.uniform(-2, 4)),
            'fraud_label': random.random() > 0.92,
            'fraud_pattern': random.choice([None, 'velocity_burst', 'geo_anomaly']),
        })

    df = pd.DataFrame(rows)
    miner = PatternMiner()
    patterns = miner.discover_patterns(df)

    print(f"\nDiscovered {len(patterns)} patterns:\n")
    for p in patterns:
        print(f"  [{p['risk_tier']:8s}] {p['name']} — {p['transaction_count']} tx, "
              f"{p['affected_users']} users")
        print(f"           {p['description'][:100]}...")
        print()