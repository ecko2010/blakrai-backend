"""
Shared test fixtures — mock settings, in-memory DB, etc.
"""

import os
import pytest

# Override env vars BEFORE any app imports
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test:token")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-123")
os.environ.setdefault("DRY_RUN", "true")
