from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from repositories.carsharing_repo import (
    CarSharingRepository,
    ReservationInput,
    Txn1Result,
)


@dataclass
class Txn2Result:
    maintenance_rows_affected: int
    vehicle_status_after: Optional[Dict[str, Any]]
    maintenance_ticket_after: Optional[Dict[str, Any]] = None  # proof: updated row in DB
    trigger_note: Optional[str] = None  # e.g. "Trigger executed: vehicle status set to 'available'"


@dataclass
class Txn3Result:
    deleted_rows: int
    deleted_record: Optional[Dict[str, Any]] = None  # proof: row that was removed
    verified_gone: bool = False  # True if we confirmed row no longer exists


class TransactionsService:
    def __init__(self, repo: CarSharingRepository):
        self._repo = repo

    def run_txn1_view_and_insert(
        self, zone_type: str, reservation: ReservationInput
    ) -> Txn1Result:
        return self._repo.run_txn1_view_and_insert(zone_type, reservation)

    def run_txn2_close_maintenance_ticket(
        self, vehicle_id: int, ticket_no: int, closed_at: str
    ) -> Txn2Result:
        affected = self._repo.close_maintenance_ticket(vehicle_id, ticket_no, closed_at)
        status_after = self._repo.get_vehicle_status(vehicle_id)
        ticket_after = self._repo.get_maintenance_ticket(vehicle_id, ticket_no)
        trigger_note = None
        if status_after and str(status_after.get("status")).lower() == "available":
            trigger_note = "Trigger executed: vehicle status set to 'available'."
        return Txn2Result(
            maintenance_rows_affected=affected,
            vehicle_status_after=status_after,
            maintenance_ticket_after=ticket_after,
            trigger_note=trigger_note,
        )

    def run_txn3_delete_reservation(
        self, customer_id: int, vehicle_id: int, start_time: str, status: str
    ) -> Txn3Result:
        deleted_count, deleted_row = self._repo.delete_reservation(
            customer_id, vehicle_id, start_time, status
        )
        verified = not self._repo.reservation_exists(
            customer_id, vehicle_id, start_time, status
        )
        return Txn3Result(
            deleted_rows=deleted_count,
            deleted_record=deleted_row,
            verified_gone=verified,
        )
