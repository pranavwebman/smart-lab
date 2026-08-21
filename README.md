# Smart Clinical Lab

Production-Ready Laboratory Management Desktop Application for Clinical/Diagnostic Laboratories in Kerala, India.

## Vision & Features
- **Offline-First & Windows Desktop Application**: Designed with Python, Tkinter/ttk, SQLite, SQLAlchemy, and ReportLab.
- **Dynamic Test Catalog**: Fully configurable test catalog, categories, parameters, and reference ranges (numeric, text, option-based). Zero hardcoded clinical tests in Python code.
- **Complete End-to-End Workflow**:
  - Patient Registration & Rapid Search (ID/Name/Phone)
  - Order Creation & Automatic Pricing
  - Sample Collection Tracking
  - Result Entry with Range Flags (LOW / NORMAL / HIGH)
  - Role-Based Result Verification
  - ReportLab PDF Lab Reports with custom header/logo & dynamic page numbers
  - Billing, Discounting, Payment Recording & Receipt PDF Generation
  - Operational Dashboard with Real-Time Daily Statistics
  - Audit Logging of critical clinical & financial operations
  - Automated & Manual SQLite Backups with pre-restore safe backups & integrity checks

## Architecture & Structure
```text
smart_clinical_lab/
├── app/
│   ├── main.py                  # Entry point
│   ├── config/                  # AppData path resolution & defaults
│   ├── database/                # Connection, Engine, and Schema Migrations
│   ├── models/                  # SQLAlchemy ORM Models
│   ├── repositories/            # Clean data access layer
│   ├── services/                # Business logic, state machines & backup
│   ├── security/                # PBKDF2 Hashing & Session Context
│   ├── reports/                 # ReportLab PDF report/receipt generators
│   ├── ui/                      # Tkinter views, main window & dialogs
│   ├── utilities/               # Utility functions
│   └── validation/              # Input validators
├── tests/                       # Pytest unit tests & E2E integration workflow
├── assets/                      # Bundled app logos/icons
├── scripts/                     # Utility scripts
├── smart_lab.spec               # PyInstaller specification
├── build.py                     # Build executable script
└── requirements.txt
```

## First-Run Experience & AppData Storage
When launched for the first time:
1. Creates local data directory in `%LOCALAPPDATA%\SmartClinicalLab` (or `~/.local/share/SmartClinicalLab`).
2. Initializes SQLite database (`smart_lab.db`) and applies version migrations.
3. Prompts the Administrator to configure initial credentials (username, password, display name) and laboratory details (Lab Name, Address, Phone).
4. Seeds default system permissions and configurable roles (Administrator, Receptionist, Lab Technician, Verifier).

## Installation & Running from Source
```bash
# Clone repository and install dependencies
pip install -r requirements.txt

# Run application
python app/main.py
```

## Running Automated Tests
```bash
# Execute unit and end-to-end integration tests
PYTHONPATH=. pytest -v
```

## Building Executable (EXE)
```bash
python build.py
```
The generated standalone executable will be output to `dist/SmartClinicalLab`.

## Security & Data Integrity
- Passwords are encrypted using PBKDF2 SHA-256 with 100,000 iterations and random salts.
- Role-based permission enforcement for sensitive actions (verification, settings, user management, backup/restore).
- SQLite foreign key constraints enabled.
- Automatic safety backup created prior to any database restore operation with `PRAGMA integrity_check;` validation.
