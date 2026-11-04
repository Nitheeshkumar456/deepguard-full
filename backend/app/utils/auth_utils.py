import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from ..config import settings

# Choose RS256 if RSA keys are provided, otherwise fall back to HS256
if settings.JWT_PRIVATE_KEY and settings.JWT_PUBLIC_KEY:
    ALGORITHM = "RS256"
else:
    ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a signed JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Update claim with expiration, unique jti, and scope type
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "jti": uuid.uuid4().hex, "type": "access"})
    if ALGORITHM == "RS256":
        return jwt.encode(to_encode, settings.JWT_PRIVATE_KEY, algorithm=ALGORITHM)
    else:
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a signed JWT refresh token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    
    # Update claim with expiration, unique jti, and scope type
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "jti": uuid.uuid4().hex, "type": "refresh"})
    if ALGORITHM == "RS256":
        return jwt.encode(to_encode, settings.JWT_PRIVATE_KEY, algorithm=ALGORITHM)
    else:
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token payload. Returns None if invalid or expired.
    """
    try:
        if ALGORITHM == "RS256":
            return jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=[ALGORITHM])
        else:
            return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
