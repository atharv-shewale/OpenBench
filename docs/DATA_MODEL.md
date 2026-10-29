# OpenBench — Data Model

> **Source of truth:** `CONTEXT.md`. This document describes the database schema in detail.

---

## Entity Relationship Overview

```
users ──< credit_transactions
users ──< bookings >── equipment >── labs
users ──< lab_memberships >── labs
bookings ──< audit_log
equipment ──< equipment_availability_windows
bookings ──< action_proposals
```

---

## Tables

### `users`

Stores all platform users regardless of role.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Login identifier |
| `full_name` | VARCHAR(255) | NOT NULL | Display name |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt hash |
| `role` | VARCHAR(20) | NOT NULL, default `'user'` | One of: `user`, `owner`, `manager`, `admin` |
| `credit_balance` | INTEGER | NOT NULL, default `0` | Current spendable credits |
| `credit_held` | INTEGER | NOT NULL, default `0` | Credits reserved for pending/approved bookings |
| `organisation` | VARCHAR(255) | nullable | Employer / institution name |
| `is_active` | BOOLEAN | NOT NULL, default `true` | Soft-disable account |
| `created_at` | DATETIME | NOT NULL, default `app_now()` | |
| `updated_at` | DATETIME | NOT NULL, auto-update | |

> **Invariant:** `credit_balance >= 0` and `credit_held >= 0` at all times. Enforced in `credit_service`.

---

### `labs`

An institution's physical space / facility.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `name` | VARCHAR(255) | NOT NULL | e.g. "Vidyasagar Fab Lab" |
| `institution` | VARCHAR(255) | NOT NULL | e.g. "Vidyasagar Engineering College" |
| `city` | VARCHAR(100) | NOT NULL | |
| `description` | TEXT | nullable | Rich text / markdown |
| `contact_email` | VARCHAR(255) | nullable | |
| `is_active` | BOOLEAN | NOT NULL, default `true` | |
| `created_at` | DATETIME | NOT NULL | |

---

### `lab_memberships`

Associates users (owner, manager roles) to labs they administer.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL | |
| `lab_id` | INTEGER | FK → `labs.id`, NOT NULL | |
| `role` | VARCHAR(20) | NOT NULL | `owner` or `manager` |
| `created_at` | DATETIME | NOT NULL | |

> **Unique constraint:** `(user_id, lab_id)`.

---

### `equipment`

An individual piece of equipment or a bookable space within a lab.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `lab_id` | INTEGER | FK → `labs.id`, NOT NULL | |
| `name` | VARCHAR(255) | NOT NULL | e.g. "3D Printer Alpha" |
| `type` | VARCHAR(50) | NOT NULL | `fabrication`, `testing`, `space`, `other` |
| `description` | TEXT | nullable | |
| `credit_per_hour` | INTEGER | NOT NULL | e.g. `10` |
| `max_booking_hours` | INTEGER | NOT NULL, default `4` | Max single booking length |
| `status` | VARCHAR(20) | NOT NULL, default `'available'` | `available`, `maintenance`, `retired` |
| `image_url` | VARCHAR(512) | nullable | |
| `created_at` | DATETIME | NOT NULL | |
| `updated_at` | DATETIME | NOT NULL | |

---

### `equipment_availability_windows`

Recurring weekly availability windows (when equipment can be booked).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `equipment_id` | INTEGER | FK → `equipment.id`, NOT NULL | |
| `day_of_week` | INTEGER | NOT NULL | 0=Monday … 6=Sunday |
| `start_time` | TIME | NOT NULL | e.g. `09:00` |
| `end_time` | TIME | NOT NULL | e.g. `17:00` |

---

### `bookings`

Central table for all slot reservations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL | The booker |
| `equipment_id` | INTEGER | FK → `equipment.id`, NOT NULL | |
| `status` | VARCHAR(25) | NOT NULL, default `'PENDING'` | See state machine in `CONTEXT.md` |
| `slot_start` | DATETIME | NOT NULL | Requested start (UTC) |
| `slot_end` | DATETIME | NOT NULL | Requested end (UTC) |
| `checked_in_at` | DATETIME | nullable | Actual check-in time |
| `checked_out_at` | DATETIME | nullable | Actual check-out time |
| `credits_held` | INTEGER | NOT NULL, default `0` | Credits reserved on creation |
| `credits_charged` | INTEGER | NOT NULL, default `0` | Credits actually deducted on completion |
| `purpose` | TEXT | nullable | User's stated purpose / project |
| `manager_note` | TEXT | nullable | Manager's comment on approval/rejection |
| `created_at` | DATETIME | NOT NULL | |
| `updated_at` | DATETIME | NOT NULL | |

> **Status values:** `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`, `IN_PROGRESS`, `NO_SHOW_PROPOSED`, `NO_SHOW`, `COMPLETED`

---

### `credit_transactions`

Immutable ledger of all credit movements. Never updated, only appended.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL | |
| `booking_id` | INTEGER | FK → `bookings.id`, nullable | Related booking if applicable |
| `tx_type` | VARCHAR(30) | NOT NULL | `WELCOME_GRANT`, `HOLD`, `HOLD_RELEASE`, `DEDUCT`, `FORFEIT`, `ADMIN_GRANT`, `ADMIN_DEDUCT` |
| `amount` | INTEGER | NOT NULL | Positive = credit added; negative = credit removed |
| `balance_after` | INTEGER | NOT NULL | Snapshot of balance after this tx |
| `description` | TEXT | nullable | Human-readable note |
| `created_at` | DATETIME | NOT NULL | |

---

### `action_proposals`

APScheduler or AI advisory actions that require human confirmation before taking effect.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `proposal_type` | VARCHAR(50) | NOT NULL | e.g. `NO_SHOW_PENALTY`, `AUTO_CANCEL`, `BADGE_AWARD` |
| `entity_type` | VARCHAR(50) | NOT NULL | e.g. `booking`, `user` |
| `entity_id` | INTEGER | NOT NULL | |
| `triggered_by` | VARCHAR(50) | NOT NULL | `scheduler`, `ai`, `system` |
| `rationale` | TEXT | NOT NULL | Plain-English explanation of why this is proposed |
| `proposed_payload` | TEXT | NOT NULL | JSON of what will happen if confirmed |
| `status` | VARCHAR(20) | NOT NULL, default `'PENDING'` | `PENDING`, `CONFIRMED`, `REJECTED` |
| `reviewed_by` | INTEGER | FK → `users.id`, nullable | Manager/admin who acted |
| `reviewed_at` | DATETIME | nullable | |
| `review_note` | TEXT | nullable | Reviewer's comment |
| `created_at` | DATETIME | NOT NULL | |

---

### `audit_log`

Append-only, hash-chained ledger of all consequential actions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `entity_type` | VARCHAR(50) | NOT NULL | `booking`, `user`, `equipment`, `credit_tx`, `proposal`, `clock` |
| `entity_id` | INTEGER | NOT NULL | PK of the affected row |
| `action` | VARCHAR(80) | NOT NULL | e.g. `BOOKING_CREATED`, `BOOKING_APPROVED`, `CREDIT_HELD` |
| `actor_id` | INTEGER | nullable | `users.id`; null for system/scheduler |
| `actor_role` | VARCHAR(20) | nullable | Role at time of action |
| `payload` | TEXT | NOT NULL | JSON snapshot |
| `rationale` | TEXT | nullable | Required for all scheduler/AI actions |
| `prev_hash` | CHAR(64) | NOT NULL | SHA-256 of previous row's `hash`; `"000…0"` for row 1 |
| `hash` | CHAR(64) | NOT NULL, UNIQUE | SHA-256(`id\|entity_type\|entity_id\|action\|payload\|prev_hash`) |
| `created_at` | DATETIME | NOT NULL | `app_now()` — never real `utcnow()` |

> **Integrity rule:** No UPDATE or DELETE is ever issued against this table. Application-level check + DB trigger (where supported).

---

### `badges`

Achievement badges that can be awarded to users.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL | |
| `badge_type` | VARCHAR(50) | NOT NULL | e.g. `FIRST_BOOKING`, `POWER_USER`, `NO_SHOW_FREE` |
| `awarded_at` | DATETIME | NOT NULL | |
| `awarded_by` | INTEGER | FK → `users.id`, nullable | Manager/admin; null if auto + confirmed |
| `proposal_id` | INTEGER | FK → `action_proposals.id`, nullable | If awarded via proposal flow |

---

## Credit Balance Invariants

```
credit_balance  = sum of all WELCOME_GRANT + HOLD_RELEASE + ADMIN_GRANT
                - sum of all DEDUCT + FORFEIT + ADMIN_DEDUCT
credit_held     = sum of all HOLD amounts for PENDING/APPROVED bookings
spendable       = credit_balance - credit_held   (must be ≥ 0 to create a new booking)
```

---

## Indexes (recommended)

```sql
CREATE INDEX idx_bookings_user       ON bookings(user_id);
CREATE INDEX idx_bookings_equipment  ON bookings(equipment_id);
CREATE INDEX idx_bookings_status     ON bookings(status);
CREATE INDEX idx_bookings_slot       ON bookings(slot_start, slot_end);
CREATE INDEX idx_audit_entity        ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_actor         ON audit_log(actor_id);
CREATE INDEX idx_credit_tx_user      ON credit_transactions(user_id);
CREATE INDEX idx_proposals_status    ON action_proposals(status);
```

