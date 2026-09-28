# Architecture Decision Records (ADRs)

## Overview
This document records the major architectural decisions, trade-offs, and technical rationale for the **EVE Healthcare Backend System**.

---

### ADR-001: Framework & Pattern Selection — FastAPI Modular Monolith

- **Status**: Accepted
- **Context**: The requirements specify building a production-grade, maintainable backend for diagnostic test bookings, pricing offerings, payment simulations, and webhook processing.
- **Decision**: Use **FastAPI** with Python 3.12+ organized as a **Modular Monolith**.
- **Rationale**:
  - Microservices introduce unnecessary network overhead, distributed transaction complexity, and deployment friction for this domain scope.
  - A Modular Monolith provides strict domain separation (API layer, Services layer, Repositories layer, Models, Schemas) while retaining single-process transactional guarantees, simple deployments, and high developer velocity.
  - FastAPI provides native async execution, automatic Pydantic v2 OpenAPI generation, and high performance.

---

### ADR-002: Database & ORM — PostgreSQL with SQLAlchemy 2.0 Async & Alembic

- **Status**: Accepted
- **Context**: Transaction safety, strict relational constraints (foreign keys, uniqueness, decimal precision), and schema migrations are mandatory.
- **Decision**: Use **PostgreSQL** with **SQLAlchemy 2.0 (Async Engine)** and **Alembic**.
- **Rationale**:
  - PostgreSQL delivers ACID compliance, row-level locking (`SELECT ... FOR UPDATE`), and partial unique indexing.
  - SQLAlchemy 2.0 standardizes explicit, type-hinted ORM mappings using `Mapped[...]` and `mapped_column(...)`, avoiding legacy implicit magic.
  - Alembic manages versioned, repeatable database migrations (`alembic upgrade head`).

---

### ADR-003: Monetary Data Types — High-Precision Decimal (`NUMERIC(10, 2)`)

- **Status**: Accepted
- **Context**: Storing test prices, booking amounts, and payment transaction values in floating-point representations introduces rounding errors.
- **Decision**: All financial amounts are stored as PostgreSQL `NUMERIC(10, 2)` and represented in Python using `decimal.Decimal`.
- **Rationale**: Guarantees deterministic precision for INR currency calculations and eliminates binary floating-point inaccuracies.

---

### ADR-004: Price Integrity — Server-Side Price Snapshotting

- **Status**: Accepted
- **Context**: Clients must never be allowed to dictate booking amounts or payment prices. Diagnostic centres may also update test prices in the future.
- **Decision**:
  1. The client submits only `centre_id`, `offering_id`, and `appointment_at`.
  2. The server fetches the current active price from `CentreTestOffering.price` and snapshots it onto `Booking.amount`.
  3. Subsequent price alterations by diagnostic centres do not alter historical booking totals.
- **Rationale**: Prevents price tampering vulnerability and preserves historical ledger accuracy.

---

### ADR-005: Concurrency Protection — Slot Locking & Database Constraints

- **Status**: Accepted
- **Context**: High concurrency could cause double-booking of the same diagnostic appointment slot at a centre.
- **Decision**:
  - Pessimistic locking (`FOR UPDATE`) on centre test offerings during booking creation.
  - Database-level unique index on `(centre_id, offering_id, appointment_at)` for non-cancelled/non-failed bookings.
  - Explicit transactional check (`check_conflicting_booking`) before insertion.
- **Rationale**: Prevents race conditions at both the application service level and database level.

---

### ADR-006: Webhook Security & Multi-Tier Idempotency

- **Status**: Accepted
- **Context**: Webhooks from payment gateways may be retried multiple times, arrive out of order, or be forged by malicious actors.
- **Decision**:
  1. **HMAC SHA256 Signature**: Every webhook request must contain a valid `X-Webhook-Signature` computed using `WEBHOOK_SECRET`.
  2. **Database Persistence**: Webhook events are recorded in a `webhook_events` table with a `UNIQUE(event_id)` constraint.
  3. **Idempotent Response**: If an `event_id` is re-received, the system detects the existing record and returns HTTP 200 with `status: "already_processed"` without modifying payment or booking state.
  4. **Out-of-Order Handling**: If a payment is already `SUCCESS`, subsequent `FAILED` webhooks for the same payment are ignored safely.

---

### ADR-007: Observability & Standardized Error Contracts

- **Status**: Accepted
- **Context**: Debugging runtime exceptions requires request correlation IDs, and API clients require consistent error JSON schemas.
- **Decision**:
  - `RequestIDMiddleware` injects an `X-Request-ID` header into every request and propagates it to structured logs (`app/core/logging.py`).
  - Global exception handlers catch domain exceptions (`AppException`) and return standard JSON error schemas:
    ```json
    {
      "success": false,
      "error": {
        "code": "SLOT_ALREADY_BOOKED",
        "message": "This appointment slot is already booked",
        "request_id": "req_12345"
      }
    }
    ```
