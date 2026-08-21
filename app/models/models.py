"""
SQLAlchemy ORM Data Models for Smart Clinical Lab.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Index, Table
)
from sqlalchemy.orm import relationship
import enum
from app.database.connection import Base


class RoleEnum(str, enum.Enum):
    ADMINISTRATOR = "Administrator"
    RECEPTIONIST = "Receptionist"
    LAB_TECHNICIAN = "Laboratory Technician"
    VERIFIER = "Verifier"


class OrderStatusEnum(str, enum.Enum):
    DRAFT = "Draft"
    REGISTERED = "Registered"
    SAMPLE_COLLECTED = "Sample Collected"
    PROCESSING = "Processing"
    RESULTS_PENDING = "Results Pending"
    RESULTS_ENTERED = "Results Entered"
    VERIFIED = "Verified"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class ResultTypeEnum(str, enum.Enum):
    NUMERIC = "Numeric"
    TEXT = "Text"
    POS_NEG = "Positive/Negative"
    NORM_ABNORM = "Normal/Abnormal"
    SELECT_OPTION = "Select Option"


class FlagEnum(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    ABNORMAL = "ABNORMAL"
    NONE = "NONE"


class PaymentStatusEnum(str, enum.Enum):
    UNPAID = "Unpaid"
    PARTIAL = "Partial"
    PAID = "Paid"


# Many-to-Many table for User Roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# Many-to-Many table for Role Permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class DatabaseVersion(Base):
    __tablename__ = "database_version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, nullable=False, unique=True)
    applied_at = Column(DateTime, default=datetime.now)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    permissions = relationship("Permission", secondary=role_permissions, backref="roles")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)

    roles = relationship("Role", secondary=user_roles, backref="users")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False, index=True)
    date_of_birth = Column(String(20), nullable=True) # YYYY-MM-DD
    age = Column(Integer, nullable=True)
    age_unit = Column(String(10), default="Years") # Years, Months, Days
    gender = Column(String(20), nullable=False) # Male, Female, Other
    phone = Column(String(30), nullable=True, index=True)
    address = Column(Text, nullable=True)
    email = Column(String(100), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    registration_date = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True, nullable=False)

    orders = relationship("Order", back_populates="patient", cascade="all, delete-orphan")


class TestCategory(Base):
    __tablename__ = "test_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0)

    tests = relationship("Test", back_populates="category")


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("test_categories.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    sample_type = Column(String(100), nullable=True) # Blood, Urine, etc.
    preparation_instructions = Column(Text, nullable=True)
    turnaround_time = Column(String(50), nullable=True) # e.g. "2 hours"
    price = Column(Float, default=0.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    category = relationship("TestCategory", back_populates="tests")
    parameters = relationship("TestParameter", back_populates="test", cascade="all, delete-orphan", order_by="TestParameter.display_order")


class TestParameter(Base):
    __tablename__ = "test_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False)
    result_type = Column(String(30), default=ResultTypeEnum.NUMERIC.value)
    unit = Column(String(50), nullable=True) # mg/dL, g/dL, %
    decimal_precision = Column(Integer, default=2)
    options = Column(Text, nullable=True) # JSON list or comma separated for select options
    display_order = Column(Integer, default=0)
    is_required = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    test = relationship("Test", back_populates="parameters")
    reference_ranges = relationship("ReferenceRange", back_populates="parameter", cascade="all, delete-orphan")


class ReferenceRange(Base):
    __tablename__ = "reference_ranges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_id = Column(Integer, ForeignKey("test_parameters.id", ondelete="CASCADE"), nullable=False)
    gender = Column(String(20), default="All") # Male, Female, All
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    text_range = Column(String(255), nullable=True) # e.g. "Negative", "70 - 110"
    notes = Column(Text, nullable=True)

    parameter = relationship("TestParameter", back_populates="reference_ranges")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
    order_date = Column(DateTime, default=datetime.now, nullable=False, index=True)
    status = Column(String(30), default=OrderStatusEnum.REGISTERED.value, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    # Billing fields snapshot
    total_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    payment_status = Column(String(20), default=PaymentStatusEnum.UNPAID.value)

    patient = relationship("Patient", back_populates="orders")
    created_by = relationship("User")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    samples = relationship("SampleCollection", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="RESTRICT"), nullable=False)
    test_name_snapshot = Column(String(150), nullable=False)
    price_snapshot = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    test = relationship("Test")
    results = relationship("TestResult", back_populates="order_item", cascade="all, delete-orphan")


class SampleCollection(Base):
    __tablename__ = "sample_collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    sample_type = Column(String(100), nullable=False)
    sample_identifier = Column(String(100), nullable=True) # Barcode / Sample ID
    collected_at = Column(DateTime, nullable=True)
    collected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_collected = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    order = relationship("Order", back_populates="samples")
    collected_by = relationship("User")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    parameter_id = Column(Integer, ForeignKey("test_parameters.id", ondelete="RESTRICT"), nullable=False)
    parameter_name_snapshot = Column(String(150), nullable=False)
    unit_snapshot = Column(String(50), nullable=True)
    result_value = Column(Text, nullable=True)
    flag = Column(String(20), default=FlagEnum.NONE.value)
    reference_range_snapshot = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    entered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entered_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    order_item = relationship("OrderItem", back_populates="results")
    parameter = relationship("TestParameter")
    entered_by = relationship("User", foreign_keys=[entered_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False) # Cash, Card, UPI, Other
    payment_date = Column(DateTime, default=datetime.now)
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    order = relationship("Order", back_populates="payments")
    recorded_by = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    username = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    entity = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
