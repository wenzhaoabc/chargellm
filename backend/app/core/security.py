from __future__ import annotations

from hashlib import pbkdf2_hmac
import secrets


PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_bytes.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations_raw, salt_hex, digest_hex = stored_hash.split("$", 3)
        iterations = int(iterations_raw)
        salt_bytes = bytes.fromhex(salt_hex)
    except (TypeError, ValueError):
        return False
    if scheme != "pbkdf2_sha256":
        return False
    candidate = pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iterations).hex()
    return secrets.compare_digest(candidate, digest_hex)


def generate_access_token(prefix: str = "token") -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def generate_invite_code(prefix: str = "DEMO") -> str:
    raw = secrets.token_hex(4).upper()
    return f"{prefix}-{raw[:4]}-{raw[4:]}"


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"
