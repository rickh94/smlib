from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AuthRole(Enum):
    admin = "ADMIN"
    standard = "STANDARD"


class User(BaseModel):
    email: EmailStr = Field(
        ..., title="Email", description="An email to be used for signing in."
    )
    full_name: Optional[str] = Field(None, title="Full Name")
    disabled: Optional[bool] = Field(
        False,
        title="Disabled",
        description="Whether a user's account has been disabled",
    )


class UserWithRole(User):
    role: AuthRole = AuthRole.standard


class UserInDB(UserWithRole):
    class Config:
        use_enum_values = True

    _id: Optional[str] = None

    @property
    def id(self):
        return self._id


class OTP(BaseModel):
    email: EmailStr = Field(..., title="Email")
    code: str = Field(
        ..., title="One Time Password", description="Single use login code"
    )


class Magic(BaseModel):
    email: EmailStr = Field(..., title="Email")
    secret: str = Field(..., title="Secret from magic link url.")


class AuthRequest(BaseModel):
    email: EmailStr = Field(..., title="Email", description="Email of registered user")
    next: str = Field(None, title="Next", description="Next url to redirect to")
