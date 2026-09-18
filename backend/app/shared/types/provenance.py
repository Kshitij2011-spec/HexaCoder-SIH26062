"""Canonical Data Provenance Enumeration."""

from enum import Enum


class DataProvenance(str, Enum):
    """Data provenance classification tags enforced across all entities and events."""
    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    FORECAST = "FORECAST"
    SCENARIO = "SCENARIO"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    PUBLIC_SOURCE = "PUBLIC_SOURCE"
    ADVISORY = "ADVISORY"
