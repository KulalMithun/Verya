# TDR 002: Offline Sync Engine & Idempotent Event Ledger

## Status
Accepted

## Context
Industrial warehouse floors frequently suffer from intermittent Wi-Fi coverage due to steel racking, cold storage insulation, and RF deadzones. If a mobile scanner loses connectivity while confirming a pick, an operator must not be blocked. However, naively retrying offline requests upon reconnecting risks executing multiple deductions for the same physical pick.

## Decision
We implemented a dual-sided offline synchronization system:
1. **Client Ledger (IndexedDB + LocalStorage)**:
   - When offline, every operator action generates a deterministic `SyncEvent` containing:
     - `event_id`: Unique UUIDv4 generated at the moment of physical action.
     - `idempotency_key`: Compound key `pick_{task_id}_{event_id}`.
     - `action`: Specific execution verb (`CONFIRM_PICK`, `REPORT_EXCEPTION`).
     - `payload`: Complete transaction parameters.
   - The UI optimistically transitions the task to keep the operator moving.
2. **Server-Side Idempotent Ingestion (`SyncEngine`)**:
   - Every batch POST to `/api/openwes/sync/` is wrapped in `@transaction.atomic`.
   - The backend checks `SyncEvent.objects.filter(idempotency_key=key).first()`.
   - If found, the server skips all side effects, increments `duplicate_count`, and returns the original receipt outcome.
   - If not found, the event is executed, inventory is deducted, the event is marked `PROCESSED`, and an audit log is committed.

## Consequences
- **Positive**: Zero risk of double-depleting stock during network retries or device reconnect storms.
- **Positive**: Operators experience uninterrupted workflow even in zero-connectivity zones.
- **Verification**: Verified via test case where submitting the exact same sync payload twice reports 1 synced on pass 1 and 1 duplicate on pass 2, with unchanged inventory.
