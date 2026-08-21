"""
Unit tests for database models, security, services, reference range flags, status transitions, billing, and backup operations.
"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.database.connection import Base
from app.database.migrations import run_migrations
from app.models import (
    User, Patient, Test, TestParameter, ReferenceRange, Order,
    OrderStatusEnum, FlagEnum, PaymentStatusEnum
)
from app.security import hash_password, verify_password, SessionContext
from app.services import (
    AuthService, PatientService, TestService, OrderService, ResultService,
    VerificationService, BillingService, BackupService
)


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)

    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()

    run_migrations(session)
    yield session

    session.close()


def test_password_hashing():
    pwd = "SecretPassword123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_auth_service(db_session):
    auth_svc = AuthService(db_session)
    assert auth_svc.is_first_run() is True

    admin = auth_svc.create_initial_admin("admin", "admin123", "Admin User")
    assert admin.username == "admin"
    assert auth_svc.is_first_run() is False

    login_user = auth_svc.login("admin", "admin123")
    assert login_user is not None
    assert login_user.username == "admin"

    failed_user = auth_svc.login("admin", "wrongpass")
    assert failed_user is None


def test_patient_service(db_session):
    patient_svc = PatientService(db_session)
    p = patient_svc.register_patient(
        full_name="John Doe",
        gender="Male",
        age=30,
        phone="9876543210"
    )

    assert p.id is not None
    assert p.patient_id.startswith("PAT")
    assert p.full_name == "John Doe"

    search_results = patient_svc.search_patients("John")
    assert len(search_results) == 1
    assert search_results[0].patient_id == p.patient_id


def test_test_service_and_reference_ranges(db_session):
    test_svc = TestService(db_session)
    t = test_svc.create_test("GLU", "Glucose Fasting", price=150.0, sample_type="Blood")
    param = test_svc.add_parameter(t.id, "GLU_F", "Glucose Fasting", unit="mg/dL")
    test_svc.add_reference_range(param.id, gender="All", min_value=70.0, max_value=110.0)

    assert t.code == "GLU"
    assert len(t.parameters) == 1
    assert t.parameters[0].unit == "mg/dL"


def test_order_service_status_transitions(db_session):
    patient_svc = PatientService(db_session)
    p = patient_svc.register_patient("Alice Smith", "Female", age=25)

    test_svc = TestService(db_session)
    t = test_svc.create_test("CBC", "Complete Blood Count", 300.0)

    order_svc = OrderService(db_session)
    order = order_svc.create_order(p.id, [t.id])

    assert order.status == OrderStatusEnum.REGISTERED.value
    assert order.total_amount == 300.0

    # Valid transition
    order_svc.update_status(order.id, OrderStatusEnum.SAMPLE_COLLECTED.value)
    assert order.status == OrderStatusEnum.SAMPLE_COLLECTED.value

    # Invalid transition should raise ValueError
    with pytest.raises(ValueError):
        order_svc.update_status(order.id, OrderStatusEnum.COMPLETED.value)


def test_result_flag_calculation(db_session):
    patient_svc = PatientService(db_session)
    p = patient_svc.register_patient("Bob Brown", "Male", age=40)

    test_svc = TestService(db_session)
    t = test_svc.create_test("HB_TEST", "Hemoglobin Test", 100.0)
    param = test_svc.add_parameter(t.id, "HB", "Hemoglobin", unit="g/dL")
    test_svc.add_reference_range(param.id, gender="Male", min_value=13.0, max_value=17.0)

    order_svc = OrderService(db_session)
    order = order_svc.create_order(p.id, [t.id])

    res_svc = ResultService(db_session)

    # Test Low Flag
    flag_low = res_svc.calculate_flag("11.5", param, p.gender, p.age)
    assert flag_low == FlagEnum.LOW.value

    # Test Normal Flag
    flag_norm = res_svc.calculate_flag("14.5", param, p.gender, p.age)
    assert flag_norm == FlagEnum.NORMAL.value

    # Test High Flag
    flag_high = res_svc.calculate_flag("18.2", param, p.gender, p.age)
    assert flag_high == FlagEnum.HIGH.value


def test_billing_and_payments(db_session):
    patient_svc = PatientService(db_session)
    p = patient_svc.register_patient("Charlie Day", "Male", age=22)

    test_svc = TestService(db_session)
    t = test_svc.create_test("LFT", "Liver Function Test", 600.0)

    order_svc = OrderService(db_session)
    order = order_svc.create_order(p.id, [t.id], discount_amount=100.0)

    assert order.total_amount == 500.0

    billing = BillingService(db_session)
    p1 = billing.record_payment(order.id, 200.0, "Cash")
    assert order.paid_amount == 200.0
    assert order.payment_status == PaymentStatusEnum.PARTIAL.value

    p2 = billing.record_payment(order.id, 300.0, "UPI")
    assert order.paid_amount == 500.0
    assert order.payment_status == PaymentStatusEnum.PAID.value
