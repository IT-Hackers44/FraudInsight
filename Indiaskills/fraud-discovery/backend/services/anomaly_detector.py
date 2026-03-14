import numpy as np
import pandas as pd
import joblib
import os
from typing import Tuple, List, Dict, Any
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from datetime import datetime


class AnomalyDetector:
    def __init__(self, contamination: float = 0.05):
        """Initialize ensemble anomaly detector"""
        self.contamination = contamination

        # Model 1: Isolation Forest
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            n_estimators=200,
            random_state=42,
            n_jobs=-1
        )

        # Model 2: DBSCAN
        self.dbscan = DBSCAN(eps=0.5, min_samples=5)

        # Model 3: Statistical Z-Score
        self.zscore_threshold = 3.5

        # Scaler for DBSCAN
        self.scaler = StandardScaler()

        self.is_fitted = False
        self.mean_features: np.ndarray = None
        self.std_features: np.ndarray = None

    # ─────────────────────────────────────────────
    # Private: sanitize input
    # ─────────────────────────────────────────────

    def _sanitize(self, features) -> np.ndarray:
        """
        Force input to a clean 2D numpy float64 array.

        Fixes:
          - 'ufunc does not support argument of type float which has no callable sqrt'
            → caused by Python-native floats from SQLAlchemy rows
          - 'Expected a 1D array, got an array with shape (N, M)'
            → caused by wrong ndim passed to sklearn
          - NaN / inf values that crash distance calculations
        """
        # Step 1: force to numpy float64 — handles Python native floats,
        #         pandas DataFrames, lists of lists, object arrays
        X = np.array(features, dtype=np.float64)

        # Step 2: replace NaN / inf
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Step 3: guarantee 2D shape — sklearn always wants (n_samples, n_features)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        return X

    # ─────────────────────────────────────────────
    # Core public methods
    # ─────────────────────────────────────────────

    def fit(self, features) -> None:
        """Fit all ensemble models on training data"""
        X = self._sanitize(features)

        # Isolation Forest
        self.isolation_forest.fit(X)

        # DBSCAN scaler + fit
        self.scaler.fit(X)
        self.dbscan.fit(self.scaler.transform(X))

        # Z-Score statistics — stored as 1D so broadcasting works correctly
        self.mean_features = np.mean(X, axis=0).ravel()
        self.std_features  = np.std(X,  axis=0).ravel()
        self.std_features[self.std_features == 0] = 1.0   # avoid division by zero

        self.is_fitted = True

    def predict_ensemble(
        self, features
    ) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """
        Run ensemble prediction.
        Returns:
            ensemble_predictions  – np.ndarray[int]   1 = anomaly, 0 = normal
            risk_scores           – np.ndarray[float]  0.0 – 1.0
            results               – List[Dict]  per-sample detail
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted yet. Call fit() first.")

        X = self._sanitize(features)
        n_samples = X.shape[0]

        # ── Model 1: Isolation Forest ──
        if_scores      = self.isolation_forest.score_samples(X)   # lower = more anomalous
        if_predictions = self.isolation_forest.predict(X)          # -1 = anomaly
        if_anomalies   = (if_predictions == -1).astype(np.int32)

        # ── Model 2: DBSCAN ──
        scaled_X         = self.scaler.transform(X)
        dbscan_labels    = self.dbscan.fit_predict(scaled_X)
        dbscan_anomalies = (dbscan_labels == -1).astype(np.int32)

        # ── Model 3: Z-Score ──
        # mean/std are 1D (n_features,) → broadcasting with X (n_samples, n_features) works correctly
        mean   = self.mean_features.ravel()
        std    = self.std_features.ravel()
        zscores          = np.abs((X - mean) / std)                           # (n_samples, n_features)
        zscore_anomalies = np.any(zscores > self.zscore_threshold, axis=1).astype(np.int32)
        zscore_max       = zscores.max(axis=1)                                 # (n_samples,)

        # ── Ensemble voting — require ≥2 models ──
        ensemble_votes       = if_anomalies + dbscan_anomalies + zscore_anomalies
        ensemble_predictions = (ensemble_votes >= 2).astype(np.int32)

        # ── Composite risk score ──
        if_score_min  = if_scores.min()
        if_score_max  = if_scores.max()
        score_range   = max(float(if_score_max - if_score_min), 1e-9)
        if_normalized = (if_scores - if_score_min) / score_range
        if_inverted   = 1.0 - if_normalized                    # 1.0 = most anomalous

        dbscan_contrib   = dbscan_anomalies.astype(np.float64) * 0.3
        zscore_contrib   = np.minimum(zscore_max / self.zscore_threshold, 1.0) * 0.2
        ensemble_contrib = ensemble_predictions.astype(np.float64) * 0.1

        risk_scores = if_inverted * 0.4 + dbscan_contrib + zscore_contrib + ensemble_contrib
        risk_scores = np.clip(risk_scores, 0.0, 1.0)

        # ── Build detailed results ──
        results: List[Dict[str, Any]] = []
        for i in range(n_samples):
            results.append({
                'index':               i,
                'risk_score':          float(risk_scores[i]),
                'risk_tier':           self._get_risk_tier(float(risk_scores[i])),
                'is_anomaly_if':       bool(if_anomalies[i]),
                'is_anomaly_dbscan':   bool(dbscan_anomalies[i]),
                'is_anomaly_zscore':   bool(zscore_anomalies[i]),
                'ensemble_consensus':  bool(ensemble_predictions[i]),
                'flagged_by_count':    int(ensemble_votes[i]),
                'anomaly_explanation': self._generate_explanation(
                    if_anomalies[i], dbscan_anomalies[i], zscore_anomalies[i],
                    if_scores[i], zscores[i]
                ),
                'if_score':   float(if_scores[i]),
                'max_zscore': float(zscore_max[i]),
            })

        return ensemble_predictions, risk_scores, results

    # ─────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────

    def save_model(self, filepath: str) -> None:
        """Save trained model to disk"""
        model_data = {
            'isolation_forest': self.isolation_forest,
            'scaler':           self.scaler,
            'zscore_threshold': self.zscore_threshold,
            'mean_features':    self.mean_features,
            'std_features':     self.std_features,
            'is_fitted':        self.is_fitted,
        }
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """Load trained model from disk"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")

        model_data          = joblib.load(filepath)
        self.isolation_forest = model_data['isolation_forest']
        self.scaler           = model_data['scaler']
        self.zscore_threshold = model_data['zscore_threshold']
        self.mean_features    = model_data['mean_features']
        self.std_features     = model_data['std_features']
        self.is_fitted        = model_data['is_fitted']
        print(f"Model loaded from {filepath}")

    # ─────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────

    def _get_risk_tier(self, risk_score: float) -> str:
        if risk_score >= 0.85:
            return "CRITICAL"
        elif risk_score >= 0.65:
            return "HIGH"
        elif risk_score >= 0.40:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_explanation(
        self,
        is_if: bool,
        is_dbscan: bool,
        is_zscore: bool,
        if_score: float,
        zscores: np.ndarray,
    ) -> str:
        reasons = []

        if is_if:
            reasons.append(
                f"Isolation Forest flagged as outlier (score: {float(if_score):.4f})"
            )
        if is_dbscan:
            reasons.append("DBSCAN classified as noise — no nearby cluster")
        if is_zscore:
            zscores_1d = np.array(zscores).ravel()
            max_idx    = int(np.argmax(np.abs(zscores_1d)))
            max_z      = float(abs(zscores_1d[max_idx]))
            reasons.append(
                f"Z-score exceeded threshold at feature #{max_idx} "
                f"(z={max_z:.2f}, threshold={self.zscore_threshold})"
            )

        if not reasons:
            return "No anomaly detected — passes all three detectors"

        return " | ".join(reasons)


# ─────────────────────────────────────────────
# Smoke-test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)

    # Simulate Python-native float object arrays (exactly what SQLAlchemy produces)
    normal_rows  = [[float(v) for v in row] for row in np.random.randn(900, 20).tolist()]
    anomaly_rows = [[float(v) for v in row] for row in (np.random.randn(100, 20) + 5).tolist()]

    X_obj = np.empty((1000, 20), dtype=object)
    for i, row in enumerate(normal_rows + anomaly_rows):
        for j, val in enumerate(row):
            X_obj[i, j] = val   # pure Python floats in object array

    print(f"Input dtype  : {X_obj.dtype}")       # object
    print(f"Input shape  : {X_obj.shape}")        # (1000, 20)

    detector = AnomalyDetector(contamination=0.1)
    detector.fit(X_obj)
    predictions, scores, results = detector.predict_ensemble(X_obj)

    print(f"Anomalies    : {predictions.sum()} / {len(predictions)}")
    print(f"Score range  : {scores.min():.4f} – {scores.max():.4f}")
    print("\nTop 5 results:")
    for r in sorted(results, key=lambda x: x['risk_score'], reverse=True)[:5]:
        print(
            f"  idx={r['index']:4d}  risk={r['risk_score']:.4f}  "
            f"tier={r['risk_tier']:<8}  votes={r['flagged_by_count']}"
        )