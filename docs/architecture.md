# OpenWES Architecture & Technical Design Document

OpenWES (Open Warehouse Execution System) provides a real-time, high-velocity warehouse execution layer extending the InvenTree inventory system.

---

## 1. System Context & Layering

```mermaid
graph TD
    subgraph Client ["Warehouse Floor & Office Clients"]
        Scanner["Rugged Android Scanners (Zebra, Honeywell)"]
        Tablet["Warehouse Tablet HUD / Voice Headsets"]
        Workstation["Desktop Supervisor & Dispatch Stations"]
    end

    subgraph Frontend ["OpenWES React 18 Application"]
        Router["Mantine v7 / OpenWES Router"]
        HUD["OperatorMode Component"]
        VoiceSTT["Web Speech API / SpeechSynthesis"]
        LocalQueue["IndexedDB Offline Queue"]
        Supervisor["Supervisor Board Heatmap & Exceptions"]
        Analytics["Warehouse Analytics & Velocity"]
    end

    subgraph Backend ["OpenWES Backend Services (Django + DRF)"]
        APIGateway["REST API Endpoints (/api/openwes/)"]
        AuthContext["Role-Based Access Control"]
        
        subgraph Engines ["Execution Engines"]
            AssignmentEngine["Multi-Factor Assignment Engine"]
            RoutingEngine["S-Shape / TSP Pick-Path Optimizer"]
            VoiceEngine["Voice Command Parser & Contextual FSM"]
            SyncEngine["Idempotent Event Ledger & Deduplicator"]
        end

        subgraph OpenWesModels ["OpenWES Domain Models"]
            WarehouseTask["WarehouseTask (FSM State Machine)"]
            WarehouseZone["WarehouseZone & Coordinate Geometry"]
            TaskAssignment["TaskAssignment (Explainable Logs)"]
            WarehouseException["WarehouseException Management"]
            Replenishment["ReplenishmentTask Engine"]
            SyncLedger["SyncEvent Ledger"]
            AuditLog["WarehouseAuditEvent (Immutable)"]
        end
    end

    subgraph InvenTreeFoundation ["InvenTree Master Data"]
        PartMaster["Part Catalog (SKU, IPN, Units)"]
        StockMaster["StockItem & StockLocation Hierarchies"]
        OrderMaster["SalesOrder & Shipments"]
        UserMaster["User & Permission Models"]
    end

    Scanner --> HUD
    Tablet --> HUD
    Workstation --> Supervisor
    Workstation --> Analytics

    HUD <--> LocalQueue
    HUD <--> VoiceSTT
    HUD --> APIGateway
    Supervisor --> APIGateway
    Analytics --> APIGateway

    APIGateway --> Engines
    Engines --> OpenWesModels
    OpenWesModels --> InvenTreeFoundation
```

---

## 2. Warehouse Task Finite State Machine (FSM)

Warehouse tasks enforce strict state transitions to prevent race conditions and illegal floor actions.

```mermaid
stateDiagram-v2
    [*] --> PENDING: Order Allocated / Task Created
    PENDING --> ASSIGNED: Auto-Assigned / Supervisor Assigned
    PENDING --> CANCELLED: Order Cancelled
    
    ASSIGNED --> IN_PROGRESS: Operator Starts Task
    ASSIGNED --> PENDING: Reassigned / Unassigned
    ASSIGNED --> CANCELLED: Cancelled
    
    IN_PROGRESS --> PAUSED: Break / Shift Change
    PAUSED --> IN_PROGRESS: Resume
    
    IN_PROGRESS --> COMPLETED: All Items Picked & Barcode Verified
    IN_PROGRESS --> PARTIAL: Short Pick Confirmed
    IN_PROGRESS --> EXCEPTION: Damaged / Missing / Blocked
    
    EXCEPTION --> IN_PROGRESS: Exception Cleared
    EXCEPTION --> COMPLETED: Approved by Supervisor
    EXCEPTION --> CANCELLED: Voided
    
    PARTIAL --> COMPLETED: Balance Handled
    
    COMPLETED --> [*]
    CANCELLED --> [*]
```

### State Machine Transition Rules
- **Atomic Operations**: All state changes transition inside a database transaction (`@transaction.atomic`).
- **Inventory Side Effects**: Only occur when transitioning to `COMPLETED` or `PARTIAL` with non-zero picked quantities.
- **Audit Logging**: Every transition automatically generates an immutable `WarehouseAuditEvent`.

---

## 3. Pick-Path Optimization Engine

Floor walking time accounts for up to 60% of warehouse operational labor. OpenWES provides modular routing algorithms:

### Algorithms
1. **S-Shape (Snake) Heuristic** (Default):
   - Orders picking locations across parallel aisles in an alternating "S" or "Z" pattern.
   - Operators traverse aisle 1 south-to-north, aisle 2 north-to-south, eliminating aisle re-entries and backtracking.
2. **Nearest-Neighbor TSP Heuristic**:
   - Greedy Euclidean distance ordering for cross-docking or non-standard floor geometries.
3. **Zonal Coordinate Ordering**:
   - Strict lexicographical ordering by `Zone -> Aisle -> Bay -> Level`.

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant HUD as OperatorMode HUD
    participant API as /api/openwes/tasks/optimize-route/
    participant Engine as PickPathRoutingEngine
    participant DB as WarehouseLocationMeta

    Operator->>HUD: Request Route Optimization
    HUD->>API: POST {task_ids: [101, 102, 103, 104], strategy: 'S_SHAPE'}
    API->>DB: Query Bin Coordinates (X, Y, Z, Aisle, Bay)
    DB-->>API: Coordinates Matrix
    API->>Engine: optimize_pick_path(task_dicts, strategy='S_SHAPE')
    Engine-->>API: Ordered Route + Cumulative Distances
    API->>DB: Persist sequence numbers on WarehouseTask
    API-->>HUD: {route: [{step: 1, loc: 'A-01-04'}, {step: 2, loc: 'A-02-02'}, ...]}
    HUD-->>Operator: Display Step-by-Step Optimized Route
```

---

## 4. Multi-Factor Task Assignment Engine

Instead of naive FIFO assignment, OpenWES utilizes a multi-factor score:

$$\text{Total Score} = (0.35 \times D_{\text{travel}}) + (0.30 \times W_{\text{queue}}) + (0.20 \times P_{\text{order}}) + (0.15 \times Z_{\text{transit}})$$

- **$D_{\text{travel}}$ (35%)**: Manhattan distance from operator's current location to pick bin.
- **$W_{\text{queue}}$ (30%)**: Current active backlog assigned to the operator.
- **$P_{\text{order}}$ (20%)**: Order priority weighting (Critical > High > Medium > Low).
- **$Z_{\text{transit}}$ (15%)**: Zone affinity bonus (0 penalty if inside the same zone; positive transit penalty if switching zones).

Every assignment produces an explainable decision log stored in `TaskAssignment.reason`.

---

## 5. Offline Synchronization & Idempotency Architecture

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant Scanner as Scanner HUD (Client)
    participant IDB as IndexedDB Ledger
    participant Net as Network Connection
    participant SyncAPI as /api/openwes/sync/
    participant SyncEngine as SyncEngine
    participant StockItem as InvenTree StockItem

    Note over Scanner,IDB: Offline Mode (Wi-Fi Dropout)
    Operator->>Scanner: Confirm Pick 2 units (SKU: ESP32-S3)
    Scanner->>IDB: Write SyncEvent {event_id: uuid-123, key: 'pick_123', status: 'PENDING'}
    Scanner->>Scanner: Optimistically mark task COMPLETED in UI

    Note over Scanner,Net: Wi-Fi Reconnected
    Scanner->>IDB: Read all pending events
    Scanner->>SyncAPI: POST /api/openwes/sync/ {events: [...]}
    SyncAPI->>SyncEngine: process_sync_batch(events)
    
    alt Event Not Processed
        SyncEngine->>StockItem: Deduct 2 units (56 -> 54)
        SyncEngine->>IDB: Update SyncEvent (Status: PROCESSED)
        SyncEngine-->>Scanner: {synced_count: 1, duplicate_count: 0}
    else Event Already Processed (Duplicate Retry)
        SyncEngine->>SyncEngine: Detect existing idempotency_key
        SyncEngine-->>Scanner: {synced_count: 0, duplicate_count: 1}
        Note over StockItem: Zero additional deduction
    end
```

---

## 6. Voice-Directed Picking FSM

The voice subsystem abstracts browser Web Speech API and offline Vosk engines behind a strict contextual state machine:

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> NAVIGATING: "Ready" / "Start"
    NAVIGATING --> AWAITING_ITEM_CONFIRMATION: "Arrived" / "Ready"
    AWAITING_ITEM_CONFIRMATION --> AWAITING_QUANTITY: Barcode Scanned / "Confirm"
    AWAITING_QUANTITY --> COMPLETED: "Picked <N>" / "Confirm"
    
    NAVIGATING --> EXCEPTION: "Blocked"
    AWAITING_ITEM_CONFIRMATION --> EXCEPTION: "Missing" / "Damaged"
    AWAITING_QUANTITY --> EXCEPTION: "Short Pick"
    
    EXCEPTION --> IDLE: "Next" / Exception Cleared
    COMPLETED --> IDLE: "Next" / "Ready"
```

---

## 7. Audit Logging & Compliance

- Every floor event records an immutable `WarehouseAuditEvent`.
- Log entries include timestamp, actor ID, affected task, source/destination bin, part/SKU, and full JSON payload diffs (previous stock vs. new stock, scanned barcode string, exception notes).
- Audit logs are read-only and indexed for instantaneous supervisor search and compliance reviews.
