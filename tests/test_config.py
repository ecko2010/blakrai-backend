"""
Test config — Settings class, channel ID lookup, admin IDs parsing.
"""

import os
import pytest


class TestConfig:
    """Test the Settings class."""

    def test_settings_loads(self):
        from app.config import settings
        assert settings.TELEGRAM_BOT_TOKEN is not None

    def test_admin_ids_parsing(self):
        from app.config import settings
        # Default env is "123456789,987654321" or empty — just check it works
        ids = settings.admin_ids
        assert isinstance(ids, list)
        for x in ids:
            assert isinstance(x, int)

    def test_get_channel_id(self):
        from app.config import settings
        # Should return int (could be 0 if not configured)
        cid = settings.get_channel_id("en", "free")
        assert isinstance(cid, int)

    def test_get_channel_id_elite_maps_to_pro(self):
        """ELITE users go to the PRO channel."""
        from app.config import settings
        pro = settings.get_channel_id("en", "pro")
        elite = settings.get_channel_id("en", "elite")
        assert pro == elite

    def test_all_channel_ids_returns_dict(self):
        from app.config import settings
        channels = settings.all_channel_ids
        assert isinstance(channels, dict)

    def test_dry_run_exists(self):
        from app.config import settings
        assert isinstance(settings.DRY_RUN, bool)

    def test_admin_api_key_exists(self):
        from app.config import settings
        assert isinstance(settings.ADMIN_API_KEY, str)


class TestConfigChannelMatrix:
    """Verify all 6 lang×tier combinations are handled."""

    @pytest.mark.parametrize("lang", ["uk", "en", "ru"])
    @pytest.mark.parametrize("tier", ["free", "pro"])
    def test_channel_id_for_all_combos(self, lang, tier):
        from app.config import settings
        result = settings.get_channel_id(lang, tier)
        assert isinstance(result, int)
