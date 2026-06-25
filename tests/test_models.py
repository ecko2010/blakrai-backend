"""
Test models — enum values, model field defaults.
"""

import pytest
from app.models import (
    Language, Tier, SignalDirection, SignalStatus,
    PaymentStatus, UpdateType,
)


class TestEnums:
    """Validate all enum values match expected strings."""

    def test_language_values(self):
        assert Language.UK.value == "uk"
        assert Language.EN.value == "en"
        assert Language.RU.value == "ru"
        assert len(Language) == 3

    def test_tier_values(self):
        assert Tier.FREE.value == "free"
        assert Tier.PRO.value == "pro"
        assert Tier.ELITE.value == "elite"
        assert len(Tier) == 3

    def test_signal_direction(self):
        assert SignalDirection.LONG.value == "long"
        assert SignalDirection.SHORT.value == "short"
        assert len(SignalDirection) == 2

    def test_signal_status(self):
        statuses = [s.value for s in SignalStatus]
        assert "active" in statuses
        assert "tp1_hit" in statuses
        assert "tp2_hit" in statuses
        assert "tp3_hit" in statuses
        assert "stopped" in statuses
        assert "closed" in statuses
        assert "cancelled" in statuses
        assert "expired" in statuses
        assert len(SignalStatus) == 8

    def test_payment_status(self):
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.COMPLETED.value == "completed"
        assert PaymentStatus.FAILED.value == "failed"

    def test_update_type(self):
        assert UpdateType.TP1_HIT.value == "tp1_hit"
        assert UpdateType.SL_HIT.value == "sl_hit"
        assert UpdateType.ADJUSTMENT.value == "adjustment"


class TestEnumFromString:
    """Ensure enums can be created from string values (for API deserialization)."""

    def test_language_from_string(self):
        assert Language("uk") == Language.UK
        assert Language("en") == Language.EN
        assert Language("ru") == Language.RU

    def test_tier_from_string(self):
        assert Tier("free") == Tier.FREE
        assert Tier("pro") == Tier.PRO
        assert Tier("elite") == Tier.ELITE

    def test_signal_status_from_string(self):
        assert SignalStatus("active") == SignalStatus.ACTIVE
        assert SignalStatus("tp1_hit") == SignalStatus.TP1_HIT
        assert SignalStatus("stopped") == SignalStatus.STOPPED

    def test_invalid_enum_raises(self):
        with pytest.raises(ValueError):
            Language("invalid")
        with pytest.raises(ValueError):
            Tier("diamond")
