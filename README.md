# LifeFlow — Blood Bank Management System

> **Stack:** Flask (Python 3.14) · MySQL 8.0 · Docker Compose · JavaScript (Vanilla) · Pytest  
> **Status:** Production-Ready & Defensible for SDE Technical Interviews

LifeFlow is an enterprise-grade blood bank management system engineered to model critical real-world healthcare constraints: blood-type ABO/Rh compatibility, urgency-driven queue prioritization, donor eligibility (minimum age 18 and the 90-day donation interval rule), and near-real-time inventory tracking with transaction-safe allocation.

---

## 🚀 Key Architectural Highlights

1. **Normalized 3NF Relational Schema & Composite Indexes:**
   - 7 normalized tables: `users`, `donors`, `requesters`, `blood_units`, `donations`, `blood_requests`, `request_fulfillments`.
   - Composite indexes: `blood_units(status, blood_type)` for $O(1)$ live stock aggregation and `blood_requests(status, urgency, requested_at)` for priority queue sorting.
   - Unique constraint on `request_fulfillments.unit_id` guaranteeing at the database level that a physical blood unit can never be double-allocated.

2. **Concurrency & Transaction Safety:**
   - **Pessimistic Row Locking (`SELECT ... FOR UPDATE`):** When approving requests, candidate viable units are locked under an atomic database transaction. If two admins approve competing requests simultaneously for the same scarce unit, one transaction acquires the lock, fulfills the request, and the second fails safely with an explicit insufficient stock notice. Inventory never goes negative.
   - **Atomic Donation Intake:** Creates both the `BloodUnit` (with 42-day whole blood shelf-life) and the `Donation` log record in a single transaction, rolling back both if an error occurs.

3. **Domain Business Logic (Layered Architecture):**
   - Routes remain thin HTTP controllers.
   - Business rules live in pure, decoupled service modules (`eligibility_service.py`, `compatibility_service.py`, `request_service.py`, `inventory_service.py`, `auth_service.py`) that are 100% unit-tested.

4. **Near-Real-Time Inventory Tracking:**
   - 10-second client-side auto-polling via vanilla JS `fetch('/api/inventory')` with delta highlighting animations, low-stock threshold alerts, and manual refresh controls without heavy WebSocket overhead.

5. **Role-Based Authentication & Security:**
   - 3 roles: `admin`, `donor`, `requester`.
   - Passwords hashed securely using Werkzeug PBKDF2:SHA256 (never plaintext).
   - Server-side `@role_required` route decorators and ownership isolation.

---

## 📊 Database Schema Architecture (3NF)

```
       ┌────────────────────────┐
       │         users          │
       │────────────────────────│
       │ id (PK)                │
       │ name                   │
       │ email (UNIQUE)         │
       │ password_hash          │
       │ role [admin/donor/req] │
       └───────────┬────────────┘
                   │ 1:1
       ┌───────────┴────────────┬────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
┌──────────────┐        ┌──────────────┐         ┌──────────────┐
│    donors    │        │  requesters  │         │  Audit Logs  │
│──────────────│        │──────────────│         │ (Admin User) │
│ id (PK)      │        │ id (PK)      │         └──────────────┘
│ user_id (FK) │        │ user_id (FK) │
│ blood_type   │        │ org_name     │
│ dob          │        │ phone        │
│ last_don_date│        └──────┬───────┘
└──────┬───────┘               │ 1:N
       │ 1:N                   ▼
       │               ┌───────────────────────┐
       ▼               │    blood_requests     │
┌──────────────┐       │───────────────────────│
│  donations   │       │ id (PK)               │
│──────────────│       │ requester_id (FK)     │
│ id (PK)      │       │ blood_type_requested  │
│ donor_id (FK)│       │ units_requested       │
│ unit_id (FK) ◄─┐     │ urgency [crit/urg/rtn]│
│ donated_at   │ │     │ status                │
└──────────────┘ │     └───────────┬───────────┘
                 │ 1:1             │ 1:N
                 ▼                 ▼
       ┌───────────────────┐ 1:1 ┌─────────────────────────┐
       │    blood_units    │◄────┤   request_fulfillments  │
       │───────────────────│     │─────────────────────────│
       │ id (PK)           │     │ id (PK)                 │
       │ blood_type        │     │ request_id (FK)         │
       │ collected_at      │     │ unit_id (FK, UNIQUE)    │
       │ expires_at (+42d) │     │ allocated_at            │
       │ status [avail/used│     └─────────────────────────┘
       └───────────────────┘
```

---

## 🛠️ Quick Setup & Execution

### 1. Launch Containerized MySQL 8
```bash
# Starts MySQL 8 container with healthcheck and auto-initialized schema
docker compose up -d
```

### 2. Environment & Dependencies
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Seed Realistic Demo Data
```bash
python seed.py
```

### 4. Run Development Server
```bash
python run.py
# Server runs on: http://127.0.0.1:5050
```

### Demo Credentials:
- **Admin:** `admin@lifeflow.org` / `admin123`
- **Donor (Eligible, O-):** `donor@lifeflow.org` / `donor123`
- **Donor 2 (Ineligible, 90-day rule):** `recent@lifeflow.org` / `donor123`
- **Requester (Hospital):** `hospital@lifeflow.org` / `request123`
- **Requester (Trauma ICU):** `trauma@lifeflow.org` / `request123`

---

## 🧪 Automated Testing Suite (`pytest`)

LifeFlow includes a comprehensive test suite verifying every domain rule, boundary condition, and multi-threaded race condition against real MySQL:

```bash
pytest -v
```

### Verified Test Categories:
- **Eligibility (`tests/test_eligibility.py`):** Under-18 rejection, exact 18th birthday acceptance, 89-day rejection with exact remaining day countdown, 90-day acceptance, and first-time donor eligibility.
- **Compatibility Matrix (`tests/test_compatibility.py`):** All 8x8 blood type pairs, verifying $O^-$ universal red-cell donation, $AB^+$ universal reception, and Rh factor constraints.
- **Urgency Prioritization (`tests/test_prioritization.py`):** Multi-tier sorting ($Critical \to Urgent \to Routine$) and FIFO submission tiebreaking.
- **Transaction Concurrency (`tests/test_transactions.py`):** Multi-threaded concurrent approval simulation on a scarce unit; asserts pessimistic row locking prevents double-allocation and keeps inventory non-negative.
- **Inventory Aggregates (`tests/test_inventory.py`):** Grouped stock counts, automatic filtering of expired units, and $<3$ unit low-stock threshold warnings.
- **Authentication & Roles (`tests/test_auth.py`):** Password hashing, role gating (403 forbidden), unauthenticated rejection (401), and profile ownership.
- **REST API Contracts (`tests/test_api.py`):** JSON schemas and HTTP response codes matching specifications.

---

## 📡 REST API Reference

| Method | Endpoint | Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Public | Register donor or requester profile |
| `POST` | `/api/auth/login` | Public | Authenticate and start session |
| `POST` | `/api/auth/logout` | Any | End session |
| `POST` | `/api/donors/donate` | Donor | Record donation (server eligibility + 90-day check) |
| `GET` | `/api/donors/me/history`| Donor | Retrieve user's own donation history |
| `GET` | `/api/inventory` | Public | Live available unit counts per blood type |
| `GET` | `/api/admin/inventory/units` | Admin | Filterable physical blood unit inspection |
| `POST` | `/api/requests` | Requester| Submit blood request with urgency tier |
| `GET` | `/api/requests/me` | Requester| Track submitted requests & fulfillment details |
| `GET` | `/api/admin/requests` | Admin | Prioritized request queue (Critical $\to$ Routine) |
| `POST` | `/api/admin/requests/<id>/approve` | Admin | Row-locked transaction approval & unit allocation |
| `POST` | `/api/admin/requests/<id>/reject` | Admin | Reject request with recorded clinical reason |
| `GET` | `/api/admin/dashboard` | Admin | Real database aggregates and low-stock alerts |
