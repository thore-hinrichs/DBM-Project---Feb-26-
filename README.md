# CarSharing Group 6 — Flask App (Assignment 7)

Connects to your MySQL DB and runs the Assignment 6 transactions:

1) Feature 1: SELECT from view `v_vehicle_latest_location` (filtered by zone_type) + INSERT Reservation
2) Feature 2: UPDATE MaintenanceTicket to closed (fires your triggers)
3) Feature 3: DELETE Reservation by (customer_id, vehicle_id, start_time, status)

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

## Run
```bash
flask --app app run --debug
```
Open http://127.0.0.1:5000
