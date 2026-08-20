"""
Security utilities including PBKDF2 password hashing and verification.
"""

import hashlib
import os
import secrets

def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2 with SHA256 and a random salt.
    Format stored: pbkdf2_sha256$iterations$salt$hash
    """
    if not password:
        raise ValueError("Password cannot be empty")

    salt = secrets.token_hex(16)
    iterations = 100000
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plain password against a stored PBKDF2 hash.
    """
    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split('$')
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False

        iterations = int(parts[1])
        salt = parts[2]
        expected_key = parts[3]

        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return secrets.compare_digest(key.hex(), expected_key)
    except Exception:
        return False
