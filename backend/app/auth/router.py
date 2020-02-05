import datetime
import logging
import os
from typing import List

from fastapi import APIRouter, Depends, Body, HTTPException, Form, Query
from starlette.requests import Request
from starlette.responses import UJSONResponse
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from app.auth import models, security, crud
from app.auth.forms import RequestLoginForm
from app.auth.security import oauth2_scheme
from app.dependencies import send_email, templates

auth_router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
mailgun_key = os.getenv("MAILGUN_KEY")
mailgun_enpoint = os.getenv("MAILGUN_ENDPOINT")
from_name = os.getenv("MAILGUN_FROM_NAME")
from_address = os.getenv("MAILGUN_FROM_ADDRESS")
DEBUG = bool(os.getenv("DEBUG", False))
secure_cookies = not DEBUG

logger = logging.getLogger()

from_name = os.getenv("MAILGUN_FROM_NAME")
from_address = os.getenv("MAILGUN_FROM_ADDRESS")


@auth_router.get("/login")
async def login(request: Request, next_location: str = Query(None, alias="next")):
    form = RequestLoginForm(meta={"csrf_context": request.session})
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "next_location": next_location, "form": form},
    )


@auth_router.post("/login")
async def login_post(
    request: Request,
    # email: str = Form(...),
    # login_type: str = Form(...),
    next_location: str = Query(None, alias="next"),
):
    form = RequestLoginForm(
        await request.form(), meta={"csrf_context": request.session}
    )
    if not form.validate():
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "form": form}
        )
    email = form.email.data
    login_type = form.login_type.data
    user = await crud.get_user_by_email(email)
    if not user:
        form.email.errors.append("Could not find user with this email.")
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "form": form},
        )
    if user.disabled:
        form.email.errors.append("This user is disabled.")
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "form": form},
        )
    if login_type == "code":
        await send_otp(email)
        return templates.TemplateResponse(
            "auth/submit-code.html",
            {"request": request, "email": email, "next_location": next_location},
        )
    elif login_type == "magic":
        await send_magic(email, next_location, "/auth/magic")
        response = templates.TemplateResponse(
            "auth/magic-sent.html", {"request": request}
        )
        response.set_cookie("magic_email", email, httponly=True, secure=secure_cookies)
        return response
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "form": form, "error": "Something has gone wrong."},
    )


async def send_otp(email):
    otp = security.generate_otp(email)
    await send_email(
        email,
        "Your One Time Password",
        f"Your password is {otp}",
        from_address,
        from_name,
    )


async def send_magic(email, next_location, location):
    magic_link = security.generate_magic_link(email, next_location, location)
    await send_email(
        email,
        "Your magic sign in link",
        f"Click this link to sign in\n{magic_link}",
        from_address,
        from_name,
    )


@auth_router.post("/request")
async def request_login(data: models.AuthRequest = Body(...)):
    user = await crud.get_user_by_email(data.email)
    if not user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="No user with that email."
        )
    if user.disabled:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="This user is disabled."
        )
    await send_otp(data.email)
    return "Please check your email for a single use password."


@auth_router.post("/request-magic")
async def request_magic(data: models.AuthRequest = Body(...)):
    user = await crud.get_user_by_email(data.email)
    if not user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="No user with that email."
        )
    if user.disabled:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="This user is disabled."
        )
    await send_magic(data.email, data.next, location="/api/login")
    return "Please check your email for your sign in link."


@auth_router.post("/confirm-magic")
async def verify_magic(data: models.Magic = Body(...)):
    user = await security.authenticate_user_magic(data.email, data.secret)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid Link")
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    response = UJSONResponse({"status": "authenticated"})
    response.set_cookie(
        oauth2_scheme.token_name, access_token, httponly=True, secure=secure_cookies
    )
    return response


@auth_router.post("/confirm")
async def confirm_login(data: models.OTP = Body(...)):
    user = await security.authenticate_user(data.email, data.code)
    logger.debug(user)
    if not user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid Email or Code"
        )
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    response = UJSONResponse({"status": "authenticated"})
    response.set_cookie(
        oauth2_scheme.token_name, access_token, httponly=True, secure=secure_cookies
    )
    return response


@auth_router.post(
    "/register",
    response_model=models.User,
    status_code=HTTP_201_CREATED,
    responses={400: {"description": "Email is invalid"}},
)
async def register(user: models.User = Body(...)):
    if await crud.get_user_by_email(user.email):
        raise HTTPException(
            status_code=400, detail="A user with that email already exists"
        )
    new_user = models.UserInDB.parse_obj(user)
    created_user = await crud.create_user(new_user)
    return created_user


@auth_router.get("/sign-out")
async def sign_out(
    current_user: models.User = Depends(security.get_current_active_user),
):
    response = UJSONResponse({"status": "signed out"})
    response.set_cookie(oauth2_scheme.token_name, "", httponly=True)
    return response


@auth_router.get("/me", response_model=models.User)
async def read_users_me(
    current_user: models.User = Depends(security.get_current_active_user),
):
    """Get User data"""
    return current_user


@auth_router.put("/me", response_model=models.User)
async def update_users_me(
    current_user: models.UserWithRole = Depends(security.get_current_active_user),
    updated: models.User = Body(...),
):
    """Updates user info."""
    updated_with_role = models.UserWithRole.parse_obj(updated)
    updated_with_role.role = current_user.role
    updated_user = await crud.update_user_by_email(
        current_user.email, updated_with_role
    )
    return updated_user


@auth_router.get("/users/all", response_model=List[models.UserInDB])
async def admin_read_all_users(
    _current_user: models.UserInDB = Depends(security.get_current_admin_user),
):
    """Get data for all users"""
    all_users = []
    async for user in await crud.get_all_users():
        all_users.append(user)
    return all_users


@auth_router.post(
    "/users",
    response_model=models.User,
    status_code=HTTP_201_CREATED,
    responses={400: {"description": "Email is invalid"}},
)
async def create_user(
    user: models.User = Body(...),
    _current_user=Depends(security.get_current_admin_user),
):
    if await crud.get_user_by_email(user.email):
        raise HTTPException(
            status_code=400, detail="A user with that email already exists"
        )
    new_user = models.UserInDB.parse_obj(user)
    created_user = await crud.create_user(new_user)
    return created_user


@auth_router.get("/users/{user_email}")
async def admin_read_user(
    user_email: str,
    _current_user: models.UserWithRole = Depends(security.get_current_admin_user),
):
    """Admin: Get a single user"""
    user = await crud.get_user_by_email(user_email)
    if not user:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="Could not find matching user."
        )
    return user


@auth_router.put("/users/{user_email}", response_model=models.UserWithRole)
async def admin_update_user(
    user_email: str,
    _current_user: models.UserWithRole = Depends(security.get_current_admin_user),
    updated: models.UserWithRole = Body(...),
):
    """Admin update a user."""
    updated = models.UserInDB.parse_obj(updated)
    return await crud.update_user_by_email(user_email, updated)


@auth_router.delete("/users/{user_email}", response_model=str)
async def admin_delete_user(
    user_email: str,
    _current_user: models.UserWithRole = Depends(security.get_current_admin_user),
):
    """Admin delete a user."""
    print(_current_user)
    await crud.delete_user_by_email(user_email)
    return "User Deleted"
