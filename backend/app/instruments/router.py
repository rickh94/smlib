import logging
import os

from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from app import util
from app.auth.models import UserInDB
from app.auth.security import get_current_active_user
from app.instruments import crud
from app.dependencies import templates

instrument_router = APIRouter()

logger = logging.getLogger()


@instrument_router.get("/{instrument_name}")
async def get_single_instrument(
    request: Request,
    instrument_name: str,
    current_user: UserInDB = Depends(get_current_active_user),
    page: int = Query(1),
    sort: str = Query("piece"),
    direction: int = Query(1),
):
    limit = int(os.getenv("SHEETS_PER_PAGE", 20))
    prev_page, next_page = util.get_next_prev_page_urls(request.url, page)
    sheets = await crud.get_instrument_sheets(
        current_user.email, instrument_name, limit, page, sort, direction
    )
    if not await crud.instrument_sheets_has_next(
        current_user.email, instrument_name, limit, page
    ):
        next_page = None
    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "page": page,
            "sort": sort,
            "direction": direction,
            "sheets": sheets,
            "next_page": next_page,
            "prev_page": prev_page,
            "sort_links": util.get_sort_links(request.url, sort, direction),
            "title": instrument_name,
        },
    )


@instrument_router.get("")
async def get_instruments(
    request: Request, current_user: UserInDB = Depends(get_current_active_user),
):
    instruments = await crud.get_all_instruments(current_user.email)
    return templates.TemplateResponse(
        "instruments/all.html",
        {
            "request": request,
            "instruments": sorted(instruments),
            "title": "All instruments",
        },
    )
