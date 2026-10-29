# OpenBench: Comprehensive Technology & Attribution Disclosures

In accordance with ethical engineering practices and hackathon transparency requirements, this document provides a comprehensive inventory of all software libraries, frameworks, open-source packages, user interface icons, and Artificial Intelligence tools utilised throughout the design, development, and testing of **OpenBench**.

---

## 1. Backend Libraries & Frameworks (Python)

All backend dependencies are defined in [`backend/requirements.txt`](./backend/requirements.txt) and operate under permissive open-source licenses (MIT, Apache 2.0, or BSD):

| Library / Package | Version Spec | License | Purpose & Justification |
| :--- | :--- | :--- | :--- |
| **FastAPI** | `^0.110.0` | MIT | High-performance, asynchronous REST API framework with native OpenAPI schema generation. |
| **Uvicorn** | `^0.28.0` | BSD | Lightning-fast ASGI web server implementation for Python. |
| **SQLAlchemy** | `^2.0.28` | MIT | Object-Relational Mapping (ORM) and SQL database toolkit with mapped column typing. |
| **Pydantic** | `^2.6.4` | MIT | Data validation and settings management using Python type annotations. |
| **Pydantic-Settings** | `^2.2.1` | MIT | Hierarchical environment configuration and `.env` parsing. |
| **python-jose** | `^3.3.0` | MIT | Cryptographic JSON Web Token (JWT) encoding, signing, and verification (HS256). |
| **passlib[bcrypt]** | `^1.7.4` | BSD | Secure cryptographic password hashing with salted bcrypt. |
| **python-multipart** | `^0.0.9` | Apache 2.0 | Streaming multi-part form-data parser required for photo uploads. |
| **Pillow (PIL)** | `^10.2.0` | HPND | Python Imaging Library used for pixel alignment, luminance subtraction, and advisory photo-diff generation. |
| **APScheduler** | `^3.10.4` | MIT | In-process background task scheduler executing the grace-period auto-release scanner. |
| **pytest** | `^8.1.1` | MIT | Primary testing framework for unit tests, RBAC isolation, and end-to-end lifecycle verification. |
| **httpx** | `^0.27.0` | BSD | Next-generation HTTP client utilized by Starlette TestClient for API assertions. |
| **pytest-asyncio** | `^0.23.6` | Apache 2.0 | Pytest plugin for testing asynchronous coroutines. |

---

## 2. Frontend Libraries & Frameworks (JavaScript / Node.js)

All frontend dependencies are defined in [`frontend/package.json`](./frontend/package.json) and operate under permissive licenses:

| Library / Package | Version Spec | License | Purpose & Justification |
| :--- | :--- | :--- | :--- |
| **React** | `^18.2.0` | MIT | Declarative component architecture powering the single-page application (SPA). |
| **React DOM** | `^18.2.0` | MIT | DOM rendering engine for React. |
| **React Router DOM** | `^6.22.3` | MIT | Client-side routing, route guards, and navigation state. |
| **Vite** | `^5.1.6` | MIT | Next-generation frontend build tooling with hot module replacement (HMR). |
| **Tailwind CSS** | `^3.4.1` | MIT | Utility-first CSS framework enabling accessible, responsive, high-contrast layouts. |
| **PostCSS & Autoprefixer**| `^8.4.35` / `^10.4.18` | MIT | CSS transformation and cross-browser vendor prefixing. |
| **Lucide React** | `^0.358.0` | ISC | Accessible, lightweight icon pack used throughout navigation, status badges, and action bars. |
| **qrcode** | `^1.5.3` | MIT | Client-side vector and canvas QR code generator for machine terminals and booking passes. |
| **Canvas-Confetti** | `^1.9.2` | MIT | Lightweight visual celebration effect triggered upon successful QR session completion. |

---

## 3. UI Templates, Boilerplates & Media Assets

- **Templates & Boilerplates**: No pre-built commercial admin templates (e.g. Bootstrap Admin, TailwindUI kits) were used. The entire layout, dashboard views, timeline cards, simulator toggles, and modals were custom-designed and authored from scratch using raw Tailwind CSS utility classes.
- **Icons**: Standard SVG iconography sourced entirely from open-source [`lucide-react`](https://lucide.dev/).
- **Fonts**: System sans-serif font stack (`system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`) with fallback support for Devanagari script for Hindi and Marathi localization.
- **Stock Images**: Sample equipment and workshop photos in the demo database are royalty-free placeholder representations. In-app condition photos are dynamically captured or test-uploaded into the private signed media directory.

---

## 4. Artificial Intelligence & Algorithmic Tools Disclosure

### A. AI Coding Assistance
- **Antigravity (Google DeepMind)**: Served as the primary pair-programming and coding assistant during development. Antigravity was utilized for scaffolding boilerplate FastAPI router definitions, formulating SQLAlchemy 2.0 mapped-column models, writing comprehensive pytest integration scenarios, generating mathematical formulations for the Gini coefficient fairness simulator, and compiling technical documentation.
- **Verification Integrity**: All algorithms, business logic rules (rolling hour caps, waitlist ranking score weights, grace-period scans), cryptographic hash chains, and security boundaries were designed, validated, and verified through automated test suites (86 passing tests with zero skipped or failing assertions).

### B. Algorithmic Implementations Within the Platform
- **Pillow Advisory Computer-Vision Diff**: A custom algorithmic visual difference pipeline implemented in `backend/app/services/image_diff_service.py`. It resamples pre- and post-session condition images to matching dimensions (640x480), converts them to grayscale luminance, calculates absolute pixel differences, and renders red bounding masks around changed regions exceeding a 15% delta threshold. It is explicitly labeled in the UI as *"advisory, a human decides"*.
- **Fairness Replay Simulator**: A deterministic, seeded mathematical simulation engine implemented in `backend/app/services/fairness_simulator_service.py` that computes the Lorenz curve and Gini coefficient across simulated user personas competing for machine capacity.
- **Machine Activity Simulator**: A simulated telemetry generator in `frontend/src/components/MachineActivitySimulator.jsx` and `backend/app/routers/equipment.py` that emits synthetic power, voltage, and spindle-run telemetry to demonstrate IoT integration.

---

## 5. Security & Cryptographic Integrity

- **Cryptographic Hash Ledger**: Implements native Python standard library `hashlib.sha256` for tamper-evident chaining. No external proprietary blockchain or distributed ledger protocols were used.
- **Signed Storage URLs**: Implements native Python standard library `hmac` and `hashlib.sha256` with unix timestamp expiry verification to protect equipment condition photos from unauthorized public indexing.
- **Password Protection**: Implements `bcrypt` via Passlib for one-way password salting and hashing. Plaintext credentials are never logged, stored, or transmitted in audit ledgers.

