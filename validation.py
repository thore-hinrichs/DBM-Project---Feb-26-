"""Simple input validation for form data. Returns (value, error_message)."""
from __future__ import annotations
import re
from typing import Optional, Tuple

def _norm_dt(s: str) -> str:
    """Normalize datetime from datetime-local (YYYY-MM-DDTHH:MM) to MySQL format."""
    s = (s or "").strip()
    if not s:
        return s
    if "T" in s:
        s = s.replace("T", " ")
    if len(s) == 16:  # YYYY-MM-DD HH:MM
        s += ":00"
    return s


def validate_positive_int(
    value: Optional[str], field_name: str
) -> Tuple[Optional[int], Optional[str]]:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, f"{field_name} is required."
    try:
        n = int(value)
        if n <= 0:
            return None, f"{field_name} must be a positive number."
        return n, None
    except ValueError:
        return None, f"{field_name} must be a whole number."


def validate_optional_positive_int(
    value: Optional[str], field_name: str
) -> Tuple[Optional[int], Optional[str]]:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, None
    try:
        n = int(value)
        if n < 0:
            return None, f"{field_name} must be 0 or greater."
        return n, None
    except ValueError:
        return None, f"{field_name} must be a whole number."


def validate_required_str(
    value: Optional[str], field_name: str
) -> Tuple[Optional[str], Optional[str]]:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, f"{field_name} is required."
    return value.strip(), None


def validate_datetime(
    value: Optional[str], field_name: str, required: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    normalized = _norm_dt((value or "").strip())
    if not normalized:
        if required:
            return None, f"{field_name} is required."
        return None, None
    # Match YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS
    if not re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(:\d{2})?$", normalized):
        return None, f"{field_name} must be in format YYYY-MM-DD HH:MM or YYYY-MM-DDTHH:MM."
    return normalized, None


def validate_txn1_form(data) -> Tuple[Optional[ReservationInput], Optional[str], Optional[str]]:
    """Validate Txn1 form. Returns (ReservationInput, zone_type, error_message)."""
    from repositories.carsharing_repo import ReservationInput

    zone_type, _ = validate_required_str(
        data.get("zone_type"), "Zone type"
    )
    if not zone_type:
        zone_type = "SERVICE_AREA"

    customer_id, err = validate_positive_int(data.get("customer_id"), "Customer ID")
    if err:
        return None, zone_type, err
    vehicle_id, err = validate_positive_int(data.get("vehicle_id"), "Vehicle ID")
    if err:
        return None, zone_type, err
    start_time, err = validate_datetime(data.get("start_time"), "Start time")
    if err:
        return None, zone_type, err
    placed_time, err = validate_datetime(data.get("placed_time"), "Placed time")
    if err:
        return None, zone_type, err

    end_time, _ = validate_datetime(data.get("end_time"), "End time", required=False)
    status = (data.get("status") or "confirmed").strip() or "confirmed"
    channel = (data.get("channel") or "app").strip() or "app"
    promo_code = (data.get("promo_code") or "").strip() or None
    assigned_at, _ = validate_datetime(data.get("assigned_at"), "Assigned at", required=False)
    pickup_condition = (data.get("pickup_condition") or "").strip() or None
    pickup_odometer, err = validate_optional_positive_int(
        data.get("pickup_odometer"), "Pickup odometer"
    )
    if err:
        return None, zone_type, err

    return (
        ReservationInput(
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            start_time=start_time,
            end_time=end_time,
            status=status,
            placed_time=placed_time,
            channel=channel,
            promo_code=promo_code,
            assigned_at=assigned_at,
            pickup_condition=pickup_condition,
            pickup_odometer=pickup_odometer,
        ),
        zone_type,
        None,
    )


def validate_txn2_form(data) -> Tuple[Optional[int], Optional[int], str, Optional[str]]:
    """Returns (vehicle_id, ticket_no, closed_at, error_message)."""
    vehicle_id, err = validate_positive_int(data.get("vehicle_id"), "Vehicle ID")
    if err:
        return None, None, "", err
    ticket_no, err = validate_positive_int(data.get("ticket_no"), "Ticket number")
    if err:
        return None, None, "", err
    from datetime import datetime
    closed_at_raw = (data.get("closed_at") or "").strip()
    closed_at, err = validate_datetime(
        closed_at_raw, "Closed at", required=False
    )
    if err:
        return None, None, "", err
    if not closed_at:
        closed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return vehicle_id, ticket_no, closed_at, None


def validate_txn3_form(data) -> Tuple[Optional[int], Optional[int], Optional[str], str, Optional[str]]:
    """Returns (customer_id, vehicle_id, start_time, status, error_message)."""
    customer_id, err = validate_positive_int(data.get("customer_id"), "Customer ID")
    if err:
        return None, None, None, "", err
    vehicle_id, err = validate_positive_int(data.get("vehicle_id"), "Vehicle ID")
    if err:
        return None, None, None, "", err
    start_time, err = validate_datetime(data.get("start_time"), "Start time")
    if err:
        return None, None, None, "", err
    status = (data.get("status") or "confirmed").strip() or "confirmed"
    return customer_id, vehicle_id, start_time, status, None
