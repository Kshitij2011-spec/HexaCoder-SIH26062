"""Inventory Application Service (Stock Availability Engine, Ledger, Events, Audit)."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.app.domains.inventory.models import (
    InventoryItemModel,
    InventoryStockLotModel,
    InventoryTransactionModel,
)
from backend.app.domains.inventory.repository import InventoryRepository
from backend.app.domains.inventory.schemas import (
    InventoryItemCreate,
    InventoryStockLotCreate,
    StockAvailabilityRead,
    StockReceiptRequest,
    StockReservationRequest,
    StockReleaseRequest,
    StockIssueRequest,
    StockQuarantineRequest,
    StockStatusTransitionRequest,
)
from backend.app.domains.inventory.transitions import validate_inventory_transition
from backend.app.shared.types.states import InventoryStatus, InventoryTransactionType
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError, DomainValidationError


def ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime object is timezone-aware and normalized to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_lot_availability(
    on_hand: Decimal,
    reserved: Decimal,
    quarantined: Decimal,
    damaged: Decimal,
    reorder_point: Optional[Decimal] = None
) -> Tuple[Decimal, bool]:
    """
    Deterministic domain-authoritative availability calculation:
    available = on_hand - (reserved + quarantined + damaged)
    is_deficit = available <= reorder_point (when reorder_point is specified)
    """
    unavailable = reserved + quarantined + damaged
    available = max(Decimal("0"), on_hand - unavailable)
    is_deficit = False
    if reorder_point is not None:
        is_deficit = bool(available <= reorder_point)
    return available, is_deficit


class InventoryService:
    """
    Central domain service for inventory catalog management, stock lot tracking,
    authoritative availability computation, and immutable operational ledger movements.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = InventoryRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    # ============================================================
    # 1. CATALOG ITEMS
    # ============================================================

    def create_item(
        self,
        data: InventoryItemCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> InventoryItemModel:
        """Registers a new standard catalog item."""
        cid = correlation_id or uuid.uuid4()

        existing = self.repo.get_item_by_code(data.item_code)
        if existing:
            raise ConflictError(f"Inventory item with code '{data.item_code}' already exists.")

        item = InventoryItemModel(
            id=uuid.uuid4(),
            item_code=data.item_code,
            item_name=data.item_name,
            category=data.category,
            unit=data.unit,
            criticality=data.criticality.value,
            description=data.description,
            operational_metadata=data.operational_metadata,
            data_provenance=data.data_provenance.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        created = self.repo.create_item(item)

        self.audit_service.record_audit(
            action="CREATE_INVENTORY_ITEM",
            entity_type="INVENTORY_ITEM",
            entity_id=created.id,
            after_snapshot={"item_code": created.item_code, "category": created.category},
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="InventoryItemCreated",
            entity_type="INVENTORY_ITEM",
            entity_id=created.id,
            new_state=created.criticality,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            correlation_id=cid,
            evidence={"item_code": created.item_code, "unit": created.unit},
        )

        self.session.commit()
        return created

    def get_item(self, item_id: uuid.UUID) -> InventoryItemModel:
        """Retrieves item by UUID or raises EntityNotFoundError."""
        item = self.repo.get_item_by_id(item_id)
        if not item:
            raise EntityNotFoundError("InventoryItem", item_id)
        return item

    def list_items(
        self,
        category: Optional[str] = None,
        criticality: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryItemModel], int]:
        """Lists catalog items with optional filtering and pagination."""
        return self.repo.list_items(
            category=category,
            criticality=criticality,
            page=page,
            page_size=page_size
        )

    # ============================================================
    # 2. STOCK LOTS
    # ============================================================

    def create_stock_lot(
        self,
        data: InventoryStockLotCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> InventoryStockLotModel:
        """Registers a physical stock lot at an operational location."""
        cid = correlation_id or uuid.uuid4()

        # Validate item exists
        self.get_item(data.inventory_item_id)

        # Invariant checks
        if data.reserved_quantity + data.quarantined_quantity + data.damaged_quantity > data.on_hand_quantity:
            raise DomainValidationError(
                "Total unavailable stock (reserved + quarantined + damaged) cannot exceed on-hand quantity."
            )

        lot = InventoryStockLotModel(
            id=uuid.uuid4(),
            inventory_item_id=data.inventory_item_id,
            lot_code=data.lot_code,
            location_id=data.location_id,
            on_hand_quantity=data.on_hand_quantity,
            reserved_quantity=data.reserved_quantity,
            quarantined_quantity=data.quarantined_quantity,
            damaged_quantity=data.damaged_quantity,
            status=data.status.value,
            condition=data.condition,
            reorder_point=data.reorder_point,
            replenishment_lead_days=data.replenishment_lead_days,
            next_inbound_at=ensure_utc(data.next_inbound_at) if data.next_inbound_at else None,
            dependent_asset_id=data.dependent_asset_id,
            dependent_mission_id=data.dependent_mission_id,
            operational_metadata=data.operational_metadata,
            data_provenance=data.data_provenance.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        created = self.repo.create_stock_lot(lot)

        # If registered with initial physical on-hand quantity, record opening RECEIPT transaction
        if data.on_hand_quantity > 0:
            tx = InventoryTransactionModel(
                id=uuid.uuid4(),
                stock_lot_id=created.id,
                transaction_type=InventoryTransactionType.RECEIPT.value,
                quantity=data.on_hand_quantity,
                reference_type="OPENING_BALANCE",
                reference_id=None,
                performed_by_person_id=actor_person_id,
                occurred_at=datetime.now(timezone.utc),
                notes="Initial physical stock lot intake",
                operational_metadata={},
                data_provenance=created.data_provenance,
                created_at=datetime.now(timezone.utc),
            )
            self.repo.append_transaction(tx)

        self.audit_service.record_audit(
            action="CREATE_STOCK_LOT",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=created.id,
            after_snapshot={
                "location_id": str(created.location_id),
                "on_hand_quantity": float(created.on_hand_quantity),
                "status": created.status
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="StockLotCreated",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=created.id,
            new_state=created.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=created.location_id,
            correlation_id=cid,
            evidence={
                "on_hand": float(created.on_hand_quantity),
                "location_id": str(created.location_id)
            },
        )

        self.session.commit()
        return created

    def get_stock_lot(self, lot_id: uuid.UUID) -> InventoryStockLotModel:
        """Retrieves stock lot by UUID or raises EntityNotFoundError."""
        lot = self.repo.get_stock_lot_by_id(lot_id)
        if not lot:
            raise EntityNotFoundError("InventoryStockLot", lot_id)
        return lot

    def list_stock_lots(
        self,
        inventory_item_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryStockLotModel], int]:
        """Lists stock lots with optional filtering and pagination."""
        return self.repo.list_stock_lots(
            inventory_item_id=inventory_item_id,
            location_id=location_id,
            status=status,
            page=page,
            page_size=page_size
        )

    def get_stock_availability(self, lot_id: uuid.UUID) -> StockAvailabilityRead:
        """Computes domain-authoritative availability breakdown for a stock lot."""
        lot = self.get_stock_lot(lot_id)
        available, is_deficit = calculate_lot_availability(
            on_hand=Decimal(str(lot.on_hand_quantity)),
            reserved=Decimal(str(lot.reserved_quantity)),
            quarantined=Decimal(str(lot.quarantined_quantity)),
            damaged=Decimal(str(lot.damaged_quantity)),
            reorder_point=Decimal(str(lot.reorder_point)) if lot.reorder_point is not None else None
        )
        return StockAvailabilityRead(
            stock_lot_id=lot.id,
            inventory_item_id=lot.inventory_item_id,
            location_id=lot.location_id,
            on_hand_quantity=Decimal(str(lot.on_hand_quantity)),
            reserved_quantity=Decimal(str(lot.reserved_quantity)),
            quarantined_quantity=Decimal(str(lot.quarantined_quantity)),
            damaged_quantity=Decimal(str(lot.damaged_quantity)),
            available_quantity=available,
            reorder_point=Decimal(str(lot.reorder_point)) if lot.reorder_point is not None else None,
            is_deficit=is_deficit,
            status=InventoryStatus(lot.status),
        )

    # ============================================================
    # 3. STOCK MUTATIONS & OPERATIONAL LEDGER
    # ============================================================

    def receive_stock(
        self,
        lot_id: uuid.UUID,
        req: StockReceiptRequest,
        correlation_id: Optional[uuid.UUID] = None
    ) -> InventoryStockLotModel:
        """
        Receives physical goods into stock lot, updating on-hand quantity and appending
        an immutable operational RECEIPT transaction to the ledger.
        """
        cid = correlation_id or uuid.uuid4()
        lot = self.get_stock_lot(lot_id)
        prev_status = lot.status
        prev_on_hand = Decimal(str(lot.on_hand_quantity))

        lot.on_hand_quantity = prev_on_hand + req.quantity
        lot.updated_at = datetime.now(timezone.utc)

        # If stock was ON_ORDER or INBOUND, transition to AVAILABLE upon receipt
        if lot.status in [InventoryStatus.ON_ORDER.value, InventoryStatus.INBOUND.value]:
            lot.status = InventoryStatus.AVAILABLE.value

        self.repo.update_stock_lot(lot)

        # Append ledger transaction
        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            stock_lot_id=lot.id,
            transaction_type=InventoryTransactionType.RECEIPT.value,
            quantity=req.quantity,
            reference_type=req.reference_type,
            reference_id=req.reference_id,
            performed_by_person_id=req.performed_by_person_id,
            occurred_at=datetime.now(timezone.utc),
            notes=req.notes,
            operational_metadata=req.operational_metadata,
            data_provenance=lot.data_provenance,
            created_at=datetime.now(timezone.utc),
        )
        self.repo.append_transaction(tx)

        self.audit_service.record_audit(
            action="RECEIVE_STOCK",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            before_snapshot={"on_hand_quantity": float(prev_on_hand), "status": prev_status},
            after_snapshot={"on_hand_quantity": float(lot.on_hand_quantity), "status": lot.status},
            correlation_id=cid,
            actor_person_id=req.performed_by_person_id,
        )

        self.event_service.append_event(
            event_type="StockReceived",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            previous_state=prev_status,
            new_state=lot.status,
            actor_type="USER" if req.performed_by_person_id else "SYSTEM",
            actor_id=req.performed_by_person_id,
            location_id=lot.location_id,
            correlation_id=cid,
            evidence={
                "received_quantity": float(req.quantity),
                "on_hand_quantity": float(lot.on_hand_quantity),
                "reference_type": req.reference_type,
                "reference_id": str(req.reference_id) if req.reference_id else None
            },
        )

        self.session.commit()
        return lot

    def reserve_stock(
        self,
        lot_id: uuid.UUID,
        req: StockReservationRequest,
        correlation_id: Optional[uuid.UUID] = None
    ) -> InventoryStockLotModel:
        """
        Reserves available stock for a mission, team, or cargo assignment.
        Ensures reservation cannot exceed uncommitted available stock.
        """
        cid = correlation_id or uuid.uuid4()
        lot = self.get_stock_lot(lot_id)
        prev_reserved = Decimal(str(lot.reserved_quantity))
        on_hand = Decimal(str(lot.on_hand_quantity))
        quarantined = Decimal(str(lot.quarantined_quantity))
        damaged = Decimal(str(lot.damaged_quantity))

        available, _ = calculate_lot_availability(on_hand, prev_reserved, quarantined, damaged)
        if req.quantity > available:
            raise DomainValidationError(
                f"Insufficient available stock to reserve. Requested: {req.quantity}, Available: {available}"
            )

        lot.reserved_quantity = prev_reserved + req.quantity
        lot.updated_at = datetime.now(timezone.utc)
        self.repo.update_stock_lot(lot)

        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            stock_lot_id=lot.id,
            transaction_type=InventoryTransactionType.RESERVATION.value,
            quantity=req.quantity,
            reference_type=req.reference_type,
            reference_id=req.reference_id,
            performed_by_person_id=req.performed_by_person_id,
            occurred_at=datetime.now(timezone.utc),
            notes=req.notes,
            operational_metadata=req.operational_metadata,
            data_provenance=lot.data_provenance,
            created_at=datetime.now(timezone.utc),
        )
        self.repo.append_transaction(tx)

        self.audit_service.record_audit(
            action="RESERVE_STOCK",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            before_snapshot={"reserved_quantity": float(prev_reserved)},
            after_snapshot={"reserved_quantity": float(lot.reserved_quantity)},
            correlation_id=cid,
            actor_person_id=req.performed_by_person_id,
        )

        self.event_service.append_event(
            event_type="StockReserved",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            new_state=lot.status,
            actor_type="USER" if req.performed_by_person_id else "SYSTEM",
            actor_id=req.performed_by_person_id,
            location_id=lot.location_id,
            correlation_id=cid,
            evidence={
                "reserved_quantity": float(req.quantity),
                "total_reserved": float(lot.reserved_quantity),
                "reference_type": req.reference_type,
                "reference_id": str(req.reference_id) if req.reference_id else None
            },
        )

        self.session.commit()
        return lot

    def release_reservation(
        self,
        lot_id: uuid.UUID,
        req: StockReleaseRequest,
        correlation_id: Optional[uuid.UUID] = None
    ) -> InventoryStockLotModel:
        """Releases previously committed reservation back into available stock."""
        cid = correlation_id or uuid.uuid4()
        lot = self.get_stock_lot(lot_id)
        prev_reserved = Decimal(str(lot.reserved_quantity))

        if req.quantity > prev_reserved:
            raise DomainValidationError(
                f"Cannot release {req.quantity}; currently reserved is only {prev_reserved}"
            )

        lot.reserved_quantity = prev_reserved - req.quantity
        lot.updated_at = datetime.now(timezone.utc)
        self.repo.update_stock_lot(lot)

        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            stock_lot_id=lot.id,
            transaction_type=InventoryTransactionType.RELEASE.value,
            quantity=req.quantity,
            reference_type=req.reference_type,
            reference_id=req.reference_id,
            performed_by_person_id=req.performed_by_person_id,
            occurred_at=datetime.now(timezone.utc),
            notes=req.notes,
            operational_metadata={},
            data_provenance=lot.data_provenance,
            created_at=datetime.now(timezone.utc),
        )
        self.repo.append_transaction(tx)

        self.audit_service.record_audit(
            action="RELEASE_STOCK_RESERVATION",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            before_snapshot={"reserved_quantity": float(prev_reserved)},
            after_snapshot={"reserved_quantity": float(lot.reserved_quantity)},
            correlation_id=cid,
            actor_person_id=req.performed_by_person_id,
        )

        self.event_service.append_event(
            event_type="StockReservationReleased",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            new_state=lot.status,
            actor_type="USER" if req.performed_by_person_id else "SYSTEM",
            actor_id=req.performed_by_person_id,
            location_id=lot.location_id,
            correlation_id=cid,
            evidence={
                "released_quantity": float(req.quantity),
                "total_reserved": float(lot.reserved_quantity)
            },
        )

        self.session.commit()
        return lot

    def issue_stock(
        self,
        lot_id: uuid.UUID,
        req: StockIssueRequest,
        correlation_id: Optional[uuid.UUID] = None
    ) -> InventoryStockLotModel:
        """
        Issues stock from lot to field / consumer, decrementing physical on-hand quantity.
        Deducts from reserved stock first, or unreserved available stock.
        """
        cid = correlation_id or uuid.uuid4()
        lot = self.get_stock_lot(lot_id)
        prev_on_hand = Decimal(str(lot.on_hand_quantity))
        prev_reserved = Decimal(str(lot.reserved_quantity))
        quarantined = Decimal(str(lot.quarantined_quantity))
        damaged = Decimal(str(lot.damaged_quantity))

        usable = (prev_on_hand - (quarantined + damaged))
        if req.quantity > usable:
            raise DomainValidationError(
                f"Insufficient usable stock to issue. Requested: {req.quantity}, Total usable: {usable}"
            )

        # Prioritize deducting from reserved quantity if reserved
        if req.quantity <= prev_reserved:
            lot.reserved_quantity = prev_reserved - req.quantity
        else:
            lot.reserved_quantity = Decimal("0")

        lot.on_hand_quantity = prev_on_hand - req.quantity

        # If physical on-hand reaches 0, mark as CONSUMED
        if lot.on_hand_quantity == Decimal("0"):
            lot.status = InventoryStatus.CONSUMED.value

        lot.updated_at = datetime.now(timezone.utc)
        self.repo.update_stock_lot(lot)

        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            stock_lot_id=lot.id,
            transaction_type=InventoryTransactionType.ISSUE.value,
            quantity=req.quantity,
            reference_type=req.reference_type,
            reference_id=req.reference_id,
            performed_by_person_id=req.performed_by_person_id,
            occurred_at=datetime.now(timezone.utc),
            notes=req.notes,
            operational_metadata=req.operational_metadata,
            data_provenance=lot.data_provenance,
            created_at=datetime.now(timezone.utc),
        )
        self.repo.append_transaction(tx)

        self.audit_service.record_audit(
            action="ISSUE_STOCK",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            before_snapshot={"on_hand_quantity": float(prev_on_hand), "reserved_quantity": float(prev_reserved)},
            after_snapshot={"on_hand_quantity": float(lot.on_hand_quantity), "reserved_quantity": float(lot.reserved_quantity)},
            correlation_id=cid,
            actor_person_id=req.performed_by_person_id,
        )

        self.event_service.append_event(
            event_type="StockIssued",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            new_state=lot.status,
            actor_type="USER" if req.performed_by_person_id else "SYSTEM",
            actor_id=req.performed_by_person_id,
            location_id=lot.location_id,
            correlation_id=cid,
            evidence={
                "issued_quantity": float(req.quantity),
                "remaining_on_hand": float(lot.on_hand_quantity),
                "reference_type": req.reference_type,
                "reference_id": str(req.reference_id) if req.reference_id else None
            },
        )

        self.session.commit()
        return lot

    def quarantine_stock(
        self,
        lot_id: uuid.UUID,
        req: StockQuarantineRequest,
        correlation_id: Optional[uuid.UUID] = None
    ) -> InventoryStockLotModel:
        """Quarantines stock for inspection, safety, or contamination reasons."""
        cid = correlation_id or uuid.uuid4()
        lot = self.get_stock_lot(lot_id)
        on_hand = Decimal(str(lot.on_hand_quantity))
        reserved = Decimal(str(lot.reserved_quantity))
        prev_quarantined = Decimal(str(lot.quarantined_quantity))
        damaged = Decimal(str(lot.damaged_quantity))

        available, _ = calculate_lot_availability(on_hand, reserved, prev_quarantined, damaged)
        if req.quantity > available:
            raise DomainValidationError(
                f"Insufficient unreserved stock to quarantine. Requested: {req.quantity}, Available: {available}"
            )

        lot.quarantined_quantity = prev_quarantined + req.quantity
        lot.condition = "QUARANTINED"

        # If entire lot is quarantined, update status
        if lot.quarantined_quantity >= on_hand:
            lot.status = InventoryStatus.QUARANTINED.value

        lot.updated_at = datetime.now(timezone.utc)
        self.repo.update_stock_lot(lot)

        tx = InventoryTransactionModel(
            id=uuid.uuid4(),
            stock_lot_id=lot.id,
            transaction_type=InventoryTransactionType.QUARANTINE.value,
            quantity=req.quantity,
            reference_type="QUARANTINE_REASON",
            reference_id=None,
            performed_by_person_id=req.performed_by_person_id,
            occurred_at=datetime.now(timezone.utc),
            notes=req.reason,
            operational_metadata=req.operational_metadata,
            data_provenance=lot.data_provenance,
            created_at=datetime.now(timezone.utc),
        )
        self.repo.append_transaction(tx)

        self.audit_service.record_audit(
            action="QUARANTINE_STOCK",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            before_snapshot={"quarantined_quantity": float(prev_quarantined)},
            after_snapshot={"quarantined_quantity": float(lot.quarantined_quantity)},
            correlation_id=cid,
            actor_person_id=req.performed_by_person_id,
        )

        self.event_service.append_event(
            event_type="StockQuarantined",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            new_state=lot.status,
            actor_type="USER" if req.performed_by_person_id else "SYSTEM",
            actor_id=req.performed_by_person_id,
            location_id=lot.location_id,
            correlation_id=cid,
            evidence={
                "quarantined_quantity": float(req.quantity),
                "total_quarantined": float(lot.quarantined_quantity),
                "reason": req.reason
            },
        )

        self.session.commit()
        return lot

    def transition_status(
        self,
        lot_id: uuid.UUID,
        req: StockStatusTransitionRequest,
        correlation_id: Optional[uuid.UUID] = None
    ) -> InventoryStockLotModel:
        """Validates and applies lifecycle status transition for stock lot."""
        cid = correlation_id or uuid.uuid4()
        lot = self.get_stock_lot(lot_id)
        prev_status = lot.status

        validate_inventory_transition(current_state_str=prev_status, target_state_str=req.target_status.value)

        lot.status = req.target_status.value
        lot.updated_at = datetime.now(timezone.utc)
        self.repo.update_stock_lot(lot)

        self.audit_service.record_audit(
            action="TRANSITION_STOCK_STATUS",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            before_snapshot={"status": prev_status},
            after_snapshot={"status": lot.status, "reason": req.reason},
            correlation_id=cid,
            actor_person_id=req.performed_by_person_id,
        )

        self.event_service.append_event(
            event_type="StockStatusChanged",
            entity_type="INVENTORY_STOCK_LOT",
            entity_id=lot.id,
            previous_state=prev_status,
            new_state=lot.status,
            actor_type="USER" if req.performed_by_person_id else "SYSTEM",
            actor_id=req.performed_by_person_id,
            location_id=lot.location_id,
            correlation_id=cid,
            evidence={"reason": req.reason},
        )

        self.session.commit()
        return lot

    def list_transactions(
        self,
        lot_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryTransactionModel], int]:
        """Retrieves paginated audit transaction history for a stock lot."""
        self.get_stock_lot(lot_id)  # Validate lot exists
        return self.repo.list_transactions_by_lot(lot_id, page=page, page_size=page_size)
