"""
LightGBM quality gate — predicts probability of TP1 hit for each signal.

Starts in SHADOW MODE: logs predictions alongside signals but does NOT filter.
After accumulating 300+ closed signals, can be retrained and optionally activated.
"""

import hashlib
import os
import pickle

import numpy as np
from dataclasses import dataclass
from datetime import datetime, timezone
from loguru import logger

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    lgb = None  # type: ignore[assignment]

from app.ml.features import FEATURE_NAMES

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "quality_gate.pkl")
MIN_TRAINING_SAMPLES = 300


@dataclass
class QualityPrediction:
    p_tp1: float          # probability of hitting TP1
    expected_quality: float  # 0.0-1.0 quality rank
    shadow_mode: bool     # if True, prediction is logged but not used for filtering
    features_used: int
    model_version: str | None = None


class QualityGate:
    """LightGBM-based signal quality gate.

    Shadow mode: logs predictions without filtering signals.
    After enough training data (300+ closed signals), can be retrained.
    """

    def __init__(self):
        self._model = None
        self._feature_names: list[str] = FEATURE_NAMES
        self._model_version: str | None = None
        self._shadow_mode = True
        self._load_model()

    def _load_model(self):
        if not HAS_LIGHTGBM:
            logger.info("LightGBM not installed — quality gate runs in shadow-only mode")
            return

        if os.path.exists(MODEL_PATH):
            try:
                raw = open(MODEL_PATH, "rb").read()
                # Verify checksum if available (prevents loading tampered models)
                checksum_path = MODEL_PATH + ".sha256"
                if os.path.exists(checksum_path):
                    expected = open(checksum_path).read().strip()
                    actual = hashlib.sha256(raw).hexdigest()
                    if actual != expected:
                        logger.error(f"Quality gate model checksum mismatch! Expected {expected}, got {actual}")
                        return
                saved = pickle.loads(raw)  # noqa: S301
                self._model = saved["model"]
                self._feature_names = saved.get("feature_names", FEATURE_NAMES)
                self._model_version = saved.get("version", "unknown")
                self._shadow_mode = saved.get("shadow_mode", True)
                logger.info(
                    f"Quality gate model loaded: v{self._model_version}, "
                    f"shadow={self._shadow_mode}, features={len(self._feature_names)}"
                )
            except Exception as e:
                logger.error(f"Failed to load quality gate model: {e}")

    def predict(self, features: dict[str, float]) -> QualityPrediction:
        """Predict signal quality. In shadow mode, always passes."""
        if not HAS_LIGHTGBM or self._model is None:
            return QualityPrediction(
                p_tp1=0.5, expected_quality=0.5,
                shadow_mode=True, features_used=0,
            )

        try:
            X = np.array([[features.get(f, 0.0) for f in self._feature_names]])
            pred = self._model.predict(X)[0]
            p_tp1 = float(np.clip(pred, 0.0, 1.0))

            return QualityPrediction(
                p_tp1=p_tp1,
                expected_quality=p_tp1,
                shadow_mode=self._shadow_mode,
                features_used=len(self._feature_names),
                model_version=self._model_version,
            )
        except Exception as e:
            logger.error(f"Quality gate prediction error: {e}")
            return QualityPrediction(
                p_tp1=0.5, expected_quality=0.5,
                shadow_mode=True, features_used=0,
            )

    @property
    def is_active(self) -> bool:
        return HAS_LIGHTGBM and self._model is not None

    @property
    def shadow_mode(self) -> bool:
        return self._shadow_mode

    async def retrain(self) -> bool:
        """Retrain model from historical signal data.

        Returns True if model was successfully retrained.
        """
        if not HAS_LIGHTGBM:
            logger.warning("LightGBM not available — skip retrain")
            return False

        try:
            from app.database import async_session
            from app.models import Signal, SignalStatus
            from sqlalchemy import select
            from app.ml.features import extract_features
            from app.signals.analyzer import IndicatorSet
            from app.exchanges.scoring import TRUST_SCORES

            # Fetch all closed signals
            terminal_statuses = (
                SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
                SignalStatus.STOPPED, SignalStatus.EXPIRED, SignalStatus.CLOSED,
            )

            async with async_session() as session:
                result = await session.execute(
                    select(Signal).where(Signal.status.in_(terminal_statuses))
                )
                signals = result.scalars().all()

            if len(signals) < MIN_TRAINING_SAMPLES:
                logger.info(
                    f"Quality gate: not enough training data "
                    f"({len(signals)}/{MIN_TRAINING_SAMPLES})"
                )
                return False

            # Build training data from signal factors
            X_rows = []
            y_rows = []

            for sig in signals:
                if not sig.factors or "indicators" not in sig.factors:
                    continue

                # Reconstruct IndicatorSet from stored factors
                ind_dict = sig.factors["indicators"]
                valid_fields = {k for k in IndicatorSet.__dataclass_fields__}
                ind = IndicatorSet(**{k: v for k, v in ind_dict.items() if k in valid_fields})

                direction = "long" if sig.direction.value == "long" else "short"
                ex_name = (sig.exchange or "binance").lower()

                features = extract_features(
                    indicators=ind,
                    exchange_score=TRUST_SCORES.get(ex_name, 0.5),
                    direction=direction,
                )

                # Label: 1 if TP1+ was hit, 0 otherwise
                hit_tp = sig.status in (
                    SignalStatus.TP1_HIT, SignalStatus.TP2_HIT,
                    SignalStatus.TP3_HIT, SignalStatus.CLOSED,
                )

                X_rows.append(features)
                y_rows.append(1.0 if hit_tp else 0.0)

            if len(X_rows) < MIN_TRAINING_SAMPLES:
                logger.info(
                    f"Quality gate: not enough valid training rows "
                    f"({len(X_rows)}/{MIN_TRAINING_SAMPLES})"
                )
                return False

            # Convert to arrays using sorted feature names
            feature_names = sorted(X_rows[0].keys())
            X = np.array([[row.get(f, 0.0) for f in feature_names] for row in X_rows])
            y = np.array(y_rows)

            # Train LightGBM
            dataset = lgb.Dataset(X, label=y, feature_name=feature_names)

            params = {
                "objective": "binary",
                "metric": "auc",
                "learning_rate": 0.05,
                "num_leaves": 31,
                "max_depth": 5,
                "min_child_samples": 10,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                "verbose": -1,
                "seed": 42,
            }

            model = lgb.train(
                params,
                dataset,
                num_boost_round=200,
            )

            # Save model
            os.makedirs(MODEL_DIR, exist_ok=True)
            version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            raw = pickle.dumps({
                "model": model,
                "feature_names": feature_names,
                "version": version,
                "shadow_mode": True,  # Always shadow until manually activated
                "n_samples": len(X_rows),
                "positive_rate": float(np.mean(y)),
            })
            with open(MODEL_PATH, "wb") as f:
                f.write(raw)
            # Save checksum for integrity verification on load
            with open(MODEL_PATH + ".sha256", "w") as f:
                f.write(hashlib.sha256(raw).hexdigest())

            self._model = model
            self._feature_names = feature_names
            self._model_version = version

            logger.info(
                f"Quality gate retrained: v{version}, "
                f"{len(X_rows)} samples, positive_rate={np.mean(y):.2%}"
            )
            return True

        except Exception as e:
            logger.error(f"Quality gate retrain failed: {e}", exc_info=True)
            return False


# Singleton
quality_gate = QualityGate()
