from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Schema


class AuthRole(Enum):
    admin = "ADMIN"
    standard = "STANDARD"


class User(BaseModel):
    email: EmailStr = Schema(
        ..., title="Email", description="An email to be used for signing in."
    )
    full_name: Optional[str] = Schema(None, title="Full Name")
    disabled: Optional[bool] = Schema(
        False,
        title="Disabled",
        description="Whether a user's account has been disabled",
    )


class UserWithRole(User):
    role: AuthRole = AuthRole.standard


class UserInDB(UserWithRole):
    _id: Optional[str] = None

    @property
    def id(self):
        return self._id


class OTP(BaseModel):
    email: EmailStr = Schema(..., title="Email")
    code: str = Schema(
        ..., title="One Time Password", description="Single use login code"
    )


class Magic(BaseModel):
    email: EmailStr = Schema(..., title="Email")
    secret: str = Schema(..., title="Secret from magic link url.")


class AuthRequest(BaseModel):
    email: EmailStr = Schema(..., title="Email", description="Email of registered user")
    next: str = Schema(None, title="Next", description="Next url to redirect to")
