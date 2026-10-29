# OpenBench — API Reference

> **Source of truth:** `CONTEXT.md`. This document describes all REST endpoints.
> Base URL: `http://localhost:8000/api`
> All timestamps are **UTC ISO-8601**. All endpoints return `application/json`.

---

## Authentication

OpenBench uses **JWT Bearer tokens**.

```
Authorization: Bearer <access_token>
```

- Access token TTL: **30 minutes**
- Refresh token TTL: **7 days**
- Role is embedded in the JWT `role` claim.

---

## 1. Auth

### `POST /auth/register`
Register a new user account.

**Request body:**
```json
{
  "email": "rahul@iti-jadavpur.ac.in",
  "full_name": "Rahul Mondal",
  "password": "SecurePass123!",
  "organisation": "ITI Jadavpur"
}
```

**Response `201`:**
```json
{
  "id": 1,
  "email": "rahul@iti-jadavpur.ac.in",
  "full_name": "Rahul Mondal",
  "role": "user",
  "credit_balance": 50,
  "credit_held": 0,
  "organisation": "ITI Jadavpur",
  "created_at": "2026-10-29T10:00:00Z"
}
```

> On registration, a `WELCOME_GRANT` of 50 credits is automatically issued and written to `credit_transactions`. An audit log entry `USER_REGISTERED` is written.

---

### `POST /auth/login`
Obtain access + refresh tokens.

**Request body (form-encoded):**
```
username=rahul@iti-jadavpur.ac.in&password=SecurePass123!
```

**Response `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### `POST /auth/refresh`
Exchange a refresh token for a new access token.

**Request body:**
```json
{ "refresh_token": "eyJ..." }
```

**Response `200`:** Same shape as `/auth/login`.

---

### `GET /auth/me`
Get the currently authenticated user's profile.

**Auth:** Required (any role)
**Response `200`:** Same shape as register response.

---

## 2. Labs

### `GET /labs`
List all active labs.

**Auth:** Public
**Query params:** `city`, `search` (name/institution substring)

**Response `200`:**
```json
[
  {
    "id": 1,
    "name": "Vidyasagar Fab Lab",
    "institution": "Vidyasagar Engineering College",
    "city": "Kolkata",
    "description": "...",
    "equipment_count": 3
  }
]
```

---

### `GET /labs/{lab_id}`
Get lab detail including equipment list.

**Auth:** Public
**Response `200`:**
```json
{
  "id": 1,
  "name": "Vidyasagar Fab Lab",
  "institution": "Vidyasagar Engineering College",
  "city": "Kolkata",
  "description": "...",
  "contact_email": "fablab@vidyasagar.ac.in",
  "equipment": [
    { "id": 1, "name": "3D Printer Alpha", "type": "fabrication", "credit_per_hour": 10, "status": "available" }
  ]
}
```

---

### `POST /labs`
Create a new lab.

**Auth:** `owner` or `admin`

**Request body:**
```json
{
  "name": "Vidyasagar Fab Lab",
  "institution": "Vidyasagar Engineering College",
  "city": "Kolkata",
  "description": "...",
  "contact_email": "fablab@vidyasagar.ac.in"
}
```

**Response `201`:** Full lab object.

---

### `PATCH /labs/{lab_id}`
Update lab details.

**Auth:** `owner` / `manager` of that lab, or `admin`

---

## 3. Equipment

### `GET /equipment`
List all available equipment across all labs.

**Auth:** Public
**Query params:** `lab_id`, `type` (`fabrication`/`testing`/`space`/`other`), `available_from` (datetime), `available_to` (datetime), `max_credit_per_hour`

**Response `200`:**
```json
[
  {
    "id": 1,
    "lab_id": 1,
    "lab_name": "Vidyasagar Fab Lab",
    "name": "3D Printer Alpha",
    "type": "fabrication",
    "credit_per_hour": 10,
    "max_booking_hours": 4,
    "status": "available",
    "image_url": null
  }
]
```

---

### `GET /equipment/{equipment_id}`
Get equipment detail including upcoming availability.

**Auth:** Public
**Response `200`:** Full equipment object + `availability_windows` array.

---

### `GET /equipment/{equipment_id}/slots`
Get bookable time slots for a given date range.

**Auth:** Any authenticated user
**Query params:** `date_from` (date), `date_to` (date, max 14 days ahead)

**Response `200`:**
```json
{
  "equipment_id": 1,
  "slots": [
    {
      "slot_start": "2026-10-30T09:00:00Z",
      "slot_end": "2026-10-30T10:00:00Z",
      "available": true
    }
  ]
}
```

---

### `POST /equipment`
List new equipment in a lab.

**Auth:** `owner` / `manager` of that lab, or `admin`

**Request body:**
```json
{
  "lab_id": 1,
  "name": "3D Printer Alpha",
  "type": "fabrication",
  "description": "Creality Ender 5 Plus — max build 350×350×400mm",
  "credit_per_hour": 10,
  "max_booking_hours": 4,
  "availability_windows": [
    { "day_of_week": 0, "start_time": "09:00", "end_time": "17:00" },
    { "day_of_week": 1, "start_time": "09:00", "end_time": "17:00" }
  ]
}
```

**Response `201`:** Full equipment object.

---

### `PATCH /equipment/{equipment_id}`
Update equipment (name, credit rate, status, availability windows).

**Auth:** `owner` / `manager` of parent lab, or `admin`

---

## 4. Bookings

### `POST /bookings`
Create a new booking. Credits are **held** (not deducted) immediately.

**Auth:** `user` or `admin`

**Request body:**
```json
{
  "equipment_id": 1,
  "slot_start": "2026-10-30T10:00:00Z",
  "slot_end": "2026-10-30T12:00:00Z",
  "purpose": "3D printing prototype for ITI project — gear housing"
}
```

**Response `201`:**
```json
{
  "id": 1,
  "user_id": 1,
  "equipment_id": 1,
  "status": "PENDING",
  "slot_start": "2026-10-30T10:00:00Z",
  "slot_end": "2026-10-30T12:00:00Z",
  "credits_held": 20,
  "credits_charged": 0,
  "purpose": "3D printing prototype...",
  "created_at": "2026-10-29T10:00:00Z"
}
```

**Errors:**
- `402` – insufficient spendable credits
- `409` – slot conflict with an existing `APPROVED` or `IN_PROGRESS` booking
- `422` – slot outside equipment availability windows

---

### `GET /bookings`
List bookings.

**Auth:** Any authenticated user
- `user`: sees own bookings only
- `manager`/`owner`: sees bookings for their lab(s)
- `admin`: sees all bookings

**Query params:** `status`, `equipment_id`, `lab_id`, `from`, `to`, `page`, `page_size`

---

### `GET /bookings/{booking_id}`
Get booking detail.

**Auth:** Booking owner, manager of that lab, or admin.

---

### `POST /bookings/{booking_id}/approve`
Approve a `PENDING` booking.

**Auth:** `manager` of the lab, or `admin`

**Request body:**
```json
{ "note": "Approved — please bring your student ID." }
```

**Response `200`:** Updated booking object.
> Writes `BOOKING_APPROVED` to audit log.

---

### `POST /bookings/{booking_id}/reject`
Reject a `PENDING` booking.

**Auth:** `manager` of the lab, or `admin`

**Request body:**
```json
{ "note": "Slot conflicts with scheduled maintenance." }
```

**Response `200`:** Updated booking object (status → `REJECTED`, held credits released).
> Writes `BOOKING_REJECTED` to audit log.

---

### `POST /bookings/{booking_id}/cancel`
Cancel a booking (any non-terminal state).

**Auth:** Booking owner (own booking only if status is `PENDING` or `APPROVED`), manager, or admin.

**Response `200`:** Updated booking object. Held credits released.
> Writes `BOOKING_CANCELLED` to audit log.

---

### `POST /bookings/{booking_id}/checkin`
Check in to an approved slot. Booking → `IN_PROGRESS`.

**Auth:** Booking owner, or admin.
**Constraint:** Can only check in within ±15 minutes of `slot_start` (evaluated against `app_now()`).

**Response `200`:** Updated booking object.
> Writes `BOOKING_CHECKIN` to audit log.

---

### `POST /bookings/{booking_id}/checkout`
Check out of an active session. Booking → `COMPLETED`. Credits deducted.

**Auth:** Booking owner, or admin.

**Response `200`:**
```json
{
  "booking": { "...": "...", "status": "COMPLETED", "credits_charged": 20 },
  "credit_balance_after": 30
}
```
> Writes `BOOKING_CHECKOUT` and `CREDIT_DEDUCTED` to audit log.

---

## 5. Action Proposals (Human-in-the-Loop)

### `GET /proposals`
List pending action proposals.

**Auth:** `manager` (own lab proposals), `admin` (all)
**Query params:** `status` (default `PENDING`), `proposal_type`, `lab_id`

**Response `200`:**
```json
[
  {
    "id": 1,
    "proposal_type": "NO_SHOW_PENALTY",
    "entity_type": "booking",
    "entity_id": 1,
    "triggered_by": "scheduler",
    "rationale": "Booking B1 (Rahul Mondal, 3D Printer Alpha) had slot_start 2026-10-30T10:00Z. No check-in was recorded by 10:15Z (app_now: 10:20Z). Proposing NO_SHOW status and credit forfeiture of 20 credits.",
    "proposed_payload": { "new_status": "NO_SHOW", "credits_to_forfeit": 20 },
    "status": "PENDING",
    "created_at": "2026-10-30T10:20:00Z"
  }
]
```

---

### `GET /proposals/{proposal_id}`
Get proposal detail.

**Auth:** `manager`, `admin`

---

### `POST /proposals/{proposal_id}/confirm`
Confirm and execute a proposal.

**Auth:** `manager` of the relevant lab, or `admin`

**Request body:**
```json
{ "note": "Confirmed — student was a no-show. Applying penalty." }
```

**Response `200`:** Updated proposal + affected entity.
> Executes the `proposed_payload`, writes `PROPOSAL_CONFIRMED` + action-specific entries to audit log.

---

### `POST /proposals/{proposal_id}/reject`
Reject a proposal (no action taken).

**Auth:** `manager`, `admin`

**Request body:**
```json
{ "note": "Student called ahead — giving benefit of the doubt." }
```

**Response `200`:** Updated proposal (status → `REJECTED`).
> Writes `PROPOSAL_REJECTED` to audit log.

---

## 6. Audit Log

### `GET /audit`
Query the audit log.

**Auth:** `manager` (filtered to own lab entities), `admin` (all)
**Query params:** `entity_type`, `entity_id`, `action`, `actor_id`, `from`, `to`, `page`, `page_size`

**Response `200`:**
```json
{
  "total": 42,
  "page": 1,
  "items": [
    {
      "id": 1,
      "entity_type": "booking",
      "entity_id": 1,
      "action": "BOOKING_CREATED",
      "actor_id": 1,
      "actor_role": "user",
      "payload": { "...": "..." },
      "rationale": null,
      "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
      "hash": "a3f9...",
      "created_at": "2026-10-29T10:00:00Z"
    }
  ]
}
```

---

### `GET /audit/verify`
Verify the integrity of the entire hash chain.

**Auth:** `admin`
**Response `200`:**
```json
{
  "chain_valid": true,
  "total_entries": 42,
  "first_entry_id": 1,
  "last_entry_id": 42
}
```

If `chain_valid: false`, returns the first broken link's `id`.

---

## 7. Credits

### `GET /credits/balance`
Get own credit balance.

**Auth:** `user`, `owner`, `manager`, `admin`

**Response `200`:**
```json
{
  "user_id": 1,
  "credit_balance": 30,
  "credit_held": 20,
  "spendable": 10
}
```

---

### `GET /credits/transactions`
List own credit transactions.

**Auth:** Any authenticated user (own only; admin sees any user's)
**Query params:** `user_id` (admin only), `tx_type`, `page`, `page_size`

---

### `POST /credits/grant`
Grant credits to a user (admin action).

**Auth:** `admin`

**Request body:**
```json
{
  "user_id": 1,
  "amount": 100,
  "description": "Hackathon winner bonus"
}
```

**Response `200`:** Updated credit balance. Writes `CREDIT_ADMIN_GRANT` to audit log.

---

## 8. Users (Admin)

### `GET /admin/users`
List all users.

**Auth:** `admin`
**Query params:** `role`, `search`, `page`, `page_size`

---

### `GET /admin/users/{user_id}`
Get user detail.

**Auth:** `admin`

---

### `PATCH /admin/users/{user_id}`
Update user (role change, deactivation).

**Auth:** `admin`

---

### `POST /admin/users/{user_id}/lab-membership`
Assign a user as manager/owner of a lab.

**Auth:** `admin`

**Request body:**
```json
{ "lab_id": 1, "role": "manager" }
```

---

## 9. Demo Clock (Admin)

All time-based logic uses `app_now()`. These endpoints allow fast-forwarding for demo purposes.

### `GET /admin/clock`
Get current demo clock state.

**Auth:** `admin`
**Response `200`:**
```json
{
  "real_utc": "2026-10-29T15:30:00Z",
  "app_now": "2026-10-29T15:30:00Z",
  "offset_seconds": 0
}
```

---

### `POST /admin/clock/advance`
Fast-forward the demo clock.

**Auth:** `admin`

**Request body:**
```json
{ "seconds": 7200 }
```

**Response `200`:**
```json
{
  "app_now": "2026-10-29T17:30:00Z",
  "offset_seconds": 7200
}
```
> Writes `CLOCK_ADVANCED` to audit log with rationale `"Demo clock advanced by 7200 seconds by admin."`.
> APScheduler jobs that fire on time-crossing will run automatically.

---

### `POST /admin/clock/reset`
Reset demo clock to real UTC (offset = 0).

**Auth:** `admin`
**Response `200`:** Updated clock state.

---

## 10. Seed (Admin / Dev)

### `POST /admin/seed`
Populate the database with all fictional demo data from `CONTEXT.md §11`.

**Auth:** `admin`
**Query params:** `wipe=true` (optional, clears existing data first)

**Response `200`:**
```json
{
  "message": "Demo data seeded successfully.",
  "users_created": 7,
  "labs_created": 2,
  "equipment_created": 5,
  "bookings_created": 3
}
```

---

## Standard Error Responses

| Status | Meaning |
|---|---|
| `400` | Bad request / validation error |
| `401` | Missing or invalid token |
| `403` | Authenticated but insufficient role/permission |
| `402` | Insufficient credits |
| `404` | Resource not found |
| `409` | Conflict (slot overlap, duplicate, invalid state transition) |
| `422` | Unprocessable entity (Pydantic validation) |
| `500` | Internal server error |

**Error body:**
```json
{
  "detail": "Human-readable error message."
}
```

---

## Audit Log Action Codes Reference

| Code | Trigger |
|---|---|
| `USER_REGISTERED` | New user account created |
| `USER_ROLE_CHANGED` | Admin changes a user's role |
| `CREDIT_WELCOME_GRANT` | 50 welcome credits on registration |
| `CREDIT_HELD` | Credits held on booking creation |
| `CREDIT_HOLD_RELEASED` | Hold released on reject/cancel |
| `CREDIT_DEDUCTED` | Credits deducted on checkout |
| `CREDIT_FORFEITED` | Credits forfeited on no-show |
| `CREDIT_ADMIN_GRANT` | Admin manually grants credits |
| `BOOKING_CREATED` | New booking created |
| `BOOKING_APPROVED` | Manager approves booking |
| `BOOKING_REJECTED` | Manager rejects booking |
| `BOOKING_CANCELLED` | Booking cancelled by user or manager |
| `BOOKING_CHECKIN` | User checks in |
| `BOOKING_CHECKOUT` | User checks out |
| `BOOKING_NO_SHOW` | No-show confirmed by manager |
| `PROPOSAL_CREATED` | Scheduler/AI creates a proposal |
| `PROPOSAL_CONFIRMED` | Manager confirms a proposal |
| `PROPOSAL_REJECTED` | Manager rejects a proposal |
| `BADGE_AWARDED` | Achievement badge awarded |
| `EQUIPMENT_CREATED` | New equipment listed |
| `EQUIPMENT_UPDATED` | Equipment details changed |
| `CLOCK_ADVANCED` | Demo clock fast-forwarded (admin) |
| `CLOCK_RESET` | Demo clock reset to real UTC |

