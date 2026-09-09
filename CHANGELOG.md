# Changelog

All notable changes to **Veyra (Warehouse Execution System)** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-09

### Added
- **OpenWES Warehouse Core**:
  - Intelligent S-Shape & Shortest Path heuristic travel route optimizer for picking waves.
  - Multi-Zone workload balancing & dynamic operator task allocation.
  - Multimodal Voice-Directed Picking engine supporting spoken digit phonetic verification (`CHECK 4 2`, `READY`, `SHORT`).
  - Bi-directional host ERP/WMS synchronization engine with real-time discrepancy resolution.
- **Standalone Windows Executable (`Veyra.exe`)**:
  - One-click build script (`build.bat` / `build.py`) compiling the entire stack into a single self-contained binary.
  - Embedded Django backend, React SPA frontend, migrations, and template SQLite database.
  - Portable persistent data storage (`./data/`) adjacent to executable.
  - Automatic browser launch upon server startup.
- **Executive & Operator Interfaces**:
  - Real-time Executive Warehouse Dashboard with dynamic KPIs, zone throughput metrics, and exception charts.
  - Full-screen Rugged Tablet Operator Mode with audio feedback and barcode scanner validation.
  - Live Floor Supervisor Control Board with zone workload heatmaps and immediate task reassignment.
  - Complete Audit Trail viewer for compliance and exception tracking.
- **Unified Single-Port Web Serving**:
  - Django Whitenoise production integration serving the modern React SPA directly on port 8000 alongside backend REST APIs.
