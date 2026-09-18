"""Locations Domain Module (Person B Track B)."""

from backend.app.domains.locations.models import LocationModel
from backend.app.domains.locations.service import LocationService
from backend.app.domains.locations.router import router

__all__ = ["LocationModel", "LocationService", "router"]
