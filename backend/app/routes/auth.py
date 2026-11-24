from datetime import datetime, timedelta, timezone
from ..limiter import limiter
from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..dependencies import get_db, get_current_user
from ..models.auth import User, Session as UserSession, PasswordResetToken, OTP
from ..config import settings
from ..services.email_service import send_otp_email
from ..services.audit_service import log_security_event, extract_device_info

logger = logging.getLogger(__name__)
from ..schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserResponse,
    OtpSend,
    OtpVerify,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MsgResponse,
)
from ..utils.security import (
    get_password_hash,
    verify_password,
    validate_password_strength,
    generate_otp_code,
    generate_secure_token,
)
from ..utils.auth_utils import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class RefreshRequest(BaseModel):
    refresh_token: str

class VerifyOtpResponse(BaseModel):
    verified: bool
    reset_token: Optional[str] = None
    message: str

@router.post("/register", response_model=MsgResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(user_data: UserRegister, request: Request, db: Session = Depends(get_db)):
    # Validate password complexity strength
    is_strong, strength_msg = validate_password_strength(user_data.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strength_msg
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )
    
    # Hash password and create unverified User record
    hashed = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed,
        is_verified=False,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    
    # Generate 6-digit OTP verification code
    otp_code = generate_otp_code()
    expiration = datetime.utcnow() + timedelta(minutes=10)
    otp_record = OTP(
        email=user_data.email,
        code=otp_code,
        purpose="register",
        expires_at=expiration,
        verified=False
    )
    db.add(otp_record)
    db.commit()
    
    # Send OTP email — real SMTP when configured, console fallback otherwise
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        delivered = send_otp_email(
            recipient_email=user_data.email,
            otp_code=otp_code,
            purpose="register",
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_password=settings.SMTP_PASSWORD,
            sender_name=settings.MAIL_FROM_NAME,
        )
        if not delivered:
            logger.error(f"OTP email delivery failed for {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to send OTP email. Please verify email settings or try again later."
            )
    else:
        # SMTP not configured — console stub (development mode)
        print(f"\n[OTP MAIL STUB] To: {user_data.email} | Code: {otp_code} | Purpose: register\n")
        logger.warning("SMTP not configured. Set SMTP_USER and SMTP_PASSWORD in backend/.env for real email delivery.")

    return {"message": "Registration successful. Please verify your email using the OTP code sent."}

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import or_, func
    identifier = login_data.email.strip()
    user = db.query(User).filter(
        or_(
            func.lower(User.email) == identifier.lower(),
            func.lower(User.name) == identifier.lower()
        )
    ).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    # Migrate bcrypt hash to Argon2 if necessary
    if user.hashed_password.startswith("$2b$"):
        new_hash = get_password_hash(login_data.password)
        user.hashed_password = new_hash
        db.commit()
    
    if not user.is_verified:
        # Generate and dispatch a fresh 6-digit OTP verification code to user's registered email
        otp_code = generate_otp_code()
        expiration = datetime.utcnow() + timedelta(minutes=10)
        otp_record = OTP(
            email=user.email,
            code=otp_code,
            purpose="register",
            expires_at=expiration,
            verified=False
        )
        db.add(otp_record)
        db.commit()

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            delivered = send_otp_email(
                recipient_email=user.email,
                otp_code=otp_code,
                purpose="register",
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT,
                smtp_user=settings.SMTP_USER,
                smtp_password=settings.SMTP_PASSWORD,
                sender_name=settings.MAIL_FROM_NAME,
            )
            if delivered:
                logger.info(f"Dispatched login verification OTP email to {user.email}")
            else:
                logger.error(f"Failed to dispatch login verification OTP email to {user.email}")
        else:
            print(f"\n[OTP MAIL STUB] To: {user.email} | Code: {otp_code} | Purpose: register\n")

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your email address ({user.email}) has not been verified. A fresh OTP verification code has been sent to your email. Please verify to continue."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated."
        )
    
    # Issue JWT tokens
    access = create_access_token(data={"sub": user.email})
    refresh = create_refresh_token(data={"sub": user.email})
    
    # Save Refresh Token session metadata
    session_expiry = datetime.utcnow() + timedelta(days=7)
    dev_info = extract_device_info(request)
    db_session = UserSession(
        user_id=user.id,
        token=refresh,
        expires_at=session_expiry,
        revoked=False,
        device_name=dev_info["device_name"],
        platform=dev_info["platform"],
        ip_address=dev_info["ip_address"],
        user_agent=dev_info["user_agent"],
        last_active_at=datetime.utcnow(),
    )
    db.add(db_session)
    db.commit()

    # Log security audit event
    log_security_event(
        db=db,
        user_id=user.id,
        action="AUTH_LOGIN",
        status="SUCCESS",
        details=f"User authenticated on {dev_info['platform']} ({dev_info['device_name']})",
        request=request
    )
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
@limiter.limit("5/minute")
def refresh_session(refresh_data: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    payload = decode_token(refresh_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session refresh token."
        )
    
    # Validate session record
    db_session = db.query(UserSession).filter(UserSession.token == refresh_data.refresh_token).first()
    if not db_session or db_session.revoked or db_session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is expired or has been revoked."
        )
    
    user = db.query(User).filter(User.id == db_session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session is invalid or deactivated."
        )
    
    # Issue new access token and reuse or re-issue refresh token
    new_access = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": new_access,
        "refresh_token": refresh_data.refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout", response_model=MsgResponse)
@limiter.limit("5/minute")
def logout(logout_data: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    db_session = db.query(UserSession).filter(UserSession.token == logout_data.refresh_token).first()
    if db_session:
        db_session.revoked = True
        db.commit()
        log_security_event(
            db=db,
            user_id=db_session.user_id,
            action="AUTH_LOGOUT",
            status="SUCCESS",
            details="User logged out and revoked refresh token",
            request=request
        )
    
    return {"message": "Successfully logged out. Refresh token has been revoked."}

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[int] = None

@router.get("/me", response_model=UserResponse)
@limiter.limit("10/minute")
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserResponse)
@router.patch("/me", response_model=UserResponse)
@limiter.limit("10/minute")
def update_profile(
    profile_data: ProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.websocket_manager import ws_manager

    if profile_data.version is not None and getattr(current_user, "version", 1) != profile_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Conflict: User profile was updated on another client device.",
                "current_user": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "email": current_user.email,
                    "version": getattr(current_user, "version", 1),
                }
            }
        )

    if profile_data.name is not None and profile_data.name.strip():
        current_user.name = profile_data.name.strip()
        current_user.version = (getattr(current_user, "version", 1) or 1) + 1
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)

        user_data = UserResponse.model_validate(current_user).model_dump()
        ws_manager.publish_event(
            user_id=current_user.id,
            event="profile.updated",
            data=user_data,
            version=current_user.version,
            entity_id=str(current_user.id),
        )

    return current_user

@router.post("/send-otp", response_model=MsgResponse)
@limiter.limit("5/minute")
def send_otp(otp_data: OtpSend, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import or_, func
    identifier = otp_data.email.strip()
    user = db.query(User).filter(
        or_(
            func.lower(User.email) == identifier.lower(),
            func.lower(User.name) == identifier.lower()
        )
    ).first()
    if not user:
        # Prevent email scanning enumeration: return generic response, but do not generate OTP
        return {"message": "If the account is registered, a verification code has been dispatched."}
    
    target_email = user.email
    otp_code = generate_otp_code()
    expiration = datetime.utcnow() + timedelta(minutes=10)
    otp_record = OTP(
        email=target_email,
        code=otp_code,
        purpose=otp_data.purpose,
        expires_at=expiration,
        verified=False
    )
    db.add(otp_record)
    db.commit()
    
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        delivered = send_otp_email(
            recipient_email=target_email,
            otp_code=otp_code,
            purpose=otp_data.purpose,
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_password=settings.SMTP_PASSWORD,
            sender_name=settings.MAIL_FROM_NAME,
        )
        if not delivered:
            logger.error(f"OTP resend email delivery failed for {target_email} (purpose={otp_data.purpose})")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to send OTP email. Please verify email settings or try again later."
            )
        logger.info(f"Dispatched OTP verification email to {target_email} (purpose={otp_data.purpose})")
    else:
        print(f"\n[OTP MAIL STUB] To: {target_email} | Code: {otp_code} | Purpose: {otp_data.purpose}\n")
        logger.warning("SMTP not configured. Set SMTP_USER and SMTP_PASSWORD in backend/.env.")

    return {"message": f"Verification code dispatched successfully to {target_email}."}

@router.post("/verify-otp", response_model=VerifyOtpResponse)
@limiter.limit("5/minute")
def verify_otp(verify_data: OtpVerify, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import or_, func
    identifier = verify_data.email.strip()
    user = db.query(User).filter(
        or_(
            func.lower(User.email) == identifier.lower(),
            func.lower(User.name) == identifier.lower()
        )
    ).first()
    target_email = user.email if user else identifier

    # Find latest unverified, unexpired OTP matching query
    now = datetime.utcnow()
    otp_record = db.query(OTP).filter(
        or_(
            func.lower(OTP.email) == target_email.lower(),
            func.lower(OTP.email) == identifier.lower()
        ),
        OTP.code == verify_data.code.strip(),
        OTP.purpose == verify_data.purpose,
        OTP.verified == False,
        OTP.expires_at > now
    ).order_by(OTP.created_at.desc()).first()
    
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )
    
    otp_record.verified = True
    db.commit()
    
    if verify_data.purpose in ("register", "login"):
        if user:
            user.is_verified = True
            db.commit()
        return {
            "verified": True,
            "message": "Email verified successfully. You may now log in."
        }
    
    elif verify_data.purpose == "reset":
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account mapping not found."
            )
        
        reset_token = generate_secure_token()
        reset_record = PasswordResetToken(
            user_id=user.id,
            token=reset_token,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            used=False
        )
        db.add(reset_record)
        db.commit()
        
        return {
            "verified": True,
            "reset_token": reset_token,
            "message": "OTP verified successfully. Use the provided reset token to update password."
        }
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported verification purpose."
    )

@router.post("/forgot-password", response_model=MsgResponse)
@limiter.limit("5/minute")
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import or_, func
    identifier = req.email.strip()
    user = db.query(User).filter(
        or_(
            func.lower(User.email) == identifier.lower(),
            func.lower(User.name) == identifier.lower()
        )
    ).first()
    if not user:
        # Prevent email scanning: return generic message
        return {"message": "If the account exists, a 6-digit OTP code has been dispatched."}
    
    target_email = user.email
    otp_code = generate_otp_code()
    expiration = datetime.utcnow() + timedelta(minutes=10)
    otp_record = OTP(
        email=target_email,
        code=otp_code,
        purpose="reset",
        expires_at=expiration,
        verified=False
    )
    db.add(otp_record)
    db.commit()
    
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        delivered = send_otp_email(
            recipient_email=target_email,
            otp_code=otp_code,
            purpose="reset",
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_password=settings.SMTP_PASSWORD,
            sender_name=settings.MAIL_FROM_NAME,
        )
        if not delivered:
            logger.error(f"Password-reset OTP email delivery failed for {target_email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to send OTP email. Please verify email settings or try again later."
            )
        logger.info(f"Dispatched password reset OTP email to {target_email}")
    else:
        print(f"\n[OTP MAIL STUB] To: {target_email} | Code: {otp_code} | Purpose: reset\n")
        logger.warning("SMTP not configured. Set SMTP_USER and SMTP_PASSWORD in backend/.env.")

    return {"message": f"If the account exists, a 6-digit OTP code has been dispatched to {target_email}."}

@router.post("/reset-password", response_model=MsgResponse)
@limiter.limit("5/minute")
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    # Validate password complexity strength
    is_strong, strength_msg = validate_password_strength(req.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strength_msg
        )
    
    from sqlalchemy import or_, func
    user = db.query(User).filter(
        or_(
            func.lower(User.email) == req.email.strip().lower(),
            func.lower(User.name) == req.email.strip().lower()
        )
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account mapping not found."
        )
    
    # Validate reset token
    reset_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )
    
    # Hash and update password
    user.hashed_password = get_password_hash(req.new_password)
    user.is_verified = True
    reset_record.used = True
    db.commit()
    
    return {"message": "Password updated successfully. You may now log in with your new credentials."}
