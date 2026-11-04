from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Full name of the user")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password of at least 8 characters")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    version: int = 1
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OtpSend(BaseModel):
    email: EmailStr
    purpose: str = Field("register", description="Purpose of verification (e.g. register, reset)")

class OtpVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    purpose: str = Field("register", description="Purpose of verification (e.g. register, reset)")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str = Field(..., description="Secure reset token received during verification")
    new_password: str = Field(..., min_length=8, description="New password of at least 8 characters")

class MsgResponse(BaseModel):
    message: str
