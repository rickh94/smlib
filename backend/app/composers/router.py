import logging
import os

from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from app.auth.models import UserInDB
from app.auth.security import get_current_active_user
from app.composers import crud
from app.dependencies import get_next_prev_page_urls, templates

composer_router = APIRouter()

logger = logging.getLogger()


@composer_router.get("/{composer_name}")
async def get_single_composer(
    request: Request,
    composer_name: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    pass


@composer_router.get("")
async def get_composers(
    request: Request, current_user: UserInDB = Depends(get_current_active_user),
):
    composers = await crud.get_all_composers(current_user.email)
    return templates.TemplateResponse(
        "composers/all.html",
        {"request": request, "composers": sorted(composers), "title": "All Composers"},
    )
