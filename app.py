from __future__ import annotations
import logging
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session

from config import get_config
from db import Database, DbSettings
from repositories.carsharing_repo import CarSharingRepository
from services.transactions_service import TransactionsService
from validation import (
    validate_txn1_form,
    validate_txn2_form,
    validate_txn3_form,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# User-facing message for any unexpected error (no DB/query details)
GENERIC_ERROR_MSG = "An error occurred. Please try again or check your input."


def _serialize_for_session(obj):
    """Convert dict/list values so session is JSON-serializable (e.g. datetime, Decimal)."""
    if obj is None:
        return None
    if hasattr(obj, "isoformat"):  # datetime/date
        return obj.isoformat()
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode("utf-8", errors="replace")
    try:
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
    except ImportError:
        pass
    if isinstance(obj, dict):
        return {k: _serialize_for_session(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_session(v) for v in obj]
    return obj


def create_app() -> Flask:
    cfg = get_config()
    app = Flask(__name__)
    app.secret_key = cfg.flask_secret_key

    db = Database(
        DbSettings(
            host=cfg.db_host,
            port=cfg.db_port,
            user=cfg.db_user,
            password=cfg.db_password,
            database=cfg.db_name,
        )
    )

    repo = CarSharingRepository(db)
    service = TransactionsService(repo)

    def _index_context(zone_type: str, latest=None):
        """Build context for index: latest, zone_types, open_tickets, reservations, customers."""
        try:
            zone_types = repo.get_distinct_zone_types()
        except Exception as e:
            logger.exception("Failed to load zone types")
            zone_types = ["SERVICE_AREA"]
        try:
            open_tickets = repo.get_open_maintenance_tickets()
        except Exception as e:
            logger.exception("Failed to load open maintenance tickets")
            open_tickets = []
        try:
            reservations = repo.get_reservations_for_dropdown()
        except Exception as e:
            logger.exception("Failed to load reservations")
            reservations = []
        try:
            customers = repo.get_customers_for_dropdown()
        except Exception as e:
            logger.exception("Failed to load customers")
            customers = []
        if latest is None:
            try:
                latest = repo.select_latest_locations_by_zone_type(zone_type)
            except Exception as e:
                logger.exception("Failed to load latest locations")
                latest = []
        return {
            "zone_type": zone_type,
            "latest": latest,
            "zone_types": zone_types,
            "open_tickets": open_tickets,
            "reservations": reservations,
            "customers": customers,
            "txn1_inserted_record": None,
            "txn2_proof": None,
            "txn3_proof": None,
            "reservation_table": None,
        }

    @app.get("/")
    def index():
        zone_type = request.args.get("zone_type", "SERVICE_AREA")
        ctx = _index_context(zone_type)
        if "last_txn2_proof" in session:
            ctx["txn2_proof"] = session.pop("last_txn2_proof")
        if "last_txn3_proof" in session:
            ctx["txn3_proof"] = session.pop("last_txn3_proof")
        return render_template("index.html", **ctx)

    @app.get("/health")
    def health():
        if repo.ping():
            return {"status": "ok"}, 200
        return {"status": "unhealthy", "message": "Database connection failed"}, 503

    @app.post("/feature1")
    def feature1():
        reservation, zone_type, validation_error = validate_txn1_form(request.form)
        if validation_error:
            flash(validation_error, "error")
            ctx = _index_context(zone_type or "SERVICE_AREA")
            return render_template("index.html", **ctx), 400

        try:
            result = service.run_txn1_view_and_insert(zone_type, reservation)
            flash(
                f"Feature 1 OK: inserted Reservation (reservation_id={result.reservation_id}). "
                "Record persisted in database — see below.",
                "success",
            )
            ctx = _index_context(zone_type, latest=result.latest)
            ctx["txn1_inserted_record"] = result.inserted_record
            try:
                ctx["reservation_table"] = repo.select_all_reservations()
            except Exception:
                ctx["reservation_table"] = None
            return render_template("index.html", **ctx)
        except Exception as e:
            logger.exception("Feature 1 failed")
            flash(GENERIC_ERROR_MSG, "error")
            return redirect(url_for("index", zone_type=zone_type))

    @app.post("/feature2")
    def feature2():
        vehicle_id, ticket_no, closed_at, validation_error = validate_txn2_form(
            request.form
        )
        if validation_error:
            flash(validation_error, "error")
            return redirect(url_for("index"))

        try:
            result = service.run_txn2_close_maintenance_ticket(
                vehicle_id, ticket_no, closed_at
            )
            flash(
                f"Feature 2 OK: updated MaintenanceTicket rows={result.maintenance_rows_affected}. "
                "Data persisted; trigger effect shown below.",
                "success",
            )
            session["last_txn2_proof"] = _serialize_for_session({
                "maintenance_ticket_after": result.maintenance_ticket_after,
                "vehicle_status_after": result.vehicle_status_after,
                "trigger_note": result.trigger_note,
            })
        except Exception as e:
            logger.exception("Feature 2 failed")
            flash(GENERIC_ERROR_MSG, "error")

        return redirect(url_for("index"))

    @app.post("/feature3")
    def feature3():
        customer_id, vehicle_id, start_time, status, validation_error = (
            validate_txn3_form(request.form)
        )
        if validation_error:
            flash(validation_error, "error")
            return redirect(url_for("index"))

        try:
            result = service.run_txn3_delete_reservation(
                customer_id, vehicle_id, start_time, status
            )
            flash(
                f"Feature 3 OK: deleted rows={result.deleted_rows}. "
                "Removed record and verification shown below.",
                "success",
            )
            session["last_txn3_proof"] = _serialize_for_session({
                "deleted_record": result.deleted_record,
                "verified_gone": result.verified_gone,
            })
        except Exception as e:
            logger.exception("Feature 3 failed")
            flash(
                str(e) if app.debug else GENERIC_ERROR_MSG,
                "error",
            )

        return redirect(url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
