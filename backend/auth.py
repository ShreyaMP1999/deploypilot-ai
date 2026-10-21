import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from backend.db.models import Membership, User
from backend.db.session import get_db
from backend.settings import settings

bearer = HTTPBearer(auto_error=False)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310_000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310_000).hex()
    return hmac.compare_digest(candidate, digest)


DUMMY_HASH = hash_password("dummy-password-do-not-use")


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    role: str


def issue_token(user_id, tenant_id):
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": user_id,
            "tenant": tenant_id,
            "iat": now,
            "exp": now + timedelta(minutes=settings().token_ttl_minutes),
            "iss": "deploypilot",
            "aud": "deploypilot-web",
        },
        settings().jwt_secret,
        algorithm="HS256",
    )


def authenticate(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)
):
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings().jwt_secret,
            algorithms=["HS256"],
            audience="deploypilot-web",
            issuer="deploypilot",
            options={"require": ["sub", "tenant", "iat", "exp"]},
        )
        membership = db.get(Membership, (claims["sub"], claims["tenant"]))
        if not membership:
            raise ValueError("Membership unavailable")
        return Principal(membership.user_id, membership.tenant_id, membership.role)
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Invalid or expired session") from None


def login(db, username, password, tenant_id):
    user = db.scalar(select(User).where(User.username == username))
    valid = verify_password(password, user.password_hash if user else DUMMY_HASH)
    if not valid or not user or not db.get(Membership, (user.id, tenant_id)):
        raise HTTPException(401, "Invalid credentials or unavailable customer")
    return {"access_token": issue_token(user.id, tenant_id), "token_type": "bearer"}
