import re
import secrets
from passlib.context import CryptContext

# Set up cryptography context using bcrypt hashing scheme
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the stored bcrypt hash.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Generate bcrypt hash for a plain password.
    """
    return pwd_context.hash(password)

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate that the password satisfies minimum security guidelines:
    - Min length: 8 characters
    - Must include at least 1 digit, 1 uppercase letter, 1 lowercase letter, and 1 special symbol.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#\$%\^&\*\(\)_\+\-=\[\]\{\}\|;':\",\./<>\?]", password):
        return False, "Password must contain at least one special character."
    
    return True, "Password is strong."

def generate_otp_code() -> str:
    """
    Generates a secure 6-digit numerical verification code.
    """
    return "".join(secrets.choice("0123456789") for _ in range(6))

def generate_secure_token() -> str:
    """
    Generates a cryptographically secure URL-safe string token.
    """
    return secrets.token_urlsafe(32)
