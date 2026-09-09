# Contributing to Veyra

Thank you for your interest in contributing to **Veyra** (Open Warehouse Execution System)!

---

## 🏗️ Architecture Overview

The Veyra codebase is split into two layers:

1. **Backend — Python & Django (`src/backend/InvenTree/`)**
   - Implements core OpenWES engines (`src/backend/InvenTree/openwes/`): wave routing, dynamic operator assignment, voice-directed picking, and host sync.
   - Provides high-throughput REST APIs via Django REST Framework.
   - Database persistence handled via SQLite (standalone) or PostgreSQL (production).

2. **Frontend — React & TypeScript (`src/frontend/`)**
   - High-performance Single Page Application built with React 19, Mantine UI, and Vite.
   - Dedicated OpenWES floor views: Executive Dashboard, Operator HUD, Supervisor Board, Task Queue, Analytics, and Audit Viewer.

3. **Standalone Distribution**
   - Automated root PyInstaller packaging script (`build.bat` / `build.py`) compiling the unified application into `dist/Veyra.exe`.

---

## 💻 Development Workflow

### Backend Development
Activate virtual environment and run the development server:
```bash
# Windows
.venv\Scripts\activate
python src/backend/InvenTree/manage.py runserver 8000
```

### Frontend Development
Run the Vite development server with hot-module reload:
```bash
cd src/frontend
npm install
npm run dev
```

### Building the Production Bundle
To build the React production bundle for backend static serving:
```bash
cd src/frontend
npm run build
```

### Building the Standalone Executable
To package into a single Windows executable:
```cmd
.\build.bat
```
*(Outputs to `dist\Veyra.exe`).*

---

## 📝 Coding Standards

- **Python**: Follow PEP 8 standards, keep type hints clean, and avoid global side effects in engine modules.
- **TypeScript / React**: Use strictly typed interfaces, Mantine theme components, and avoid un-extracted Lingui macro wrappers on dynamic runtime strings.
- **Git Commit Messages**: Write clear, descriptive commit messages describing the feature or bugfix.
