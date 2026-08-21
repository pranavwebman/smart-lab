"""
Numbering service for auto-incrementing sequential identifiers with configurable prefixes.
"""

from sqlalchemy.orm import Session
from app.repositories import SettingRepository

class NumberingService:
    def __init__(self, session: Session):
        self.session = session
        self.setting_repo = SettingRepository(session)

    def _generate_next_id(self, prefix_key: str, default_prefix: str, next_key: str, default_start: int) -> str:
        prefix = self.setting_repo.get(prefix_key, default_prefix)
        next_val_str = self.setting_repo.get(next_key, str(default_start))
        try:
            next_val = int(next_val_str)
        except ValueError:
            next_val = default_start

        generated_id = f"{prefix}{next_val}"

        # Increment for next time
        self.setting_repo.set(next_key, str(next_val + 1))
        return generated_id

    def generate_patient_id(self) -> str:
        return self._generate_next_id("patient_id_prefix", "PAT", "patient_id_next", 1001)

    def generate_order_number(self) -> str:
        return self._generate_next_id("order_id_prefix", "ORD", "order_id_next", 10001)

    def generate_receipt_number(self) -> str:
        return self._generate_next_id("receipt_id_prefix", "REC", "receipt_id_next", 50001)
