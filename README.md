# CarSharing DBM — Manager Dashboard (Flask + MySQL)

This repository contains our **Database Management** project implementation as a small **Flask** web app connected to a **local MySQL** database.

The database represents our **CarSharing** scenario based on the **RDBS model (Assignment 3)**.  
All required DB objects (tables, sample data, **view(s)**, **trigger(s)**) are created in **Assignment 5**.  
**Assignment 6** defines the transaction logic; the app features follow that logic and demonstrate it in a UI.

---

## Tech stack
- Python + Flask
- MySQL (local / localhost)
- DB driver: `mysql-connector-python`
- `.env` configuration via `python-dotenv`

---

## Features (Manager/Support perspective)

### Feature 1 — Create Reservation (INSERT)
- Shows available vehicles using the view **`v_vehicle_latest_location`** (filtered by `zone_type`)
- Inserts a new record into **`Reservation`**
- Includes validation / constraint checks (e.g. `end_time > start_time`, or optional `NULL` times)
- Invalid input results in a visible **error message** in the UI

### Feature 2 — Close Maintenance Ticket (UPDATE + Trigger)
- Updates **`MaintenanceTicket.status`** to `closed`
- A **trigger** updates the related **`Vehicle.status`** back to `available`
- The UI filters out already closed tickets, so they cannot be selected again

### Feature 3 — Delete Reservation (DELETE)
- Deletes a reservation from **`Reservation`** (based on the selected record/keys)

All changes are persisted and can be verified directly in MySQL.

---

## Prerequisites
- MySQL running locally (e.g., MySQL Workbench)
- Python 3.x
- SQL scripts from **Assignment 5** (schema + inserts + view + triggers)

---

## 1) Database setup (MySQL)

1. Create the database on your local MySQL instance (default expected name):
   - `carsharing_group6_db`

2. Run the SQL from **Assignment 5**:
   - create all tables
   - insert sample data
   - create the view `v_vehicle_latest_location`
   - create the trigger(s) required for the maintenance/availability logic

---

## 2) Python setup

From the project root (where `app.py` and `requirements.txt` are):

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt

---

## 3) Environment variables (.env)

The application reads the database connection settings from a `.env` file (so credentials are not hardcoded).

1. In the project root, create a file named **`.env`** (or copy/rename `example.env` → `.env` if provided).
2. Add your local MySQL credentials:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=carsharing_group6_db
FLASK_SECRET_KEY=dev-secret

---

## 4) Start app

1. run app.py
2. open localhost link
3. if the port is already in use (white screen), try to run different port (for e.g. flask --app app run --debug --port 5001)
