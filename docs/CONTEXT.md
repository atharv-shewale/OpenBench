# OpenBench — Source of Truth

> **Re-read this file before starting every task.**
> Last updated: 2026-10-29

---

## 1. Problem Statement

Universities, engineering colleges, and research institutions own high-value testing and fabrication equipment (oscilloscopes, 3D printers, CNC machines, tensile testers, PCB routers, wet-chemistry benches, etc.) that sits idle outside of teaching hours — often 60–80 % of the week. Meanwhile, local MSMEs, ITI students, and early-stage startups cannot afford the same equipment.

**OpenBench** is a trusted, credit-based marketplace that lets verified institutions safely share their underused spaces and equipment with verified external users, with full auditability and human oversight of every consequential action.

---

## 2. Vision Statement

> *"Every bench, every hour — earning for science."*

---

## 3. Key Stakeholders

| Role | Description |
|---|---|
| **user** | External booker: MSME technician, ITI student, startup founder |
| **owner** | Institution / lab that lists equipment or spaces |
| **manager** | Staff member at the institution who reviews bookings, confirms penalties, and oversees the lab calendar |
| **admin** | Platform super-user: manages credits, users, disputes, system health |

> **Note:** A single person can hold multiple roles (e.g. a manager is also a user on other labs).

---

## 4. Primary Use Case (Demo Journey)

**"An ITI student books a 3D printer slot at Vidyasagar Engineering College, completes the session, and earns a completion badge."**

1. Admin seeds demo data (users, labs, equipment, credit packages).
2. ITI student **Rahul** registers → gets 50 welcome credits.
3. Rahul browses available equipment → finds *3D Printer Alpha* at *Vidyasagar Fab Lab*.
4. Rahul books a 2-hour slot (costs 20 credits) → booking moves to `PENDING`.
5. Manager **Priya** reviews and `APPROVED` the booking.
6. On slot day, Rahul checks in → booking moves to `IN_PROGRESS`.
7. Rahul checks out → booking moves to `COMPLETED`.
8. Audit trail entry written at every state transition.
9. Rahul's credit balance is deducted; lab's earned-credit counter increases.
10. System proposes a "first-use" achievement badge — Priya reviews and confirms.

Every step above is reflected in an append-only, hash-chained audit log.

---

## 5. Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI (Python 3.12) |
| **ORM / DB** | SQLAlchemy 2.x; SQLite (local dev), PostgreSQL (prod via `DATABASE_URL`) |
| **Frontend** | React 18 + Vite + Tailwind CSS 3, served as static files by FastAPI |
| **Background Jobs** | APScheduler (in-process, AsyncIOScheduler) |
| **Auth** | JWT (access + refresh tokens), role-based with `role` claim |
| **Containerisation** | Docker + docker-compose (single compose file) |
| **Demo Clock** | `app_now()` — all time-based logic calls this, never `datetime.utcnow()` directly |

---

## 6. Non-Negotiables

1. **One complete journey works end-to-end** (the ITI student journey above).
2. **Every important action writes to a hash-chained append-only audit log** — no row in `audit_log` is ever updated or deleted; the next row's `prev_hash` links to the previous row's `hash`.
3. **Automated actions are explainable and human-reviewable** — APScheduler jobs may *propose* actions (e.g. no-show penalty, expired slot cancellation) but a manager must *confirm* before they take effect. The proposal record stores the algorithm's reasoning in plain English.
4. **`app_now()` everywhere** — a demo clock endpoint allows fast-forwarding time so judges can see time-based state transitions without waiting.
5. **AI is advisory only** — any AI-generated recommendation is clearly labelled, stored with its rationale, and requires human approval before it changes data.

---

## 7. Booking State Machine

```
                         ┌──────────────┐
                         │   PENDING    │  ← created by user
                         └──────┬───────┘
                    manager     │     manager
                    APPROVED    │     REJECTED
                       ┌────────┴────────┐
                       ▼                 ▼
              ┌─────────────┐    ┌──────────────┐
              │  APPROVED   │    │   REJECTED   │ (terminal)
              └──────┬──────┘    └──────────────┘
                     │
          user       │    auto (APScheduler,
          CHECK-IN   │    no-show proposed →
                     │    manager confirms)
          ┌──────────┴──────────────┐
          ▼                         ▼
  ┌──────────────┐         ┌────────────────────┐
  │  IN_PROGRESS │         │  NO_SHOW_PROPOSED  │ ← job proposes
  └──────┬───────┘         └─────────┬──────────┘
         │                           │ manager confirms
         │ user CHECK-OUT            ▼
         │               ┌──────────────────┐
         │               │    NO_SHOW       │ (terminal, penalty applied)
         │               └──────────────────┘
         ▼
  ┌──────────────┐
  │  COMPLETED   │ (terminal)
  └──────────────┘

Additional transitions (any non-terminal state):
  - User or manager CANCELS → CANCELLED (terminal)
  - APPROVED slot start passes without check-in → NO_SHOW_PROPOSED (by scheduler)
```

### State Definitions

| State | Who can enter | Description |
|---|---|---|
| `PENDING` | User (create booking) | Awaiting manager review |
| `APPROVED` | Manager | Slot confirmed; credits held (not yet deducted) |
| `REJECTED` | Manager | Slot refused; credits not held |
| `CANCELLED` | User or Manager | Explicitly cancelled; any held credits released |
| `IN_PROGRESS` | User (check-in, time window enforced) | Active session |
| `NO_SHOW_PROPOSED` | APScheduler | Scheduler detected missed check-in; awaiting manager confirmation |
| `NO_SHOW` | Manager (confirm proposal) | Penalty applied; held credits forfeited |
| `COMPLETED` | User (check-out) | Session done; credits deducted from balance |

### Credit Flow

| Transition | Credit effect |
|---|---|
| Booking created (`PENDING`) | Credits **held** (reserved, not deducted) |
| `APPROVED` | Hold confirmed |
| `REJECTED` / `CANCELLED` | Hold released |
| `COMPLETED` | Credits **deducted** from user; **credited** to lab's earned balance |
| `NO_SHOW` | Credits **forfeited** (penalty); go to platform pool |

---

## 8. Audit Log (Hash-Chain)

Every row in `audit_log` contains:

- `id` — auto-increment PK
- `entity_type` — e.g. `"booking"`, `"user"`, `"credit_tx"`
- `entity_id` — FK to the affected row
- `action` — e.g. `"BOOKING_APPROVED"`, `"CREDIT_DEDUCTED"`
- `actor_id` — user who triggered the action (null for system)
- `actor_role` — role at time of action
- `payload` — JSON snapshot of relevant state at the time
- `rationale` — plain-English explanation (mandatory for AI/scheduler proposals)
- `prev_hash` — SHA-256 of the previous row's `hash` field
- `hash` — SHA-256(`id || entity_type || entity_id || action || payload || prev_hash`)
- `created_at` — `app_now()` timestamp

The genesis row (`id=1`) has `prev_hash = "0" * 64`.

---

## 9. Demo Clock

```
GET  /api/admin/clock          → { "app_now": "2026-10-29T10:00:00Z", "offset_seconds": 0 }
POST /api/admin/clock/advance  → { "seconds": 7200 }   # fast-forward 2 hours
POST /api/admin/clock/reset    → reset to real UTC
```

`app_now()` in Python: returns `datetime.utcnow() + timedelta(seconds=CLOCK_OFFSET)`.
`CLOCK_OFFSET` is stored in a module-level variable updated by the admin endpoints.

---

## 10. Roles & Permissions Matrix

| Action | user | owner | manager | admin |
|---|---|---|---|---|
| Register / Login | ✓ | ✓ | ✓ | ✓ |
| Browse equipment | ✓ | ✓ | ✓ | ✓ |
| Create booking | ✓ | — | — | ✓ |
| Cancel own booking | ✓ | — | — | ✓ |
| Approve / Reject booking | — | — | ✓ | ✓ |
| Check in / Check out | ✓ (own) | — | — | ✓ |
| List equipment | — | ✓ | ✓ | ✓ |
| Manage lab | — | ✓ | ✓ | ✓ |
| Confirm proposals | — | — | ✓ | ✓ |
| Advance demo clock | — | — | — | ✓ |
| Manage users / credits | — | — | — | ✓ |
| View full audit log | — | — | ✓ (own lab) | ✓ |

---

## 11. Fictional Demo Data Seed

### Institutions / Labs
| ID | Name | Location |
|---|---|---|
| L1 | Vidyasagar Fab Lab | Vidyasagar Engineering College, Kolkata |
| L2 | Suryodaya Electronics Lab | Suryodaya Polytechnic, Pune |

### Equipment
| ID | Lab | Name | Type | Credit/hr |
|---|---|---|---|---|
| E1 | L1 | 3D Printer Alpha | Fabrication | 10 |
| E2 | L1 | CNC Router Mk2 | Fabrication | 25 |
| E3 | L1 | Oscilloscope Bench | Testing | 8 |
| E4 | L2 | PCB Router Delta | Fabrication | 20 |
| E5 | L2 | Tensile Tester Pro | Testing | 30 |

### Users
| ID | Name | Role | Credits | Org |
|---|---|---|---|---|
| U1 | Rahul Mondal | user | 50 | ITI Jadavpur |
| U2 | Sneha Patil | user | 120 | Patil Precision Parts (MSME) |
| U3 | Arjun Kapoor | user | 200 | KapoorTech Startup |
| U4 | Priya Sharma | manager | — | Vidyasagar Engineering College |
| U5 | Ramesh Nair | manager | — | Suryodaya Polytechnic |
| U6 | Dr. Anita Desai | owner | — | Vidyasagar Engineering College |
| U7 | Platform Admin | admin | — | OpenBench |

### Sample Bookings (for demo)
| ID | User | Equipment | Slot | Status |
|---|---|---|---|---|
| B1 | Rahul | 3D Printer Alpha | +1h from now, 2h | PENDING |
| B2 | Sneha | CNC Router Mk2 | +3h from now, 1h | APPROVED |
| B3 | Arjun | Oscilloscope Bench | yesterday, 2h | COMPLETED |

---

## 12. Deployment

```
docker-compose up --build
```

- Port `8000`: FastAPI (serves API + static React build)
- `DATABASE_URL` env var: defaults to `sqlite:///./openbench.db`; set to Postgres DSN for prod
- `SECRET_KEY` env var: JWT signing secret
- `CORS_ORIGINS` env var: comma-separated allowed origins

---

## 13. Project Structure (target)

```
openbench/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── clock.py             # app_now() + demo clock state
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # FastAPI routers (auth, bookings, equipment, admin, …)
│   │   ├── services/            # Business logic (booking_service, credit_service, …)
│   │   ├── audit.py             # Hash-chain audit log writer
│   │   ├── scheduler.py         # APScheduler jobs
│   │   └── seed.py              # Demo data seeder
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # React pages
│   │   ├── components/          # Reusable UI components
│   │   ├── api/                 # Axios API client
│   │   └── store/               # Auth + clock state (Zustand or Context)
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── docs/
│   ├── CONTEXT.md               # ← this file (source of truth)
│   ├── DATA_MODEL.md
│   └── API.md
└── docker-compose.yml
```

