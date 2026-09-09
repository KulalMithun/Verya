# 📚 Veyra Documentation

Welcome to the technical documentation for **Veyra** — a modern, resilient, high-throughput Warehouse Execution System (OpenWES).

---

## 📑 Documentation Index

| Document | Description |
|---|---|
| [System Architecture](architecture.md) | High-level system architecture, engine interactions, data model, and hardware interfacing. |
| [Deployment Guide](deployment.md) | Comprehensive deployment manual for Standalone `.exe`, Docker Compose, and Production Linux (Gunicorn + Nginx + PostgreSQL). |
| [REST API Reference](api.md) | Complete OpenAPI / REST specification for OpenWES engines, orders, tasks, and operator endpoints. |
| [Architecture Decisions (ADR)](decisions/) | Architectural Decision Records: Core Architecture, Real-Time Data Sync, and Voice-Directed Picking. |

---

## 🏢 Platform Overview

Veyra bridges enterprise resource planning (ERP) / warehouse management (WMS) with real-time floor physical execution:

```
[ ERP / WMS Hosts ] ➔ REST APIs / Webhooks
        ⬇
[ VEYRA EXECUTION CORE ]
   ├── Routing & Wave Optimizer Engine
   ├── Dynamic Operator Assignment Engine
   ├── Bi-Directional State Sync Engine
   └── Multimodal Voice-Directed Picking Engine
        ⬇
[ Physical Warehouse Floor: Pickers, Scanners, Voice Headsets, Conveyors ]
```

For setup and quick start, refer to the root [README.md](../README.md).
