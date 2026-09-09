# 🔌 Veyra REST API Reference

Veyra provides a high-throughput, comprehensive REST API for warehouse floor execution, ERP synchronization, and automated material handling integration.

---

## 🔐 Authentication

All API endpoints support:
1. **Session Authentication** (for browsers / React SPA)
2. **HTTP Basic Authentication** (`Authorization: Basic <base64(user:pass)>`)
3. **API Token Authentication** (`Authorization: Token <user-token>`)

Interactive OpenAPI / Swagger documentation is available locally at:
- **Swagger UI:** `http://localhost:8000/api-doc/`
- **Redoc UI:** `http://localhost:8000/api-doc/redoc/`

---

## 📦 OpenWES Execution Endpoints

### 1. Warehouse Executive Dashboard
- **`GET /api/openwes/dashboard/`**
  - **Description:** Real-time summary of warehouse operational state.
  - **Response:**
    ```json
    {
      "overview": {
        "orders_awaiting_picking": 10,
        "active_tasks": 18,
        "completed_tasks": 28,
        "items_picked_today": 101.0,
        "pick_accuracy_percentage": 92.9,
        "avg_pick_time_seconds": 24.5,
        "active_operators": 7,
        "open_exceptions": 8
      },
      "charts": {
        "tasks_by_status": [...],
        "zone_performance": [...],
        "picks_timeline": [...]
      }
    }
    ```

### 2. Task Queue & Routing
- **`GET /api/openwes/tasks/`**
  - **Description:** Lists all active, pending, and completed pick/pack/replenish tasks.
  - **Query Parameters:** `status`, `zone`, `operator`, `priority`.
- **`POST /api/openwes/tasks/optimize_routes/`**
  - **Description:** Triggers the S-Shape / Shortest-Path traveling salesman heuristics on the active picking queue for a given zone or order wave.
- **`POST /api/openwes/tasks/{id}/assign/`**
  - **Description:** Dynamically assigns a task to an operator based on proximity and skill certification.

### 3. Operator HUD & Execution
- **`GET /api/openwes/operator/current/`**
  - **Description:** Fetches the active assigned task for the logged-in operator terminal.
- **`POST /api/openwes/operator/confirm_pick/`**
  - **Payload:**
    ```json
    {
      "task_id": 142,
      "scanned_barcode": "SKU-MICRO-001",
      "scanned_location": "LOC-A-01-02",
      "quantity": 5
    }
    ```
- **`POST /api/openwes/operator/report_exception/`**
  - **Payload:**
    ```json
    {
      "task_id": 142,
      "exception_type": "DAMAGED_ITEM",
      "notes": "Packaging compromised on shelf",
      "photo_attachment": null
    }
    ```

### 4. Multimodal Voice-Directed Picking
- **`POST /api/openwes/voice/session/`**
  - **Description:** Initiates or resumes a hands-free headset session.
- **`POST /api/openwes/voice/command/`**
  - **Description:** Parses spoken phonetics ("READY", "CHECK 4 2", "SHORT 2", "REPEAT") and returns synthesized speech response text and audio prompt.

### 5. Host ERP Synchronization
- **`POST /api/openwes/sync/import_orders/`**
  - **Description:** Ingests sales orders, transfer requests, or customer shipment waves from host ERP systems.
- **`GET /api/openwes/sync/export_status/`**
  - **Description:** Returns inventory delta confirmations, finished shipments, and lot tracking data for export to host systems.
