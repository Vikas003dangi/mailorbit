from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Optional
import uuid
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from apps.api.config import settings
from apps.api.dependencies import get_admin_emails, get_current_user, get_db
from apps.api.services.rate_limiter import rate_limiter
from apps.api.services.system_mailer import (
    send_otp_email,
    send_password_reset_email,
    send_verification_email,
)
from packages.shared.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from packages.shared.schema import BootstrapRecord, EmailOTP, Profile, User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    timezone: str
    created_at: datetime
    is_superuser: bool = False
    is_email_verified: bool = False
    model_config = ConfigDict(from_attributes=True)


def to_user_out(user: User) -> UserOut:
    admin_set = get_admin_emails()
    is_verified = getattr(user, "is_email_verified", False)
    is_super = (user.email.lower() in admin_set) and is_verified
    return UserOut(
        id=user.id,
        email=user.email,
        timezone=user.timezone,
        created_at=user.created_at,
        is_superuser=is_super,
        is_email_verified=is_verified,
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
    message: Optional[str] = None


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    name: Optional[str] = None
    timezone: str = Field(default="UTC", description="User preferred time zone")


class SignupOtpRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class VerifySignupOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    confirm_password: str = Field(..., min_length=8, description="Confirm password")
    name: Optional[str] = None
    timezone: str = "UTC"


class ForgotPasswordOtpRequest(BaseModel):
    email: EmailStr


class ResetPasswordOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class ChangePasswordConfirmRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    otp: str = Field(..., min_length=6, max_length=6)


class DeleteAccountConfirmRequest(BaseModel):
    password: str
    confirmation_text: str  # Must be "DELETE"
    otp: str = Field(..., min_length=6, max_length=6)


def generate_numeric_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))



class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, description="Minimum 8 characters")


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Sets secure, HTTP-only, same-site refresh cookie."""
    response.set_cookie(
        key="mailorbit_refresh",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=7 * 24 * 3600,
        path="/api/v1/auth",
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: Request, payload: SignupRequest, response: Response, db: Session = Depends(get_db)):
    """Registers a new user workspace, creates verification token, and returns auth tokens."""
    rate_limiter.check(request, "signup", max_requests=5, window_seconds=3600)

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        )

    pwd_hash = hash_password(payload.password)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    user = User(
        email=payload.email.lower(),
        password_hash=pwd_hash,
        timezone=payload.timezone,
        is_email_verified=False,
        verification_token_hash=token_hash,
        verification_sent_at=now,
    )
    db.add(user)
    db.flush()

    # Create associated profile
    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)

    # Dispatch verification email via platform transactional mailer
    base_url = str(request.base_url).rstrip("/")
    mail_res = send_verification_email(to_email=user.email, token=raw_token, base_url=base_url)
    if mail_res.get("status") == "UNAVAILABLE":
        info_message = "Email verification is temporarily unavailable. Account registered in unverified mode with limited access."
    else:
        info_message = "Verification email dispatched. Please check your inbox to verify your account."

    access_token = create_access_token(str(user.id), user.email, settings.TICK_SECRET)
    refresh_token = create_refresh_token(str(user.id), settings.TICK_SECRET)
    set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=to_user_out(user),
        message=info_message,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues new access and refresh tokens with dual-keyed rate limiting."""
    rate_limiter.check(request, "login", max_requests=5, window_seconds=60, identifier=payload.email)

    user = db.query(User).filter(User.email == payload.email.lower(), User.is_active == True).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(str(user.id), user.email, settings.TICK_SECRET)
    refresh_token = create_refresh_token(str(user.id), settings.TICK_SECRET)
    set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=to_user_out(user),
    )


@router.get("/verify-email")
def verify_email(token: str = Query(..., description="Single-use verification token"), db: Session = Depends(get_db)):
    """Verifies a user's email address using a single-use token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = db.query(User).filter(User.verification_token_hash == token_hash).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

    user.is_email_verified = True
    user.verification_token_hash = None
    db.commit()

    return {
        "status": "success",
        "message": "Email verified successfully! You may now access full workspace features.",
        "email": user.email,
    }


@router.post("/forgot-password")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Dispatches a single-use password reset token via platform transactional mailer.
    Response is strictly identical whether the email exists or not to prevent user enumeration.
    """
    user = db.query(User).filter(User.email == payload.email.lower(), User.is_active == True).first()
    if user:
        raw_token = secrets.token_urlsafe(32)
        user.reset_token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.commit()

        base_url = str(request.base_url).rstrip("/")
        send_password_reset_email(to_email=user.email, token=raw_token, base_url=base_url)

    return {
        "status": "success",
        "message": "If an account exists with that email address, a password reset link has been dispatched. Please check your inbox.",
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Resets password using single-use hashed token valid for 30 minutes."""
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    user = db.query(User).filter(
        User.reset_token_hash == token_hash,
        User.reset_token_expires_at > now,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    user.password_hash = hash_password(payload.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.commit()

    return {
        "status": "success",
        "message": "Password has been reset successfully. You may now log in with your new password.",
    }


# =========================================================================
# Modern Single-Use 6-Digit OTP Flows (Signup, Reset, Change, Delete)
# =========================================================================


@router.post("/signup-otp")
def request_signup_otp(request: Request, payload: SignupOtpRequest, db: Session = Depends(get_db)):
    """Validates email availability and dispatches 6-digit verification OTP."""
    rate_limiter.check(request, "signup_otp", max_requests=5, window_seconds=300, identifier=payload.email)

    email_lower = payload.email.lower()
    existing = db.query(User).filter(User.email == email_lower).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in.",
        )

    # Clean existing pending signup OTPs for this email
    db.query(EmailOTP).filter(EmailOTP.email == email_lower, EmailOTP.purpose == "signup").delete()

    otp = generate_numeric_otp(6)
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    record = EmailOTP(
        email=email_lower,
        otp_hash=otp_hash,
        purpose="signup",
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()

    send_otp_email(to_email=email_lower, otp=otp, purpose_label="Verify Your Workspace Account")

    return {
        "status": "success",
        "message": f"A 6-digit verification code has been dispatched to {email_lower}. Valid for 15 minutes.",
        "email": email_lower,
    }


@router.post("/verify-signup-otp", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def verify_signup_otp(
    request: Request,
    payload: VerifySignupOtpRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Verifies OTP, confirms password match, creates verified user workspace, and returns tokens."""
    rate_limiter.check(request, "verify_signup_otp", max_requests=10, window_seconds=300, identifier=payload.email)

    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match. Please re-enter.",
        )

    email_lower = payload.email.lower()
    otp_hash = hashlib.sha256(payload.otp.strip().encode()).hexdigest()
    now = datetime.now(timezone.utc)

    otp_record = db.query(EmailOTP).filter(
        EmailOTP.email == email_lower,
        EmailOTP.otp_hash == otp_hash,
        EmailOTP.purpose == "signup",
        EmailOTP.expires_at > now,
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code. Please request a new code.",
        )

    # Double check user doesn't already exist
    existing = db.query(User).filter(User.email == email_lower).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in.",
        )

    # Create verified user account
    user = User(
        email=email_lower,
        password_hash=hash_password(payload.password),
        sender_name=payload.name.strip() if payload.name else None,
        timezone=payload.timezone or "UTC",
        is_email_verified=True,
    )
    db.add(user)
    db.flush()

    # Create profile with full_name
    profile = Profile(
        user_id=user.id,
        full_name=payload.name.strip() if payload.name else None,
    )
    db.add(profile)

    # Delete consumed OTP
    db.delete(otp_record)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id), user.email, settings.TICK_SECRET)
    refresh_token = create_refresh_token(str(user.id), settings.TICK_SECRET)
    set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=to_user_out(user),
        message="Workspace verified and created successfully!",
    )


@router.post("/forgot-password-otp")
def request_forgot_password_otp(request: Request, payload: ForgotPasswordOtpRequest, db: Session = Depends(get_db)):
    """Dispatches a 6-digit password reset OTP to the registered email."""
    rate_limiter.check(request, "forgot_password_otp", max_requests=5, window_seconds=300, identifier=payload.email)

    email_lower = payload.email.lower()
    user = db.query(User).filter(User.email == email_lower, User.is_active == True).first()
    if user:
        # Clean prior reset OTPs
        db.query(EmailOTP).filter(EmailOTP.email == email_lower, EmailOTP.purpose == "forgot_password").delete()

        otp = generate_numeric_otp(6)
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        record = EmailOTP(
            email=email_lower,
            otp_hash=otp_hash,
            purpose="forgot_password",
            expires_at=expires_at,
        )
        db.add(record)
        db.commit()

        send_otp_email(to_email=email_lower, otp=otp, purpose_label="Reset Your Password")

    return {
        "status": "success",
        "message": f"If an active account exists for {email_lower}, a 6-digit reset code has been sent.",
        "email": email_lower,
    }


@router.post("/reset-password-otp")
def reset_password_with_otp(payload: ResetPasswordOtpRequest, db: Session = Depends(get_db)):
    """Resets password after verifying the 6-digit OTP."""
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match.",
        )

    email_lower = payload.email.lower()
    otp_hash = hashlib.sha256(payload.otp.strip().encode()).hexdigest()
    now = datetime.now(timezone.utc)

    otp_record = db.query(EmailOTP).filter(
        EmailOTP.email == email_lower,
        EmailOTP.otp_hash == otp_hash,
        EmailOTP.purpose == "forgot_password",
        EmailOTP.expires_at > now,
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code. Please request a new code.",
        )

    user = db.query(User).filter(User.email == email_lower, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    user.password_hash = hash_password(payload.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.delete(otp_record)
    db.commit()

    return {
        "status": "success",
        "message": "Password updated successfully! You may now sign in with your new password.",
    }


@router.post("/change-password-otp")
def request_change_password_otp(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Authenticated user requests an OTP to change their workspace password."""
    email_lower = current_user.email.lower()
    db.query(EmailOTP).filter(EmailOTP.email == email_lower, EmailOTP.purpose == "change_password").delete()

    otp = generate_numeric_otp(6)
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    record = EmailOTP(
        email=email_lower,
        otp_hash=otp_hash,
        purpose="change_password",
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()

    send_otp_email(to_email=email_lower, otp=otp, purpose_label="Confirm Password Update")

    return {
        "status": "success",
        "message": f"A 6-digit confirmation code has been sent to {email_lower}.",
    }


@router.post("/confirm-change-password")
def confirm_change_password(
    payload: ChangePasswordConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirms current password, matching new passwords, and 6-digit OTP to update password."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match.",
        )

    email_lower = current_user.email.lower()
    otp_hash = hashlib.sha256(payload.otp.strip().encode()).hexdigest()
    now = datetime.now(timezone.utc)

    otp_record = db.query(EmailOTP).filter(
        EmailOTP.email == email_lower,
        EmailOTP.otp_hash == otp_hash,
        EmailOTP.purpose == "change_password",
        EmailOTP.expires_at > now,
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired confirmation code.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.delete(otp_record)
    db.commit()

    return {
        "status": "success",
        "message": "Password updated successfully.",
    }


@router.post("/delete-account-otp")
def request_delete_account_otp(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dispatches a high-priority 6-digit verification code to delete workspace."""
    email_lower = current_user.email.lower()
    db.query(EmailOTP).filter(EmailOTP.email == email_lower, EmailOTP.purpose == "delete_account").delete()

    otp = generate_numeric_otp(6)
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    record = EmailOTP(
        email=email_lower,
        otp_hash=otp_hash,
        purpose="delete_account",
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()

    send_otp_email(to_email=email_lower, otp=otp, purpose_label="Permanently Delete Workspace")

    return {
        "status": "success",
        "message": f"A deletion confirmation code has been dispatched to {email_lower}.",
    }


@router.post("/confirm-delete-account")
def confirm_delete_account(
    payload: DeleteAccountConfirmRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently erases user account and cascades all associated data
    (campaigns, batches, contacts, relays, files, keys).
    Requires OTP, correct password, and typing 'DELETE'.
    """
    if payload.confirmation_text.strip().upper() != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type DELETE in the confirmation box.",
        )

    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password.",
        )

    email_lower = current_user.email.lower()
    otp_hash = hashlib.sha256(payload.otp.strip().encode()).hexdigest()
    now = datetime.now(timezone.utc)

    otp_record = db.query(EmailOTP).filter(
        EmailOTP.email == email_lower,
        EmailOTP.otp_hash == otp_hash,
        EmailOTP.purpose == "delete_account",
        EmailOTP.expires_at > now,
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired deletion code.",
        )

    # Cascading delete of all tenant data
    db.delete(otp_record)
    db.delete(current_user)
    db.commit()

    response.delete_cookie(
        key="mailorbit_refresh",
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
        secure=True,
    )

    return {
        "status": "success",
        "message": "Your workspace, profile, campaigns, and contacts have been permanently erased.",
    }



@router.post("/logout")
def logout(response: Response):
    """Server-side logout clearing the same-site HttpOnly refresh cookie."""
    response.delete_cookie(
        key="mailorbit_refresh",
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return {
        "status": "success",
        "message": "Logged out successfully",
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    response: Response,
    payload: Optional[RefreshRequest] = None,
    cookie_refresh: Optional[str] = Cookie(None, alias="mailorbit_refresh"),
    db: Session = Depends(get_db),
):
    """Exchanges a valid refresh token for a fresh access token."""
    token_str = (payload.refresh_token if payload and payload.refresh_token else None) or cookie_refresh
    if not token_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    try:
        decoded = decode_token(token_str, settings.TICK_SECRET)
        if decoded.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = decoded.get("sub")
        user_uuid = uuid.UUID(str(user_id))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = create_access_token(str(user.id), user.email, settings.TICK_SECRET)
    new_refresh = create_refresh_token(str(user.id), settings.TICK_SECRET)
    set_refresh_cookie(response, new_refresh)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=to_user_out(user),
    )


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user details."""
    return to_user_out(current_user)


class BootstrapAdminRequest(BaseModel):
    bootstrap_token: str = Field(..., description="One-time administrator bootstrap secret token")


@router.post("/bootstrap-admin")
def bootstrap_admin(
    request: Request,
    payload: BootstrapAdminRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    One-time bootstrap endpoint to safely elevate an account whose email is in ADMIN_EMAILS
    to verified status when system transactional email is offline.
    Permanently records token consumption in the database so it can NEVER be reused across restarts.
    """
    # 1. Caller Authorization Check (must be in ADMIN_EMAILS)
    admin_set = get_admin_emails()
    if not current_user.email or current_user.email.lower() not in admin_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User email is not authorized for administrative bootstrap",
        )

    # 2. Token Matching Check
    expected_token = getattr(settings, "ADMIN_BOOTSTRAP_TOKEN", None)
    if not expected_token or not secrets.compare_digest(payload.bootstrap_token.strip(), expected_token.strip()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired admin bootstrap token",
        )

    # 3. Permanent Database Consumption Check
    token_hash = hashlib.sha256(payload.bootstrap_token.strip().encode()).hexdigest()
    consumed = db.query(BootstrapRecord).filter(BootstrapRecord.token_hash == token_hash).first()
    if consumed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin bootstrap token has already been consumed and cannot be reused",
        )

    # Elevate and verify user
    current_user.is_email_verified = True
    current_user.verification_token_hash = None

    # Persist consumption record in database permanently
    client_ip = request.client.host if request.client else None
    record = BootstrapRecord(
        token_hash=token_hash,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    db.add(record)
    db.commit()

    # Invalidate token in memory immediately
    settings.ADMIN_BOOTSTRAP_TOKEN = None

    return {
        "status": "success",
        "message": f"User {current_user.email} successfully verified and elevated to administrator. Token permanently consumed in database.",
        "user": to_user_out(current_user),
    }

