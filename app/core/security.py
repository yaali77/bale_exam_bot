from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from pwdlib import PasswordHash

from app.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: dict | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None


def validate_national_code(code: str) -> bool:
    """اعتبارسنجی کد ملی ۱۰ رقمی ایران."""

    if not code or not code.isdigit() or len(code) != 10:
        return False

    if code == code[0] * 10:
        return False

    check = int(code[9])
    total = sum(int(code[i]) * (10 - i) for i in range(9))
    remainder = total % 11

    if remainder < 2:
        return check == remainder

    return check == 11 - remainder


def validate_phone_number(phone: str) -> bool:
    """اعتبارسنجی شماره موبایل ایران با فرمت 09xxxxxxxxx."""

    return (
        bool(phone)
        and phone.isdigit()
        and len(phone) == 11
        and phone.startswith("09")
    )
