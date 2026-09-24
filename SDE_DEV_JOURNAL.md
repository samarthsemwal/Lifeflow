# LifeFlow — SDE Architecture & Development Journal

> **Project:** LifeFlow – Blood Bank Management System  
> **Tech Stack:** Flask (Python 3.14), MySQL 8.0, Docker / Docker Compose, JavaScript (Vanilla), Jinja2, Pytest  
> **Developer:** Samarth Semwal  
> **Purpose:** Ye document aapke poore project ke har component, step, architecture decision, transaction logic, aur interview answers ko point-wise explain karta hai. Isko padhne ke baad aap kisi bhi SDE technical interview mein har ek technical sawal ka crystal-clear answer de sakenge.

---

## 📑 Index
1. [System Architecture & Layered Design](#1-system-architecture--layered-design)
2. [Step-by-Step Implementation Log](#2-step-by-step-implementation-log)
   - [Step 1: Docker & MySQL 8 Containerization](#step-1-docker--mysql-8-containerization)
   - [Step 2: 3NF Database Schema & Relational Design](#step-2-3nf-database-schema--relational-design)
   - [Step 3: Core Domain Services (Business Logic)](#step-3-core-domain-services-business-logic)
   - [Step 4: Role-Based Authentication & Security Layer](#step-4-role-based-authentication--security-layer)
   - [Step 5: Controllers & REST API Surface](#step-5-controllers--rest-api-surface)
   - [Step 6: Frontend & 10-Second Real-Time Polling Engine](#step-6-frontend--10-second-real-time-polling-engine)
   - [Step 7: Automated Testing & Concurrency Race Condition Verification](#step-7-automated-testing--concurrency-race-condition-verification)
   - [Step 8: Realistic Data Seeding](#step-8-realistic-data-seeding)
3. [Top SDE Interview Questions & Model Answers](#3-top-sde-interview-questions--model-answers)
4. [GitHub Green Streak Commit Strategy (Day-by-Day Schedule)](#4-github-green-streak-commit-strategy)

---

## 1. System Architecture & Layered Design

LifeFlow ko standard **Layered Architecture (Separation of Concerns)** pattern par build kiya gaya hai:

```
┌────────────────────────────────────────────────────────┐
│            Presentation Layer (Jinja2 + JS)            │
│  - Responsive UI with CSS custom properties            │
│  - 10s client-side polling engine (fetch API)          │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP Request / JSON Payload
                            ▼
┌────────────────────────────────────────────────────────┐
│             Route Controllers (Blueprints)             │
│  - app/blueprints/auth, donors, requests, admin, api   │
│  - Thin controllers: Only parse input & return status  │
└───────────────────────────┬────────────────────────────┘
                            │ Service Invocation
                            ▼
┌────────────────────────────────────────────────────────┐
│        Service Layer (Pure Domain Business Logic)      │
│  - eligibility_service.py   (Age 18+, 90-day rule)     │
│  - compatibility_service.py (ABO/Rh transfusion rules) │
│  - inventory_service.py     (Aggregation & Expiry)     │
│  - donation_service.py      (Atomic intake transaction)│
│  - request_service.py       (SELECT FOR UPDATE locking)│
└───────────────────────────┬────────────────────────────┘
                            │ ORM Queries & Transactions
                            ▼
┌────────────────────────────────────────────────────────┐
│               Data Access Layer (SQLAlchemy)           │
│  - 7 Normalized Models (3NF) + Composite Indexes       │
└───────────────────────────┬────────────────────────────┘
                            │ PyMySQL Protocol (TCP 3306)
                            ▼
┌────────────────────────────────────────────────────────┐
│             MySQL 8.0 Engine (Docker Container)        │
│  - InnoDB Engine with Row-Level Locking                │
│  - ACID Transactions (BEGIN / COMMIT / ROLLBACK)       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Implementation Log

### Step 1: Docker & MySQL 8 Containerization
- **Kyun banaya:** Mac par bina kisi system clutter ke production MySQL 8 instance chalane ke liye.
- **Kya implement hua:** 
  - `docker-compose.yml`: MySQL 8.0 image, root & app credentials (`lifeflow_user`), healthcheck (`mysqladmin ping`), persistent volume (`mysql_data`), aur auto-init mount (`schema.sql` mapped to `/docker-entrypoint-initdb.d/`).
  - `.env` aur `.env.example`: Secrets and database connection strings.
- **Faayda:** Ek command `docker compose up -d` se pura database container ready ho jata hai.

### Step 2: 3NF Database Schema & Relational Design
- **Kyun banaya:** Resume claim *"backed by a normalized relational schema with optimized SQL joins"* ko defend karne ke liye.
- **Tables (7 Normalized Tables):**
  1. `users`: Authentication credentials, role ENUM(`admin`, `donor`, `requester`), hashed passwords.
  2. `donors`: 1:1 user profile, `blood_type`, `date_of_birth`, `last_donation_date`.
  3. `requesters`: 1:1 user profile, `organization_name`, `contact_phone`.
  4. `blood_units`: Physical blood bags in storage with 42-day whole blood shelf life (`expires_at`), `status` ENUM(`available`, `reserved`, `used`, `expired`).
  5. `donations`: Log of all collection sessions, linking donor to physical unit.
  6. `blood_requests`: Hospital blood requests with `units_requested`, `urgency` ENUM(`critical`, `urgent`, `routine`), `status` ENUM(`pending`, `approved`, `rejected`, `fulfilled`).
  7. `request_fulfillments`: Audit join table mapping which exact unit was given to which request. **Key Detail:** `unit_id UNIQUE` constraint database level par ensure karti hai ki ek physical unit 2 baar allocate ho hi nahi sakti!
- **Composite Indexes:**
  - `blood_units(status, blood_type)`: Live inventory aggregation queries fast $O(1)$ lookups banata hai.
  - `blood_requests(status, urgency, requested_at)`: Urgency-driven queue sorting query ko bina table-scan ke instantly sort karta hai.

### Step 3: Core Domain Services (Business Logic)
- **Kyun banaya:** Business rules routes mein spaghetti code ki tarah nahi honi chahiye. Isko testable Python functions me likha gaya hai:
  - `eligibility_service.py`: 
    - Age Rule: Donor ki date of birth se current age calculate karta hai (`age < 18` $\to$ Reject).
    - 90-Day Rule: Check karta hai `(today - last_donation_date).days < 90`. Agar kam hai, toh exact next eligible date calculate karke return karta hai (`last_donation + 90 days`), taaki UI par user ko *"Not eligible until [Date]"* dikhe.
  - `compatibility_service.py`:
    - Standard medical ABO/Rh matrix dictionary lookup table.
    - $O^-$ universal donor hai (sabko de sakta hai). $AB^+$ universal recipient hai (sabse le sakta hai). $Rh^+$ blood $Rh^-$ ko nahi diya ja sakta.
  - `inventory_service.py`:
    - Group-by aggregation on `blood_units`.
    - Expired units (`expires_at <= NOW()`) ko automatically filter out karta hai.
    - Low-stock threshold alert (< 3 units) flag karta hai.
  - `donation_service.py`:
    - Atomic transaction: `BloodUnit` aur `Donation` record ek saath commit hote hain. Agar unit save ho aur donation fail ho, toh rollback dono ko delete kar deta hai.
  - `request_service.py`:
    - Urgency queue sorting: `CASE urgency WHEN 'critical' THEN 1 WHEN 'urgent' THEN 2 WHEN 'routine' THEN 3 END, requested_at ASC`.
    - Transaction-safe approval with `SELECT ... FOR UPDATE` row-locking! (Details in Step 7).

### Step 4: Role-Based Authentication & Security Layer
- **Password Security:** Passwords kabhi plaintext mein store nahi hote. Werkzeug `generate_password_hash` (PBKDF2 with SHA-256 and salt) use kiya hai.
- **Role Enforcement:** `@role_required('admin')`, `@role_required('donor')`, `@role_required('requester')` decorators route level par verify karte hain. Agar unauthorized role aati hai, toh HTML routes par redirect aur API routes par `403 Forbidden` JSON return hota hai.

### Step 5: Controllers & REST API Surface
- Blueprint controllers organize kiye gaye hain:
  - `/api/inventory`: Public live inventory JSON.
  - `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`.
  - `/api/donors/donate`, `/api/donors/me/history`.
  - `/api/requests`, `/api/requests/me`.
  - `/api/admin/requests`, `/api/admin/requests/<id>/approve`, `/api/admin/requests/<id>/reject`.
  - `/api/admin/dashboard`: Real MySQL aggregates (never mocked).

### Step 6: Frontend & 10-Second Real-Time Polling Engine
- Server-rendered clean Jinja2 templates (`base.html`, `live_inventory.html`, `request_queue.html`, `dashboard.html`).
- **Real-Time Polling (`inventory.js`):**
  - Har 10 seconds mein background mein `/api/inventory` par fetch request bhejta hai.
  - Previous counts se compare karta hai. Agar count change hua, toh particular blood card par CSS keyframe animation (`pulse-update`) trigger hoti hai.
  - "Last sync" timestamp counter update hota hai.
  - Manual "↻ Refresh" button bhi available hai.

### Step 7: Automated Testing & Concurrency Race Condition Verification
- Pytest suite (`pytest -v`) mein 28 tests hain:
  - `test_eligibility.py`: 17 vs 18 age boundary, 89 vs 90 days interval boundary.
  - `test_compatibility.py`: 8x8 matrix (all 64 combinations tested).
  - `test_prioritization.py`: Critical request jump to Rank 1 over older routine requests; FIFO tiebreak for identical urgency.
  - `test_inventory.py`: Expiration filtering, low-stock alerts.
  - `test_transactions.py` (**Interview Star Test**):
    - Concurrency test: 2 threads simultaneously ek single available unit (`AB-`) ko approve karne ki koshish karte hain.
    - Result: Database row-lock ki wajah se exactly 1 request approve hoti hai, dusri fail hoti hai with *"Insufficient inventory"*, unit exactly 1 baar allocate hoti hai, aur inventory count 0 rehta hai (never negative -1).

### Step 8: Realistic Data Seeding
- `seed.py` chala kar MySQL mein 5 sample accounts, 33 physical blood units, past donations, aur 3 pending prioritized requests populate ho jate hain.

---

## 3. Top SDE Interview Questions & Model Answers

### Q1: "Aapne race conditions aur double-allocation kaise prevent kiya?"
> **Aapka Answer:**
> *"LifeFlow mein blood requests approve karte waqt hum Pessimistic Row Locking (`SELECT ... FOR UPDATE` via SQLAlchemy `with_for_update()`) use karte hain inside an atomic database transaction.
> Jab admin kisi request ko approve karta hai, toh candidate compatible units lock ho jati hain. Agar koi dusra admin parallel request approve kar raha ho, toh MySQL transaction level par row lock hold hota hai. First transaction complete hokar unit ka status `used` karti hai aur `request_fulfillments` mein row insert karti hai. Second transaction jab lock acquire karti hai toh usko stock available nahi milta aur woh safely rollback ho jati hai.
> Iske alawa, database level par `request_fulfillments.unit_id` par UNIQUE constraint hai, jisse schema level par double allocation mathematically impossible hai."*

### Q2: "Aapka database schema 3NF me normalized kaise hai?"
> **Aapka Answer:**
> *"Humara schema 3rd Normal Form principles follow karta hai:
> 1. **1NF:** Har column atomic hai, koi repeating groups ya comma-separated lists nahi hain.
> 2. **2NF:** Har non-key attribute fully functionally dependent hai primary key par. Donor profiles aur requester profiles alag tables (`donors`, `requesters`) mein 1:1 foreign key se users table se linked hain.
> 3. **3NF:** Koi transitive dependencies nahi hain. For example, `blood_requests` table mein donor ya blood unit ki detail nahi rakhi gayi; fulfillment ke liye ek explicit associative entity `request_fulfillments` banayi gayi hai jo sirf `request_id` aur `unit_id` ko map karti hai."*

### Q3: "SQL Joins ko kaise optimize kiya?"
> **Aapka Answer:**
> *"Humne query patterns ke hisab se composite indexes design kiye:
> 1. `blood_units(status, blood_type)`: Live inventory dashboard har 10 second mein polling karta hai. Is composite index ki wajah se MySQL table scan kiye bina B-Tree index scan se instant count nikalta hai.
> 2. `blood_requests(status, urgency, requested_at)`: Admin queue query `WHERE status='pending' ORDER BY urgency, requested_at` is index se directly satisfy hoti hai bina file-sort overhead ke.
> 3. List views par SQLAlchemy joinedload/eager loading use ki hai taaki N+1 query problem prevent ho sake."*

### Q4: "90-day donation rule kaise implement aur test kiya?"
> **Aapka Answer:**
> *"Domain logic `eligibility_service.py` mein encapsulated hai. Check karta hai `(current_date - last_donation_date).days < 90`. Agar donor ineligible hai, toh hum sirf boolean false nahi bhejte, balki exact `next_eligible_date = last_donation + 90 days` aur remaining days calculate karke return karte hain.
> Isko verify karne ke liye maine boundary value testing ki: 89 days (rejected with exactly 1 day remaining) vs 90 days (eligible)."*

---

## 4. GitHub Green Streak Commit Strategy (Day-by-Day Schedule)

Aapne kaha tha ki saara code ek saath push nahi karna hai taaki GitHub par **everyday commit streak (green boxes)** banti rahe.

Maine local Git repo initialize kar diya hai (`git init`). Neeche aapke liye **6-Day Commit Schedule** hai. Aap har din ek command run karke commit kar sakte hain:

### 🟢 Day 1: Project Architecture & Environment
```bash
git add .gitignore README.md SDE_DEV_JOURNAL.md docker-compose.yml .env.example requirements.txt run.py
git commit -m "chore(infra): setup project structure, Docker Compose MySQL 8, and env configuration"
```

### 🟢 Day 2: 3NF Relational Database Schema & Models
```bash
git add schema.sql app/__init__.py app/config.py app/extensions.py app/models/
git commit -m "feat(database): implement 3NF normalized schema, SQLAlchemy models, and composite indexes"
```

### 🟢 Day 3: Domain Service Layer (Eligibility, Compatibility, Transactions)
```bash
git add app/services/
git commit -m "feat(services): implement donor eligibility (90-day rule), ABO/Rh compatibility, and locked transactions"
```

### 🟢 Day 4: Automated Test Suite (Pytest TDD & Concurrency Verification)
```bash
git add pytest.ini tests/
git commit -m "test(core): add comprehensive pytest suite covering eligibility, compatibility, and concurrency race-conditions"
```

### 🟢 Day 5: Controllers, Blueprints & REST API Endpoints
```bash
git add app/blueprints/
git commit -m "feat(api): implement REST API surface and route blueprints with role-based access control"
```

### 🟢 Day 6: Frontend Interface & Real-Time Polling Engine
```bash
git add app/static/ app/templates/ seed.py
git commit -m "feat(ui): add server-rendered Jinja2 views and 10s vanilla JS inventory polling engine"
```

> **Tip for Push:** Jab aap GitHub par empty repo banayenge (`git remote add origin <your-github-url>`), toh roz ek commit banakar `git push origin main` karenge, toh aapki roz ek green box create hogi!
