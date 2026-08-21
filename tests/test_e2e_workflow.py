"""
End-to-End Workflow Integration Test for Smart Clinical Lab.
Covers: Admin Creation -> Login -> Patient Registration -> Test Catalog Config
-> Reference Range Config -> Order Creation -> Sample Collection -> Result Entry
-> Result Verification -> Billing & Payment -> Report PDF Generation -> Audit Log -> Backup & Restore.
"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.database.connection import Base
from app.database.migrations import run_migrations
from app.models import OrderStatusEnum, FlagEnum, PaymentStatusEnum
from app.security import SessionContext
from app.services import (
    AuthService, PatientService, TestService, OrderService,
    ResultService, VerificationService, BillingService, BackupService
)
from app.reports import ReportService
from app.repositories import AuditRepository


def test_complete_end_to_end_lab_workflow(tmp_path):
    # 1. Setup Database
    db_file = tmp_path / "e2e_smart_lab.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)

    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    run_migrations(session)

    # 2. Admin Creation & Login
    auth_svc = AuthService(session)
    admin = auth_svc.create_initial_admin("lab_admin", "password123", "Chief Admin")
    assert admin is not None

    logged_user = auth_svc.login("lab_admin", "password123")
    assert logged_user is not None
    assert SessionContext.get_instance().username == "lab_admin"

    # 3. Patient Registration & Search
    patient_svc = PatientService(session)
    patient = patient_svc.register_patient(
        full_name="Kerala Patient",
        gender="Male",
        age=45,
        phone="+91 9895012345",
        address="Kochi, Kerala"
    )
    assert patient.patient_id.startswith("PAT")

    search_res = patient_svc.search_patients("9895012345")
    assert len(search_res) == 1
    assert search_res[0].id == patient.id

    # 4. Test Catalog Configuration & Reference Ranges
    test_svc = TestService(session)
    cat = test_svc.create_category("Biochemistry")
    test = test_svc.create_test("LIPID", "Lipid Profile", price=800.0, category_id=cat.id, sample_type="Blood")

    p_chol = test_svc.add_parameter(test.id, "CHOL", "Cholesterol Total", unit="mg/dL")
    test_svc.add_reference_range(p_chol.id, gender="Male", min_value=120.0, max_value=200.0)

    p_trig = test_svc.add_parameter(test.id, "TRIG", "Triglycerides", unit="mg/dL")
    test_svc.add_reference_range(p_trig.id, gender="Male", min_value=50.0, max_value=150.0)

    # 5. Order Creation
    order_svc = OrderService(session)
    order = order_svc.create_order(patient.id, [test.id], discount_amount=50.0)
    assert order.order_number.startswith("ORD")
    assert order.total_amount == 750.0
    assert order.status == OrderStatusEnum.REGISTERED.value

    # 6. Sample Collection
    assert len(order.samples) == 1
    sample = order.samples[0]
    order_svc.record_sample_collection(order.id, sample.id, sample_identifier="SMPL999")
    assert order.status == OrderStatusEnum.SAMPLE_COLLECTED.value

    # 7. Result Entry
    res_svc = ResultService(session)
    res_chol = order.items[0].results[0]
    res_trig = order.items[0].results[1]

    results_map = {
        res_chol.id: "240.0",  # HIGH
        res_trig.id: "130.0"   # NORMAL
    }
    res_svc.save_results(order.id, results_map)
    assert res_chol.flag == FlagEnum.HIGH.value
    assert res_trig.flag == FlagEnum.NORMAL.value
    assert order.status == OrderStatusEnum.RESULTS_ENTERED.value

    # 8. Result Verification
    verify_svc = VerificationService(session)
    verify_svc.verify_order_results(order.id)
    assert order.status == OrderStatusEnum.VERIFIED.value
    assert res_chol.is_verified is True

    # 9. Billing & Payment
    billing = BillingService(session)
    payment = billing.record_payment(order.id, 750.0, "UPI")
    assert order.payment_status == PaymentStatusEnum.PAID.value
    assert payment.receipt_number.startswith("REC")

    # 10. Report & Receipt PDF Generation
    rpt_svc = ReportService(session)
    report_pdf = rpt_svc.generate_patient_report(order)
    receipt_pdf = rpt_svc.generate_receipt_pdf(payment)

    assert Path(report_pdf).exists()
    assert Path(receipt_pdf).exists()

    # 11. Audit Logging Verification
    audit_repo = AuditRepository(session)
    logs = audit_repo.get_logs()
    assert len(logs) > 5

    # 12. Backup & Restore Validation
    backup_svc = BackupService(session)
    backup_file = backup_svc.create_backup()
    assert Path(backup_file).exists()

    restore_ok = backup_svc.restore_backup(backup_file)
    assert restore_ok is True

    session.close()
