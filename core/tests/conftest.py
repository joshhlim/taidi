"""Shared fixtures for the taidi_core test suite."""

from datetime import UTC, datetime
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 1, 20, 0, 0, tzinfo=UTC)


def letter_id(letter: str) -> UUID:
    """Deterministic UUID for a short player label, e.g. letter_id('A'). Keeps fixtures readable."""
    return uuid5(NAMESPACE_DNS, f"taidi-test-player-{letter}")
