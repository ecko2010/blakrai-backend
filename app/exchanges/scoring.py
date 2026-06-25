"""
Exchange scoring — ranks exchanges by latency, liquidity, trust, and data freshness.
Used by engine to select the best exchange for data fetching.
"""

import time
from dataclasses import dataclass
from loguru import logger

from app.exchanges.base import Ticker


# Trust scores based on exchange reputation, volume, and API reliability.
# These are static baselines — dynamic scores (latency, liquidity) adjust the ranking.
TRUST_SCORES: dict[str, float] = {
    "binance": 1.00,
    "bybit": 0.95,
    "okx": 0.92,
    "kucoin": 0.85,
    "bitget": 0.82,
    "gateio": 0.78,
    "mexc": 0.75,
    "htx": 0.72,
}


@dataclass
class ExchangeScore:
    exchange: str
    latency_ms: float = 0.0
    liquidity_score: float = 0.5
    trust_score: float = 0.5
    freshness_score: float = 1.0  # 1.0 = fresh, 0.0 = very stale
    composite: float = 0.5
    error_rate: float = 0.0  # 0.0 = no errors, 1.0 = all calls fail
    _calls: int = 0
    _errors: int = 0

    def compute_composite(self):
        error_penalty = 1.0 - self.error_rate
        latency_norm = 1.0 - min(1.0, self.latency_ms / 5000.0)
        self.composite = (
            self.trust_score * 0.25
            + self.liquidity_score * 0.30
            + latency_norm * 0.20
            + self.freshness_score * 0.15
            + error_penalty * 0.10
        )

    def record_call(self, success: bool):
        self._calls += 1
        if not success:
            self._errors += 1
        # Rolling error rate (last ~100 calls)
        if self._calls > 100:
            ratio = self._errors / self._calls
            self._calls = 50
            self._errors = int(ratio * 50)
        self.error_rate = self._errors / max(1, self._calls)


class ExchangeScorer:
    """Tracks and scores exchange quality in real-time."""

    def __init__(self):
        self._scores: dict[str, ExchangeScore] = {}

    def get_score(self, exchange_name: str) -> ExchangeScore:
        name = exchange_name.lower()
        if name not in self._scores:
            self._scores[name] = ExchangeScore(
                exchange=name,
                trust_score=TRUST_SCORES.get(name, 0.5),
            )
            self._scores[name].compute_composite()
        return self._scores[name]

    def update_latency(self, exchange_name: str, latency_ms: float):
        score = self.get_score(exchange_name)
        # EMA smoothing
        alpha = 0.3
        score.latency_ms = score.latency_ms * (1 - alpha) + latency_ms * alpha
        score.compute_composite()

    def update_liquidity_from_ticker(self, exchange_name: str, ticker: Ticker):
        score = self.get_score(exchange_name)
        spread = 0.0
        if ticker.bid > 0 and ticker.ask > 0:
            spread = (ticker.ask - ticker.bid) / ticker.bid

        # Tight spread = high liquidity score
        if spread < 0.001:
            liq = 1.0
        elif spread < 0.005:
            liq = 0.7
        elif spread < 0.01:
            liq = 0.4
        else:
            liq = 0.2

        # Factor in volume
        if ticker.volume_24h > 100_000_000:
            liq = min(1.0, liq + 0.2)
        elif ticker.volume_24h > 10_000_000:
            liq = min(1.0, liq + 0.1)

        score.liquidity_score = liq
        score.compute_composite()

    def update_freshness(self, exchange_name: str, data_timestamp_s: float | None):
        score = self.get_score(exchange_name)
        if data_timestamp_s is None:
            score.freshness_score = 0.5
        else:
            age_seconds = time.time() - data_timestamp_s
            if age_seconds < 60:
                score.freshness_score = 1.0
            elif age_seconds < 300:
                score.freshness_score = 0.8
            elif age_seconds < 900:
                score.freshness_score = 0.5
            else:
                score.freshness_score = 0.2
        score.compute_composite()

    def record_call(self, exchange_name: str, success: bool):
        score = self.get_score(exchange_name)
        score.record_call(success)
        score.compute_composite()

    def rank_exchanges(self) -> list[ExchangeScore]:
        """Return exchanges sorted by composite score (best first)."""
        for s in self._scores.values():
            s.compute_composite()
        return sorted(self._scores.values(), key=lambda s: s.composite, reverse=True)

    def best_exchange_for(self, available: list[str]) -> str | None:
        """Get best-scored exchange from a list of available ones."""
        if not available:
            return None
        ranked = self.rank_exchanges()
        for s in ranked:
            if s.exchange in available:
                return s.exchange
        return available[0]

    def get_ordered_list(self, subset: list[str]) -> list[str]:
        """Return exchanges from subset ordered by score (best first)."""
        if not subset:
            return []
        scored = [(name, self.get_score(name).composite) for name in subset]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored]

    def summary(self) -> dict[str, dict]:
        """Return scoring summary for admin panel / logging."""
        result = {}
        for name, score in sorted(self._scores.items(), key=lambda x: x[1].composite, reverse=True):
            result[name] = {
                "composite": round(score.composite, 3),
                "latency_ms": round(score.latency_ms, 1),
                "liquidity": round(score.liquidity_score, 3),
                "trust": round(score.trust_score, 3),
                "freshness": round(score.freshness_score, 3),
                "error_rate": round(score.error_rate, 3),
            }
        return result


# Singleton
exchange_scorer = ExchangeScorer()
