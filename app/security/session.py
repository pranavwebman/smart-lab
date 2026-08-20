"""
Session state for current logged-in user context.
"""

from typing import Optional, List

class SessionContext:
    _instance = None

    def __init__(self):
        self.current_user_id: Optional[int] = None
        self.username: Optional[str] = None
        self.display_name: Optional[str] = None
        self.roles: List[str] = []
        self.permissions: List[str] = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SessionContext()
        return cls._instance

    def set_user(self, user):
        if user:
            self.current_user_id = user.id
            self.username = user.username
            self.display_name = user.display_name
            self.roles = [r.name for r in user.roles] if user.roles else []
            self.permissions = []
            if user.roles:
                for role in user.roles:
                    for perm in role.permissions:
                        if perm.code not in self.permissions:
                            self.permissions.append(perm.code)
        else:
            self.clear()

    def clear(self):
        self.current_user_id = None
        self.username = None
        self.display_name = None
        self.roles = []
        self.permissions = []

    def has_permission(self, permission_code: str) -> bool:
        if not self.current_user_id:
            return False
        return permission_code in self.permissions

    def is_admin(self) -> bool:
        if not self.current_user_id:
            return False
        return "Administrator" in self.roles
