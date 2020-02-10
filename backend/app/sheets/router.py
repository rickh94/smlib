import logging
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Query
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.auth.models import UserInDB
from app.auth.security import get_current_active_user
from app.dependencies import templates
from app.sheets import models, storage, crud
from app.sheets.forms import SheetForm

sheet_router = APIRouter()

logger = logging.getLogger()


@sheet_router.get("/create")
async def get_create_sheet(
    request: Request, _current_user: UserInDB = Depends(get_current_active_user)
):
    form = SheetForm(meta={"csrf_context": request.session})
    return templates.TemplateResponse(
        "sheets/create.html", {"request": request, "form": form}
    )


@sheet_router.post("/create")
async def post_create_sheet(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
    sheet_file: UploadFile = File(...),
):
    form = SheetForm(await request.form(), meta={"csrf_context": request.session})
    if form.validate():
        sheet = models.Sheet(
            **form.data,
            owner_email=current_user.email,
            sheet_id=uuid.uuid4(),
            file_ext=sheet_file.filename.split(".")[-1],
        )
        print(sheet)
        await storage.save_sheet(
            sheet_file, sheet.sheet_id, sheet.owner_email, sheet.file_ext
        )
        created_sheet = await crud.create_sheet(sheet)
        return created_sheet
    return "Something went wrong"


@sheet_router.get("/{sheet_id}/download")
async def download_sheet_by_id(
    sheet_id: str, current_user: UserInDB = Depends(get_current_active_user)
):
    sheet_id = uuid.UUID(sheet_id)
    sheet = await crud.get_sheet_by_id(current_user.email, sheet_id)
    data = storage.get_sheet(sheet.sheet_id, sheet.owner_email, sheet.file_ext)
    filename = ""
    if sheet.type.lower() == "part" and sheet.instruments:
        filename = sheet.instruments[0].upper().replace(" ", "").replace(".", "") + "-"
    elif sheet.type.lower() == "score":
        filename = "SCORE-"
    filename += sheet.composers[0].split(" ")[-1] + "-"
    filename += sheet.piece.replace(" ", "").replace(".", "")
    filename += "." + sheet.file_ext
    return StreamingResponse(
        data.stream(32 * 1024),
        headers={"Content-Disposition": f"attachment; filename={filename}",},
    )


@sheet_router.get("/{sheet_id}/related")
async def get_related(
    request: Request,
    sheet_id: str,
    field: str = Query(...),
    page: int = Query(1),
    sort: str = Query("piece"),
    direction: int = Query(1),
    current_user: UserInDB = Depends(get_current_active_user),
):
    sheet_id = uuid.UUID(sheet_id)
    limit = int(os.getenv("SHEETS_PER_PAGE", 20))
    sheet = await crud.get_sheet_by_id(current_user.email, sheet_id)
    prev_page, next_page = get_next_prev_page_urls(request.url, page)
    if field == "piece":
        sheets = await crud.get_piece_related(sheet, limit, page, sort, direction,)
        if not await crud.piece_related_has_next(sheet, page, limit):
            next_page = None
    else:
        sheets = []
    return templates.TemplateResponse(
        "sheets/list.html",
        {
            "request": request,
            "page": page,
            "sort": sort,
            "direction": direction,
            "sheets": sheets,
            "next_page": next_page,
            "prev_page": prev_page,
            "title": f"Related to {getattr(sheet, field)}",
        },
    )


@sheet_router.get("/{sheet_id}")
async def get_sheet_info(
    request: Request,
    sheet_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    sheet_id = uuid.UUID(sheet_id)
    sheet = await crud.get_sheet_by_id(current_user.email, sheet_id)
    piece_related = await crud.get_piece_related(sheet, limit=3)
    return templates.TemplateResponse(
        "sheets/single.html",
        {"request": request, "sheet": sheet, "piece_related": piece_related},
    )


@sheet_router.get("")
async def get_sheets(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
    page: int = Query(1),
    sort: str = Query("piece"),
    direction: int = Query(1),
):
    limit = int(os.getenv("SHEETS_PER_PAGE", 20))
    sheet_cursor = await crud.get_user_sheets(
        current_user.email, page, sort, direction, limit
    )
    prev_page, next_page = get_next_prev_page_urls(request.url, page)
    if not await crud.user_sheets_has_next(current_user.email, page, limit):
        next_page = None
    user_sheets = [models.SheetOut.parse_obj(sheet) async for sheet in sheet_cursor]
    return templates.TemplateResponse(
        "sheets/list.html",
        {
            "request": request,
            "page": page,
            "sort": sort,
            "direction": direction,
            "sheets": user_sheets,
            "prev_page": prev_page,
            "next_page": next_page,
            "title": "All Sheets",
        },
    )


def get_next_prev_page_urls(url, page):
    next_page = url.remove_query_params(["page"]).include_query_params(page=(page + 1))
    prev_page = None
    if page > 1:
        prev_page = url.remove_query_params(["page"]).include_query_params(
            page=(page - 1)
        )
    return prev_page, next_page
