"""
Lightweight database migration and initial setup script.
Ensures incremental migrations without wiping existing patient/lab data.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.database.connection import get_engine, Base
from app.models import (
    DatabaseVersion, Role, Permission, Setting, RoleEnum
)

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1

DEFAULT_PERMISSIONS = [
    ("dashboard_view", "View operational dashboard"),
    ("patient_view", "View patients"),
    ("patient_create", "Create new patient"),
    ("patient_edit", "Edit patient details"),
    ("order_create", "Create lab orders"),
    ("sample_collect", "Record sample collections"),
    ("result_entry", "Enter test results"),
    ("result_edit", "Edit test results"),
    ("result_verify", "Verify test results"),
    ("report_generate", "Generate PDF reports"),
    ("report_print", "Print reports and receipts"),
    ("test_manage", "Manage test catalog and parameters"),
    ("user_manage", "Manage application users"),
    ("settings_manage", "Manage laboratory settings"),
    ("backup_manage", "Create backups and restore database"),
    ("audit_view", "View audit logs"),
]

ROLE_PERMISSIONS_MAP = {
    RoleEnum.ADMINISTRATOR.value: [p[0] for p in DEFAULT_PERMISSIONS],
    RoleEnum.RECEPTIONIST.value: [
        "dashboard_view", "patient_view", "patient_create", "patient_edit",
        "order_create", "sample_collect", "report_generate", "report_print"
    ],
    RoleEnum.LAB_TECHNICIAN.value: [
        "dashboard_view", "patient_view", "order_create", "sample_collect",
        "result_entry", "result_edit", "report_generate", "report_print"
    ],
    RoleEnum.VERIFIER.value: [
        "dashboard_view", "patient_view", "result_entry", "result_edit",
        "result_verify", "report_generate", "report_print"
    ]
}

DEFAULT_SETTINGS = {
    "lab_name": "Smart Clinical Laboratory",
    "lab_address": "Medical Center Road, Kochi, Kerala, India",
    "lab_phone": "+91 484 2345678",
    "lab_email": "info@smartclinicallab.com",
    "lab_logo_path": "",
    "report_header_title": "DIAGNOSTIC LABORATORY REPORT",
    "report_footer_note": "This report is generated electronically and is valid without signature when verified.",
    "date_format": "%Y-%m-%d",
    "time_format": "%H:%M:%S",
    "patient_id_prefix": "PAT",
    "patient_id_next": "1001",
    "order_id_prefix": "ORD",
    "order_id_next": "10001",
    "receipt_id_prefix": "REC",
    "receipt_id_next": "50001",
}


def run_migrations(session: Session):
    engine = session.get_bind()
    Base.metadata.create_all(bind=engine)

    # Check current DB schema version
    db_ver = session.query(DatabaseVersion).order_by(DatabaseVersion.version.desc()).first()
    current_ver = db_ver.version if db_ver else 0

    if current_ver < 1:
        _apply_migration_v1(session)
        ver_record = DatabaseVersion(version=1)
        session.add(ver_record)
        session.commit()
        logger.info("Database migration v1 applied successfully.")

    seed_roles_and_permissions(session)
    seed_default_settings(session)


def _apply_migration_v1(session: Session):
    # Initial tables created via Base.metadata.create_all()
    pass


def seed_roles_and_permissions(session: Session):
    # Seed Permissions
    perm_objs = {}
    for code, desc in DEFAULT_PERMISSIONS:
        perm = session.query(Permission).filter_by(code=code).first()
        if not perm:
            perm = Permission(code=code, description=desc)
            session.add(perm)
            session.flush()
        perm_objs[code] = perm

    # Seed Roles
    for role_name in RoleEnum:
        role = session.query(Role).filter_by(name=role_name.value).first()
        if not role:
            role = Role(name=role_name.value, description=f"{role_name.value} Role")
            session.add(role)
            session.flush()

        # Assign default permissions to role
        allowed_codes = ROLE_PERMISSIONS_MAP.get(role_name.value, [])
        role.permissions = [perm_objs[code] for code in allowed_codes if code in perm_objs]

    session.commit()


def seed_default_settings(session: Session):
    for key, val in DEFAULT_SETTINGS.items():
        setting = session.query(Setting).filter_by(key=key).first()
        if not setting:
            setting = Setting(key=key, value=val, description=f"Setting {key}")
            session.add(setting)
    session.commit()
