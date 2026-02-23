from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class ReservationInput:
    customer_id: int
    vehicle_id: int
    start_time: str
    end_time: Optional[str]
    status: str
    placed_time: str
    channel: str
    promo_code: Optional[str]
    assigned_at: Optional[str]
    pickup_condition: Optional[str]
    pickup_odometer: Optional[int]


@dataclass
class Txn1Result:
    reservation_id: int
    latest: List[Dict[str, Any]]
    inserted_record: Optional[Dict[str, Any]] = None  # proof: row as stored in DB


class CarSharingRepository:
    def __init__(self, database):
        self._db = database

    def select_latest_locations_by_zone_type(self, zone_type: str) -> List[Dict[str, Any]]:
        sql = """SELECT * FROM v_vehicle_latest_location
                 WHERE zone_type = %s
                 ORDER BY vehicle_id;"""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (zone_type,))
            return cur.fetchall()

    def select_all_reservations(self, limit: int = 200) -> List[Dict[str, Any]]:
        """All rows from Reservation table (for display after insert)."""
        sql = """SELECT * FROM Reservation ORDER BY reservation_id DESC LIMIT %s;"""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (limit,))
            return cur.fetchall()

    def get_distinct_zone_types(self) -> List[str]:
        sql = """SELECT DISTINCT zone_type FROM v_vehicle_latest_location ORDER BY zone_type;"""
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return [row[0] for row in cur.fetchall()]

    def run_txn1_view_and_insert(
        self, zone_type: str, reservation: ReservationInput
    ) -> Txn1Result:
        """Single transaction: SELECT from view, then INSERT Reservation."""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT * FROM v_vehicle_latest_location
                   WHERE zone_type = %s ORDER BY vehicle_id""",
                (zone_type,),
            )
            latest = cur.fetchall()

            cur2 = conn.cursor()
            cur2.execute(
                """INSERT INTO Reservation (
                      customer_id, vehicle_id, start_time, end_time, status,
                      placed_time, channel, promo_code, assigned_at, pickup_condition, pickup_odometer
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    reservation.customer_id,
                    reservation.vehicle_id,
                    reservation.start_time,
                    reservation.end_time,
                    reservation.status,
                    reservation.placed_time,
                    reservation.channel,
                    reservation.promo_code,
                    reservation.assigned_at,
                    reservation.pickup_condition,
                    reservation.pickup_odometer,
                ),
            )
            new_id = cur2.lastrowid
            conn.commit()
            inserted_record = self._get_reservation_by_id(conn, new_id)
            return Txn1Result(reservation_id=new_id, latest=latest, inserted_record=inserted_record)

    def _get_reservation_by_id(self, conn, reservation_id: int) -> Optional[Dict[str, Any]]:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM Reservation WHERE reservation_id = %s", (reservation_id,))
        return cur.fetchone()

    def get_reservation_by_id(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        with self._db.connection() as conn:
            return self._get_reservation_by_id(conn, reservation_id)

    def close_maintenance_ticket(
        self, vehicle_id: int, ticket_no: int, closed_at: str, status: str = "closed"
    ) -> int:
        sql = """UPDATE MaintenanceTicket
                 SET status = %s, closed_at = %s
                 WHERE vehicle_id = %s AND ticket_no = %s;"""
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (status, closed_at, vehicle_id, ticket_no))
            affected = cur.rowcount
            conn.commit()
            return affected

    def get_maintenance_ticket(
        self, vehicle_id: int, ticket_no: int
    ) -> Optional[Dict[str, Any]]:
        sql = """SELECT * FROM MaintenanceTicket
                 WHERE vehicle_id = %s AND ticket_no = %s;"""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (vehicle_id, ticket_no))
            return cur.fetchone()

    def get_reservation_by_keys(
        self, customer_id: int, vehicle_id: int, start_time: str, status: str
    ) -> Optional[Dict[str, Any]]:
        sql = """SELECT * FROM Reservation
                 WHERE customer_id = %s AND vehicle_id = %s AND start_time = %s AND status = %s;"""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (customer_id, vehicle_id, start_time, status))
            return cur.fetchone()

    def reservation_exists(
        self, customer_id: int, vehicle_id: int, start_time: str, status: str
    ) -> bool:
        return self.get_reservation_by_keys(customer_id, vehicle_id, start_time, status) is not None

    def get_vehicle_status(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        sql = """SELECT vehicle_id, status FROM Vehicle WHERE vehicle_id = %s;"""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (vehicle_id,))
            return cur.fetchone()

    def get_open_maintenance_tickets(self) -> List[Dict[str, Any]]:
        """Return open tickets (status != 'closed') for dropdown."""
        sql = """SELECT vehicle_id, ticket_no FROM MaintenanceTicket
                 WHERE status != 'closed' OR status IS NULL
                 ORDER BY vehicle_id, ticket_no
                 LIMIT 200;"""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql)
            return cur.fetchall()

    def get_reservations_for_dropdown(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return recent reservations for dropdown (customer_id, vehicle_id, start_time, status)."""
        sql = """SELECT customer_id, vehicle_id, start_time, status
                 FROM Reservation ORDER BY start_time DESC LIMIT %s;"""
        with self._db.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (limit,))
            return cur.fetchall()

    def get_customers_for_dropdown(self) -> List[Dict[str, Any]]:
        """Return customer_id list for dropdown. Uses Customer table if present."""
        try:
            sql = """SELECT customer_id FROM Customer ORDER BY customer_id LIMIT 500;"""
            with self._db.connection() as conn:
                cur = conn.cursor(dictionary=True)
                cur.execute(sql)
                return cur.fetchall()
        except Exception:
            return []

    def delete_reservation(
        self, customer_id: int, vehicle_id: int, start_time: str, status: str
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """Returns (rows_affected, deleted_row for proof). Fetches row before delete."""
        deleted_row = self.get_reservation_by_keys(
            customer_id, vehicle_id, start_time, status
        )
        sql = """DELETE FROM Reservation
                 WHERE customer_id=%s AND vehicle_id=%s AND start_time=%s AND status=%s;"""
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (customer_id, vehicle_id, start_time, status))
            affected = cur.rowcount
            conn.commit()
            return affected, deleted_row

    def ping(self) -> bool:
        """Check DB connectivity (for health check)."""
        try:
            with self._db.connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        except Exception:
            return False
