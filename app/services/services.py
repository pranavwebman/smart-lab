"""
Business logic services for authentication, patient management, test catalog,
orders, results, verification, billing, backups, audit logging, and settings.
"""

from datetime import datetime
import shutil
import sqlite3
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.models import (
    User, Role, Permission, Patient, TestCategory, Test, TestParameter, ReferenceRange,
    Order, OrderItem, SampleCollection, TestResult, Payment, AuditLog, Setting,
    OrderStatusEnum, ResultTypeEnum, FlagEnum, PaymentStatusEnum, RoleEnum
)
from app.repositories import (
    UserRepository, PatientRepository, TestRepository, OrderRepository,
    AuditRepository, SettingRepository
)
from app.security import hash_password, verify_password, SessionContext
from app.services.numbering_service import NumberingService
from app.config import get_db_path, get_backups_dir


class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditRepository(session)

    def is_first_run(self) -> bool:
        return self.user_repo.count_users() == 0

    def create_initial_admin(self, username: str, password: str, display_name: str) -> User:
        if not username or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        admin_role = self.session.query(Role).filter_by(name=RoleEnum.ADMINISTRATOR.value).first()
        if not admin_role:
            raise RuntimeError("Administrator role not found in database.")

        user = User(
            username=username.strip(),
            password_hash=hash_password(password),
            display_name=display_name.strip() or username.strip(),
            is_active=True,
            created_at=datetime.now()
        )
        user.roles.append(admin_role)
        self.user_repo.save(user)
        self.audit_repo.log_action("SYSTEM", "INITIAL_ADMIN_CREATED", "User", user.id, f"Admin {username} created")
        return user

    def login(self, username: str, password: str) -> Optional[User]:
        user = self.user_repo.get_by_username(username.strip())
        if not user or not user.is_active:
            self.audit_repo.log_action("GUEST", "LOGIN_FAILED", "User", None, f"Failed login for {username}")
            return None

        if verify_password(password, user.password_hash):
            user.last_login = datetime.now()
            self.session.commit()
            SessionContext.get_instance().set_user(user)
            self.audit_repo.log_action(user.username, "LOGIN_SUCCESS", "User", user.id)
            return user

        self.audit_repo.log_action("GUEST", "LOGIN_FAILED", "User", None, f"Invalid password for {username}")
        return None

    def logout(self):
        ctx = SessionContext.get_instance()
        if ctx.username:
            self.audit_repo.log_action(ctx.username, "LOGOUT", "User", ctx.current_user_id)
            ctx.clear()

    def create_user(self, username: str, password: str, display_name: str, role_names: List[str]) -> User:
        existing = self.user_repo.get_by_username(username.strip())
        if existing:
            raise ValueError(f"Username '{username}' is already taken.")

        roles = self.session.query(Role).filter(Role.name.in_(role_names)).all()
        user = User(
            username=username.strip(),
            password_hash=hash_password(password),
            display_name=display_name.strip(),
            is_active=True,
            created_at=datetime.now()
        )
        user.roles = roles
        self.user_repo.save(user)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "USER_CREATED", "User", user.id, f"Created user {username}")
        return user

    def update_user(self, user_id: int, display_name: str, is_active: bool, role_names: List[str], password: str = None) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found.")

        user.display_name = display_name.strip()
        user.is_active = is_active
        if password and len(password.strip()) >= 6:
            user.password_hash = hash_password(password)

        roles = self.session.query(Role).filter(Role.name.in_(role_names)).all()
        user.roles = roles
        self.user_repo.save(user)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "USER_UPDATED", "User", user.id, f"Updated user {user.username}")
        return user


class PatientService:
    def __init__(self, session: Session):
        self.session = session
        self.patient_repo = PatientRepository(session)
        self.numbering_service = NumberingService(session)
        self.audit_repo = AuditRepository(session)

    def register_patient(
        self, full_name: str, gender: str, date_of_birth: str = None, age: int = None,
        age_unit: str = "Years", phone: str = None, address: str = None, email: str = None,
        emergency_contact: str = None, notes: str = None
    ) -> Patient:
        if not full_name or not full_name.strip():
            raise ValueError("Patient full name is required.")
        if not gender:
            raise ValueError("Gender is required.")

        patient_id = self.numbering_service.generate_patient_id()

        patient = Patient(
            patient_id=patient_id,
            full_name=full_name.strip(),
            gender=gender,
            date_of_birth=date_of_birth,
            age=age,
            age_unit=age_unit,
            phone=phone.strip() if phone else None,
            address=address.strip() if address else None,
            email=email.strip() if email else None,
            emergency_contact=emergency_contact.strip() if emergency_contact else None,
            notes=notes.strip() if notes else None,
            registration_date=datetime.now(),
            is_active=True
        )
        self.patient_repo.save(patient)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "PATIENT_CREATED", "Patient", patient.id, f"Registered patient {patient.patient_id} - {patient.full_name}")
        return patient

    def update_patient(self, id_: int, **kwargs) -> Patient:
        patient = self.patient_repo.get_by_id(id_)
        if not patient:
            raise ValueError("Patient record not found.")

        for key, val in kwargs.items():
            if hasattr(patient, key) and key not in ["id", "patient_id", "registration_date"]:
                setattr(patient, key, val)

        self.patient_repo.save(patient)
        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "PATIENT_UPDATED", "Patient", patient.id, f"Updated patient {patient.patient_id}")
        return patient

    def search_patients(self, query: str = "", active_only: bool = True) -> List[Patient]:
        return self.patient_repo.search(query, active_only)


class TestService:
    def __init__(self, session: Session):
        self.session = session
        self.test_repo = TestRepository(session)
        self.audit_repo = AuditRepository(session)

    def create_category(self, name: str, description: str = None, display_order: int = 0) -> TestCategory:
        existing = self.session.query(TestCategory).filter_by(name=name.strip()).first()
        if existing:
            return existing
        cat = TestCategory(name=name.strip(), description=description, display_order=display_order)
        return self.test_repo.save_category(cat)

    def create_test(
        self, code: str, name: str, price: float, category_id: int = None, sample_type: str = "Blood",
        description: str = None, preparation_instructions: str = None, turnaround_time: str = None, notes: str = None
    ) -> Test:
        if not code or not name:
            raise ValueError("Test code and name are required.")
        if self.test_repo.get_test_by_code(code.strip()):
            raise ValueError(f"Test code '{code}' already exists.")

        test = Test(
            code=code.strip().upper(),
            name=name.strip(),
            price=price,
            category_id=category_id,
            sample_type=sample_type,
            description=description,
            preparation_instructions=preparation_instructions,
            turnaround_time=turnaround_time,
            notes=notes,
            is_active=True
        )
        self.test_repo.save_test(test)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "TEST_CREATED", "Test", test.id, f"Created test {test.code}")
        return test

    def add_parameter(
        self, test_id: int, code: str, name: str, result_type: str = ResultTypeEnum.NUMERIC.value,
        unit: str = None, decimal_precision: int = 2, options: str = None, is_required: bool = True, display_order: int = 0
    ) -> TestParameter:
        test = self.test_repo.get_test_by_id(test_id)
        if not test:
            raise ValueError("Test not found.")

        param = TestParameter(
            test_id=test_id,
            code=code.strip(),
            name=name.strip(),
            result_type=result_type,
            unit=unit,
            decimal_precision=decimal_precision,
            options=options,
            is_required=is_required,
            display_order=display_order,
            is_active=True
        )
        self.session.add(param)
        self.session.commit()
        self.session.refresh(param)
        return param

    def add_reference_range(
        self, parameter_id: int, gender: str = "All", min_age: int = None, max_age: int = None,
        min_value: float = None, max_value: float = None, text_range: str = None, notes: str = None
    ) -> ReferenceRange:
        ref = ReferenceRange(
            parameter_id=parameter_id,
            gender=gender,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            text_range=text_range,
            notes=notes
        )
        self.session.add(ref)
        self.session.commit()
        self.session.refresh(ref)
        return ref


class OrderService:
    def __init__(self, session: Session):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.numbering_service = NumberingService(session)
        self.audit_repo = AuditRepository(session)

    VALID_TRANSITIONS = {
        OrderStatusEnum.DRAFT.value: [OrderStatusEnum.REGISTERED.value, OrderStatusEnum.CANCELLED.value],
        OrderStatusEnum.REGISTERED.value: [OrderStatusEnum.SAMPLE_COLLECTED.value, OrderStatusEnum.CANCELLED.value],
        OrderStatusEnum.SAMPLE_COLLECTED.value: [OrderStatusEnum.PROCESSING.value, OrderStatusEnum.CANCELLED.value],
        OrderStatusEnum.PROCESSING.value: [OrderStatusEnum.RESULTS_PENDING.value, OrderStatusEnum.CANCELLED.value],
        OrderStatusEnum.RESULTS_PENDING.value: [OrderStatusEnum.RESULTS_ENTERED.value, OrderStatusEnum.CANCELLED.value],
        OrderStatusEnum.RESULTS_ENTERED.value: [OrderStatusEnum.VERIFIED.value, OrderStatusEnum.RESULTS_PENDING.value, OrderStatusEnum.CANCELLED.value],
        OrderStatusEnum.VERIFIED.value: [OrderStatusEnum.COMPLETED.value],
        OrderStatusEnum.COMPLETED.value: [],
        OrderStatusEnum.CANCELLED.value: []
    }

    def create_order(self, patient_id: int, test_ids: List[int], notes: str = None, discount_amount: float = 0.0) -> Order:
        if not test_ids:
            raise ValueError("An order must contain at least one test.")

        patient = self.session.query(Patient).filter_by(id=patient_id).first()
        if not patient:
            raise ValueError("Patient not found.")

        order_number = self.numbering_service.generate_order_number()
        curr_user_id = SessionContext.get_instance().current_user_id

        order = Order(
            order_number=order_number,
            patient_id=patient_id,
            order_date=datetime.now(),
            status=OrderStatusEnum.REGISTERED.value,
            created_by_id=curr_user_id,
            notes=notes,
            discount_amount=discount_amount
        )

        total = 0.0
        samples_needed = set()

        for tid in test_ids:
            test = self.session.query(Test).filter_by(id=tid).first()
            if not test or not test.is_active:
                continue

            item = OrderItem(
                test_id=test.id,
                test_name_snapshot=test.name,
                price_snapshot=test.price
            )
            order.items.append(item)
            total += test.price

            if test.sample_type:
                samples_needed.add(test.sample_type)

            for param in test.parameters:
                if param.is_active:
                    ref_text = ""
                    matching_ref = self._find_matching_ref_range(param, patient.gender, patient.age)
                    if matching_ref:
                        if matching_ref.text_range:
                            ref_text = matching_ref.text_range
                        elif matching_ref.min_value is not None and matching_ref.max_value is not None:
                            ref_text = f"{matching_ref.min_value} - {matching_ref.max_value}"

                    res = TestResult(
                        parameter_id=param.id,
                        parameter_name_snapshot=param.name,
                        unit_snapshot=param.unit,
                        reference_range_snapshot=ref_text,
                        flag=FlagEnum.NONE.value
                    )
                    item.results.append(res)

        order.total_amount = max(0.0, total - discount_amount)
        order.payment_status = PaymentStatusEnum.UNPAID.value

        for stype in samples_needed:
            sc = SampleCollection(sample_type=stype, is_collected=False)
            order.samples.append(sc)

        self.order_repo.save(order)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "ORDER_CREATED", "Order", order.id, f"Created order {order.order_number}")
        return order

    def update_status(self, order_id: int, new_status: str) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found.")

        allowed = self.VALID_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid order status transition from {order.status} to {new_status}.")

        old_status = order.status
        order.status = new_status
        self.order_repo.save(order)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "ORDER_STATUS_CHANGED", "Order", order.id, f"Order status changed from {old_status} to {new_status}")
        return order

    def record_sample_collection(self, order_id: int, sample_id: int, sample_identifier: str = None, notes: str = None):
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found.")

        curr_user_id = SessionContext.get_instance().current_user_id
        for s in order.samples:
            if s.id == sample_id:
                s.is_collected = True
                s.collected_at = datetime.now()
                s.collected_by_id = curr_user_id
                s.sample_identifier = sample_identifier
                s.notes = notes

        if all(s.is_collected for s in order.samples) and order.status == OrderStatusEnum.REGISTERED.value:
            order.status = OrderStatusEnum.SAMPLE_COLLECTED.value

        self.order_repo.save(order)

    def _find_matching_ref_range(self, param: TestParameter, gender: str, age: Optional[int]) -> Optional[ReferenceRange]:
        for r in param.reference_ranges:
            if r.gender not in ["All", gender]:
                continue
            if age is not None:
                if r.min_age is not None and age < r.min_age:
                    continue
                if r.max_age is not None and age > r.max_age:
                    continue
            return r
        return None


class ResultService:
    def __init__(self, session: Session):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.audit_repo = AuditRepository(session)

    def calculate_flag(self, result_val: str, param: TestParameter, patient_gender: str, patient_age: Optional[int]) -> str:
        if not result_val or param.result_type != ResultTypeEnum.NUMERIC.value:
            return FlagEnum.NONE.value

        try:
            val = float(result_val)
        except ValueError:
            return FlagEnum.NONE.value

        for ref in param.reference_ranges:
            if ref.gender not in ["All", patient_gender]:
                continue
            if patient_age is not None:
                if ref.min_age is not None and patient_age < ref.min_age:
                    continue
                if ref.max_age is not None and patient_age > ref.max_age:
                    continue

            if ref.min_value is not None and val < ref.min_value:
                return FlagEnum.LOW.value
            if ref.max_value is not None and val > ref.max_value:
                return FlagEnum.HIGH.value
            if ref.min_value is not None or ref.max_value is not None:
                return FlagEnum.NORMAL.value

        return FlagEnum.NONE.value

    def save_results(self, order_id: int, results_map: Dict[int, str]) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found.")

        curr_user_id = SessionContext.get_instance().current_user_id

        all_entered = True
        for item in order.items:
            for res in item.results:
                if res.id in results_map:
                    val = results_map[res.id]
                    param = res.parameter

                    if param.is_required and (val is None or str(val).strip() == ""):
                        raise ValueError(f"Parameter '{param.name}' is required.")

                    if param.result_type == ResultTypeEnum.NUMERIC.value and val and str(val).strip() != "":
                        try:
                            float(val)
                        except ValueError:
                            raise ValueError(f"Value for '{param.name}' must be numeric.")

                    if res.is_verified and res.result_value != val:
                        res.is_verified = False
                        res.verified_by_id = None
                        res.verified_at = None

                    res.result_value = str(val).strip()
                    res.entered_at = datetime.now()
                    res.entered_by_id = curr_user_id
                    res.flag = self.calculate_flag(res.result_value, param, order.patient.gender, order.patient.age)

                if not res.result_value or str(res.result_value).strip() == "":
                    all_entered = False

        if all_entered and order.status in [OrderStatusEnum.REGISTERED.value, OrderStatusEnum.SAMPLE_COLLECTED.value, OrderStatusEnum.PROCESSING.value, OrderStatusEnum.RESULTS_PENDING.value]:
            order.status = OrderStatusEnum.RESULTS_ENTERED.value

        self.order_repo.save(order)
        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "RESULTS_ENTERED", "Order", order.id, f"Entered results for order {order.order_number}")
        return order


class VerificationService:
    def __init__(self, session: Session):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.audit_repo = AuditRepository(session)

    def verify_order_results(self, order_id: int) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found.")

        ctx = SessionContext.get_instance()
        if not ctx.current_user_id:
            raise RuntimeError("Authentication required to verify results.")

        if not ctx.has_permission("result_verify") and not ctx.is_admin():
            raise PermissionError("User does not have permission to verify results.")

        for item in order.items:
            for res in item.results:
                res.is_verified = True
                res.verified_by_id = ctx.current_user_id
                res.verified_at = datetime.now()

        order.status = OrderStatusEnum.VERIFIED.value
        self.order_repo.save(order)

        self.audit_repo.log_action(ctx.username or "SYSTEM", "RESULTS_VERIFIED", "Order", order.id, f"Verified results for order {order.order_number}")
        return order


class BillingService:
    def __init__(self, session: Session):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.numbering_service = NumberingService(session)
        self.audit_repo = AuditRepository(session)

    def record_payment(self, order_id: int, amount: float, payment_method: str = "Cash", notes: str = None) -> Payment:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found.")

        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        receipt_num = self.numbering_service.generate_receipt_number()
        curr_user_id = SessionContext.get_instance().current_user_id

        payment = Payment(
            receipt_number=receipt_num,
            order_id=order.id,
            amount=amount,
            payment_method=payment_method,
            payment_date=datetime.now(),
            recorded_by_id=curr_user_id,
            notes=notes
        )
        self.session.add(payment)

        order.paid_amount += amount
        if order.paid_amount >= order.total_amount:
            order.payment_status = PaymentStatusEnum.PAID.value
        else:
            order.payment_status = PaymentStatusEnum.PARTIAL.value

        self.order_repo.save(order)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "PAYMENT_RECORDED", "Payment", payment.id, f"Recorded payment {receipt_num} of {amount} for order {order.order_number}")
        return payment


class BackupService:
    def __init__(self, session: Session):
        self.session = session
        self.audit_repo = AuditRepository(session)

    def create_backup(self) -> str:
        db_path = get_db_path()
        if not db_path.exists():
            raise FileNotFoundError("Database file not found.")

        backups_dir = get_backups_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"smart_lab_backup_{timestamp}.db"
        target_path = backups_dir / backup_filename

        shutil.copy2(db_path, target_path)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "BACKUP_CREATED", "Database", None, f"Created backup {backup_filename}")
        return str(target_path)

    def restore_backup(self, backup_filepath: str) -> bool:
        backup_path = get_db_path().__class__(backup_filepath)
        if not backup_path.exists():
            raise FileNotFoundError("Selected backup file does not exist.")

        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()

        if not res or res[0] != "ok":
            raise ValueError("Backup file integrity check failed. Restore aborted.")

        self.create_backup()

        db_path = get_db_path()
        engine = self.session.get_bind()
        self.session.close()
        engine.dispose()

        shutil.copy2(backup_path, db_path)

        performed_by = SessionContext.get_instance().username or "SYSTEM"
        self.audit_repo.log_action(performed_by, "DATABASE_RESTORED", "Database", None, f"Restored database from {backup_path.name}")
        return True
