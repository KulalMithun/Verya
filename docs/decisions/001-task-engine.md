# TDR 001: Warehouse Task Execution Engine & State Machine

## Status
Accepted

## Context
Traditional InvenTree models orders (`SalesOrder`) and physical parts (`StockItem`), but does not have an atomic execution abstraction for discrete warehouse floor tasks (e.g. pick a specific line item from bin A-01-04, route an operator, confirm physical count, report damaged items). Without a task engine, operations rely on direct stock edits without concurrency guards, state tracking, or progress visibility.

## Decision
We implemented a dedicated `WarehouseTask` model backed by a Finite State Machine (FSM):
1. **States**: `PENDING`, `ASSIGNED`, `IN_PROGRESS`, `PAUSED`, `COMPLETED`, `PARTIAL`, `EXCEPTION`, `CANCELLED`.
2. **Explicit Transition Methods**:
   - `task.assign(operator)`
   - `task.start()`
   - `task.pause()`
   - `task.confirm_pick(quantity, scanned_barcode, user)`
   - `task.report_exception(exception_type, description, reported_qty, user)`
3. **Atomic State Guards**: State transitions validate permitted source states against `WarehouseTaskStatus.VALID_TRANSITIONS`. Unauthorized transitions raise a `ValidationError`.
4. **Inventory Synchronization**: Physical inventory deduction is wrapped in `@transaction.atomic` inside `confirm_pick()`, directly reducing `StockItem.quantity` while logging an immutable `WarehouseAuditEvent`.

## Consequences
- **Positive**: Prevents race conditions where two operators pick the same inventory item concurrently.
- **Positive**: Provides instantaneous floor visibility for supervisors and dispatch algorithms.
- **Trade-off**: Requires explicit task lifecycle management rather than arbitrary ad-hoc stock edits.
