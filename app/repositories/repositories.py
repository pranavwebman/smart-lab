"""
Repository layer providing clean CRUD operations for database entities.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from app.models import (
    User, Role, Permission, Patient, TestCategory, Test, TestParameter, ReferenceRange,
    Order, OrderItem, SampleCollection, TestResult, Payment, AuditLog, Setting
)

class BaseRepository:
    def __init__(self, session: Session):
        self.session = session


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.session.query(User).filter(User.username == username).first()

    def get_all(self) -> List[User]:
        return self.session.query(User).order_by(User.username).all()

    def count_users(self) -> int:
        return self.session.query(User).count()

    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user


class PatientRepository(BaseRepository):
    def get_by_id(self, id_: int) -> Optional[Patient]:
        return self.session.query(Patient).filter(Patient.id == id_).first()

    def get_by_patient_id(self, patient_id: str) -> Optional[Patient]:
        return self.session.query(Patient).filter(Patient.patient_id == patient_id).first()

    def search(self, query: str, active_only: bool = True) -> List[Patient]:
        q = self.session.query(Patient)
        if active_only:
            q = q.filter(Patient.is_active == True)

        if query:
            pattern = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    Patient.patient_id.ilike(pattern),
                    Patient.full_name.ilike(pattern),
                    Patient.phone.ilike(pattern)
                )
            )
        return q.order_by(desc(Patient.registration_date)).all()

    def save(self, patient: Patient) -> Patient:
        self.session.add(patient)
        self.session.commit()
        self.session.refresh(patient)
        return patient


class TestRepository(BaseRepository):
    def get_categories(self) -> List[TestCategory]:
        return self.session.query(TestCategory).order_by(TestCategory.display_order, TestCategory.name).all()

    def get_category_by_id(self, cat_id: int) -> Optional[TestCategory]:
        return self.session.query(TestCategory).filter(TestCategory.id == cat_id).first()

    def save_category(self, category: TestCategory) -> TestCategory:
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category

    def get_all_tests(self, active_only: bool = False) -> List[Test]:
        q = self.session.query(Test)
        if active_only:
            q = q.filter(Test.is_active == True)
        return q.order_by(Test.name).all()

    def get_test_by_id(self, test_id: int) -> Optional[Test]:
        return self.session.query(Test).filter(Test.id == test_id).first()

    def get_test_by_code(self, code: str) -> Optional[Test]:
        return self.session.query(Test).filter(Test.code == code).first()

    def save_test(self, test: Test) -> Test:
        self.session.add(test)
        self.session.commit()
        self.session.refresh(test)
        return test


class OrderRepository(BaseRepository):
    def get_by_id(self, order_id: int) -> Optional[Order]:
        return self.session.query(Order).filter(Order.id == order_id).first()

    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        return self.session.query(Order).filter(Order.order_number == order_number).first()

    def search_orders(self, query: str = None, status: str = None, patient_id: int = None, limit: int = 100) -> List[Order]:
        q = self.session.query(Order)
        if patient_id:
            q = q.filter(Order.patient_id == patient_id)
        if status:
            q = q.filter(Order.status == status)
        if query:
            pattern = f"%{query.strip()}%"
            q = q.join(Order.patient).filter(
                or_(
                    Order.order_number.ilike(pattern),
                    Patient.patient_id.ilike(pattern),
                    Patient.full_name.ilike(pattern)
                )
            )
        return q.order_by(desc(Order.order_date)).limit(limit).all()

    def save(self, order: Order) -> Order:
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order


class AuditRepository(BaseRepository):
    def log_action(self, username: str, action: str, entity: str, entity_id: str = None, details: str = None):
        log = AuditLog(
            username=username,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details
        )
        self.session.add(log)
        self.session.commit()

    def get_logs(self, limit: int = 200, action_filter: str = None) -> List[AuditLog]:
        q = self.session.query(AuditLog)
        if action_filter:
            q = q.filter(AuditLog.action.ilike(f"%{action_filter}%"))
        return q.order_by(desc(AuditLog.timestamp)).limit(limit).all()


class SettingRepository(BaseRepository):
    def get(self, key: str, default: str = "") -> str:
        s = self.session.query(Setting).filter(Setting.key == key).first()
        return s.value if s and s.value is not None else default

    def set(self, key: str, value: str, description: str = None):
        s = self.session.query(Setting).filter(Setting.key == key).first()
        if not s:
            s = Setting(key=key, value=value, description=description)
            self.session.add(s)
        else:
            s.value = value
            if description:
                s.description = description
        self.session.commit()

    def get_all_as_dict(self) -> dict:
        settings = self.session.query(Setting).all()
        return {s.key: s.value for s in settings}
