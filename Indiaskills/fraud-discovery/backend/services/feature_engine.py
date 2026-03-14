import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Any
from sklearn.preprocessing import RobustScaler, LabelEncoder
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class FeatureEngine:
    def __init__(self):
        self.robust_scaler = RobustScaler()
        self.payment_method_encoder = LabelEncoder()
        self.merchant_category_encoder = LabelEncoder()
        self.currency_encoder = LabelEncoder()
        self.is_fitted = False
        self.user_profiles = {}
        self._known_payment_methods = []
        self._known_merchant_categories = []
        self._known_currencies = []

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def fit_transform(self, transactions_df: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, Any]]:
        df = self._clean_dataframe(transactions_df)

        # Fit label encoders on 1D string arrays
        self._known_payment_methods    = sorted(df['payment_method'].dropna().unique().tolist())
        self._known_merchant_categories = sorted(df['merchant_category'].dropna().unique().tolist())
        self._known_currencies         = sorted(df['currency'].dropna().unique().tolist())

        self.payment_method_encoder.fit(self._known_payment_methods)
        self.merchant_category_encoder.fit(self._known_merchant_categories)
        self.currency_encoder.fit(self._known_currencies)

        # Extract features → encode categoricals → scale numerics
        features_df = self._extract_features(df)
        encoded_df  = self._encode_categorical(features_df)
        scaled_arr  = self._scale(encoded_df, fit=True)

        self._build_user_profiles(df)
        self.is_fitted = True

        return scaled_arr, self._get_metadata(encoded_df)

    def transform(self, transactions_df: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("FeatureEngine not fitted yet. Call fit_transform first.")

        df          = self._clean_dataframe(transactions_df)
        features_df = self._extract_features(df)
        encoded_df  = self._encode_categorical(features_df)
        return self._scale(encoded_df, fit=False)

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        return self.user_profiles.get(user_id, {})

    def compute_transaction_anomaly_score(
        self, transaction: Dict[str, Any], user_profile: Dict[str, Any]
    ) -> float:
        if not user_profile:
            return 0.0

        score = 0.0
        user_avg = float(user_profile.get('avg_amount') or 0)
        user_std = float(user_profile.get('std_amount') or 1)
        if user_std > 0:
            amount_z = abs((float(transaction.get('amount', 0)) - user_avg) / user_std)
            score += min(amount_z, 5.0) / 5.0

        user_avg_vel = float(user_profile.get('avg_velocity_1h') or 0)
        curr_vel     = float(transaction.get('velocity_1h', 0) or 0)
        if user_avg_vel > 0:
            score += min(curr_vel / (user_avg_vel + 1), 2.0) / 2.0

        if transaction.get('is_international', False):
            if float(user_profile.get('is_international_ratio') or 0) < 0.1:
                score += 0.3

        return min(score / 3.0, 1.0)

    # ─────────────────────────────────────────────
    # Step 1 — clean raw dataframe
    # ─────────────────────────────────────────────

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        for col in ['amount', 'time_since_last_tx', 'amount_zscore', 'location_lat', 'location_lon']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(np.float64)

        for col in ['velocity_1h', 'velocity_24h']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(np.int64)

        if 'is_international' in df.columns:
            df['is_international'] = df['is_international'].fillna(False).astype(bool)

        for col in ['payment_method', 'merchant_category', 'currency']:
            if col in df.columns:
                df[col] = df[col].fillna('unknown').astype(str)

        df = df.fillna(0)
        return df

    # ─────────────────────────────────────────────
    # Step 2 — extract features
    # ─────────────────────────────────────────────

    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features = df.copy()

        # Time features
        ts = pd.to_datetime(features['timestamp'], errors='coerce')
        features['tx_hour']        = ts.dt.hour.fillna(0).astype(np.float64)
        features['tx_day_of_week'] = ts.dt.dayofweek.fillna(0).astype(np.float64)
        features['tx_is_weekend']  = ts.dt.dayofweek.isin([5, 6]).astype(np.float64)

        # User aggregation
        user_stats = df.groupby('user_id').agg(
            user_avg_amount=('amount', 'mean'),
            user_std_amount=('amount', 'std'),
            user_min_amount=('amount', 'min'),
            user_max_amount=('amount', 'max'),
            user_tx_count=('transaction_id', 'count')
        ).reset_index()
        features = features.merge(user_stats, on='user_id', how='left')

        # Merchant aggregation
        merchant_stats = df.groupby('merchant_id').agg(
            merchant_avg_amount=('amount', 'mean'),
            merchant_tx_count=('amount', 'count'),
            merchant_unique_users=('user_id', 'nunique')
        ).reset_index()
        features = features.merge(merchant_stats, on='merchant_id', how='left')

        # Cast aggregated cols to float64
        agg_cols = [
            'user_avg_amount', 'user_std_amount', 'user_min_amount',
            'user_max_amount', 'user_tx_count',
            'merchant_avg_amount', 'merchant_tx_count', 'merchant_unique_users'
        ]
        for col in agg_cols:
            if col in features.columns:
                features[col] = pd.to_numeric(features[col], errors='coerce').astype(np.float64)

        features = features.fillna(0)

        # Keep only the columns we want — in a fixed order
        wanted = [
            'amount', 'is_international', 'velocity_1h', 'velocity_24h',
            'time_since_last_tx', 'amount_zscore',
            'tx_hour', 'tx_day_of_week', 'tx_is_weekend',
            'user_avg_amount', 'user_std_amount', 'user_min_amount',
            'user_max_amount', 'user_tx_count',
            'merchant_avg_amount', 'merchant_tx_count', 'merchant_unique_users',
            'payment_method', 'merchant_category', 'currency',
        ]
        available = [c for c in wanted if c in features.columns]
        return features[available].reset_index(drop=True)

    # ─────────────────────────────────────────────
    # Step 3 — encode categoricals
    # Each LabelEncoder gets a 1D python list, never the whole matrix
    # ─────────────────────────────────────────────

    def _encode_categorical(self, features_df: pd.DataFrame) -> pd.DataFrame:
        df = features_df.copy()

        col_encoder_map = {
            'payment_method':    self.payment_method_encoder,
            'merchant_category': self.merchant_category_encoder,
            'currency':          self.currency_encoder,
        }

        for col, enc in col_encoder_map.items():
            if col not in df.columns:
                continue

            if not hasattr(enc, 'classes_'):
                # encoder not fitted — just zero-fill
                df[col] = np.float64(0)
                continue

            known = set(enc.classes_)

            # ── KEY FIX ──
            # Process one scalar value at a time.
            # Never pass a Series, array, or DataFrame slice to LabelEncoder.transform()
            # because pandas can return 2D structures in edge cases.
            encoded_vals = []
            for val in df[col].tolist():          # .tolist() gives plain Python strings
                str_val = str(val)
                if str_val in known:
                    # enc.transform expects a 1D list with one element
                    encoded_vals.append(int(enc.transform([str_val])[0]))
                else:
                    encoded_vals.append(0)

            df[col] = np.array(encoded_vals, dtype=np.float64)

        return df

    # ─────────────────────────────────────────────
    # Step 4 — scale numeric columns
    # ─────────────────────────────────────────────

    def _scale(self, encoded_df: pd.DataFrame, fit: bool) -> np.ndarray:
        """
        Scale all numeric columns and return a clean float64 2D array.
        RobustScaler.fit_transform / transform correctly accept 2D arrays.
        """
        df = encoded_df.copy()

        # Force every column to float64 before handing to sklearn
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(np.float64)

        df = df.fillna(0)

        # Sanity-check: all columns must be numeric at this point
        non_numeric = df.select_dtypes(exclude=[np.number]).columns.tolist()
        if non_numeric:
            for col in non_numeric:
                df[col] = 0.0

        X = df.values.astype(np.float64)                              # (n_samples, n_features)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Guarantee 2D
        if X.ndim == 1:
            X = X.reshape(1, -1)

        if fit:
            X_scaled = self.robust_scaler.fit_transform(X)           # accepts 2D ✓
        else:
            X_scaled = self.robust_scaler.transform(X)               # accepts 2D ✓

        return X_scaled.astype(np.float64)

    # ─────────────────────────────────────────────
    # User profiles
    # ─────────────────────────────────────────────

    def _build_user_profiles(self, df: pd.DataFrame) -> None:
        for user_id in df['user_id'].unique():
            u = df[df['user_id'] == user_id]
            std_val = u['amount'].std()
            self.user_profiles[user_id] = {
                'avg_amount':            float(u['amount'].mean()),
                'std_amount':            float(std_val) if not np.isnan(std_val) else 0.0,
                'preferred_merchants':   u['merchant_id'].value_counts().head(5).to_dict(),
                'preferred_categories':  u['merchant_category'].value_counts().head(5).to_dict(),
                'preferred_payment_methods': u['payment_method'].value_counts().head(3).to_dict(),
                'transaction_count':     int(len(u)),
                'avg_velocity_1h':       float(u['velocity_1h'].mean()),
                'avg_velocity_24h':      float(u['velocity_24h'].mean()),
                'is_international_ratio': float(
                    u['is_international'].astype(int).sum() / max(len(u), 1)
                ),
                'active_hours': list(
                    pd.to_datetime(u['timestamp'], errors='coerce').dt.hour.dropna().unique()
                ),
            }

    def _get_metadata(self, features_df: pd.DataFrame) -> Dict[str, Any]:
        return {
            'feature_names':  list(features_df.columns),
            'feature_count':  len(features_df.columns),
            'sample_count':   len(features_df),
            'user_profiles':  self.user_profiles,
            'encoders': {
                'payment_methods': list(self.payment_method_encoder.classes_)
                    if hasattr(self.payment_method_encoder, 'classes_') else [],
                'categories': list(self.merchant_category_encoder.classes_)
                    if hasattr(self.merchant_category_encoder, 'classes_') else [],
                'currencies': list(self.currency_encoder.classes_)
                    if hasattr(self.currency_encoder, 'classes_') else [],
            }
        }


# ─────────────────────────────────────────────
# Smoke-test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import random
    random.seed(42)

    rows = []
    for i in range(500):
        rows.append({
            'transaction_id':     f"TX{i:05d}",
            'user_id':            f"U{random.randint(1, 30):03d}",
            'amount':             float(random.uniform(10, 3000)),
            'currency':           random.choice(['USD', 'EUR', 'GBP']),
            'merchant_id':        f"M{random.randint(1, 20):03d}",
            'merchant_category':  random.choice(['Electronics', 'Groceries', 'Travel', 'Gaming']),
            'timestamp':          f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}T"
                                  f"{random.randint(0,23):02d}:00:00",
            'ip_address':         f"192.168.1.{random.randint(1,255)}",
            'device_fingerprint': f"DEV{random.randint(1, 8):03d}",
            'location_lat':       float(random.uniform(-90, 90)),
            'location_lon':       float(random.uniform(-180, 180)),
            'payment_method':     random.choice(['credit_card', 'debit_card', 'crypto']),
            'is_international':   random.random() > 0.8,
            'velocity_1h':        random.randint(0, 15),
            'velocity_24h':       random.randint(0, 40),
            'time_since_last_tx': float(random.uniform(0, 86400)),
            'amount_zscore':      float(random.uniform(-3, 5)),
        })

    df = pd.DataFrame(rows)

    engine = FeatureEngine()
    matrix, meta = engine.fit_transform(df)

    print(f"Matrix shape : {matrix.shape}")
    print(f"Matrix dtype : {matrix.dtype}")
    print(f"Features     : {meta['feature_names']}")
    assert matrix.dtype == np.float64, "dtype must be float64"
    assert matrix.ndim  == 2,          "must be 2D"
    print("All assertions passed.")