"""Cargo Domain Module (Person B Track B)."""

from backend.app.domains.cargo.models import CargoConsignmentModel, CargoPackageModel
from backend.app.domains.cargo.service import CargoService, calculate_cargo_risk
from backend.app.domains.cargo.router import router

__all__ = ["CargoConsignmentModel", "CargoPackageModel", "CargoService", "calculate_cargo_risk", "router"]
