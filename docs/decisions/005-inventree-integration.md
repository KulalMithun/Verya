# TDR 005: Clean Architecture Integration with InvenTree Core

## Status
Accepted

## Context
A key project requirement was to transform InvenTree into OpenWES without destroying, corrupting, or blindly rewriting core InvenTree functionality. We must preserve upstream compatibility, migrations, attribution, and existing inventory/BOM capabilities.

## Decision
We implemented OpenWES as a self-contained Django application (`openwes`) within InvenTree:
1. **App Boundary (`src/backend/InvenTree/openwes/`)**:
   - Registered cleanly in `INSTALLED_APPS` via `openwes.apps.OpenWesConfig`.
   - Models link to InvenTree core entities (`Part`, `StockItem`, `StockLocation`, `SalesOrder`, `User`) using standard Django foreign keys without altering InvenTree's own migrations or database tables.
   - Core InvenTree data continues to function normally through standard InvenTree views and REST endpoints.
2. **Dedicated OpenWES API Namespace (`/api/openwes/`)**:
   - All execution endpoints are mounted under `/api/openwes/` in `InvenTree/urls.py`, keeping the core `/api/` endpoints intact.
3. **Frontend Coexistence**:
   - OpenWES execution UI components live in `src/frontend/src/pages/openwes/`.
   - Registered under `/openwes/*` in the frontend router.
   - An "OpenWES" execution tab is integrated into the main navigation bar alongside Parts, Stock, Manufacturing, Purchasing, and Sales.
4. **Upstream Attribution**:
   - InvenTree's open-source origin, license (MIT), and contributors are prominently credited in `README.md`, system documentation, and architecture records.

## Consequences
- **Positive**: Future InvenTree core updates can be merged with minimal conflict.
- **Positive**: Users can utilize standard InvenTree features alongside OpenWES execution features seamlessly.
- **Positive**: 100% compliant with open-source licensing and attribution guidelines.
