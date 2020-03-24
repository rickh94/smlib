import logging
import os
import string
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Query
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.auth.models import UserInDB
from app.auth.security import get_current_active_user
from app.dependencies import templates
from app.util import get_next_prev_page_urls, get_sort_links
from app.sheets import models, storage, crud
from app.sheets.forms import SheetForm, UpdateSheetForm

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
        await storage.save_sheet(
            sheet_file, sheet.sheet_id, sheet.owner_email, sheet.file_ext
        )
        created_sheet = await crud.create_sheet(sheet)
        return templates.TemplateResponse(
            "sheets/created.html",
            {"request": request, "sheet_id": created_sheet.sheet_id},
        )
    return "Something went wrong"


def clean_for_filename(text: str):
    allowed_chars = f"-_(){string.ascii_letters}{string.digits}"
    return "".join(c for c in text if c in allowed_chars)


@sheet_router.get("/{sheet_id}/download")
async def download_sheet_by_id(
    sheet_id: str, current_user: UserInDB = Depends(get_current_active_user)
):
    sheet_id = uuid.UUID(sheet_id)
    sheet = await crud.get_sheet_by_id(current_user.email, sheet_id)
    data = storage.get_sheet(sheet.sheet_id, sheet.owner_email, sheet.file_ext)
    filename = ""
    if sheet.type.lower() == "part" and sheet.instruments:
        filename = sheet.instruments[0].upper() + "-"
    elif sheet.type.lower() == "score":
        filename = "SCORE-"
    filename += sheet.composers[0].split(" ")[-1] + "-"
    filename += sheet.piece.title().replace(" ", "").replace(".", "")
    filename = clean_for_filename(filename) + "." + sheet.file_ext
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
    if field in models.Sheet.allowed_related_fields():
        sheets = await crud.find_related(
            sheet, field, limit, page, sort, direction, exclude=False
        )
        if not await crud.related_has_next(sheet, field, page, limit):
            next_page = None
    else:
        sheets = []
    title_text = getattr(sheet, field)
    if isinstance(title_text, list):
        title_text = ", ".join(title_text)
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
            "title": f"Related to {title_text}",
            "sort_links": get_sort_links(request.url, sort, direction),
        },
    )


@sheet_router.get("/{sheet_id}/update")
async def get_sheet_update_form(
    request: Request,
    sheet_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    form = UpdateSheetForm(meta={"csrf_context": request.session})
    sheet_id = uuid.UUID(sheet_id)
    sheet = await crud.get_sheet_by_id(current_user.email, sheet_id)
    form.piece.data = sheet.piece
    form.composers.data = sheet.composers
    form.genre.data = sheet.genre
    form.tags.data = sheet.tags
    form.instruments.data = sheet.instruments
    form.type.data = sheet.type
    return templates.TemplateResponse(
        "sheets/update.html",
        {
            "request": request,
            "form": form,
            "sheet_id": sheet_id,
            "piece_title": sheet.piece,
        },
    )


@sheet_router.post("/{sheet_id}/update")
async def post_sheet_update(
    request: Request,
    sheet_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    sheet_file: UploadFile = File(None),
):
    form = UpdateSheetForm(await request.form(), meta={"csrf_context": request.session})
    if form.validate():
        old_sheet = await crud.get_sheet_by_id(current_user.email, uuid.UUID(sheet_id))
        new_id = uuid.uuid4()
        file_ext = old_sheet.file_ext
        if sheet_file.filename:
            file_ext = sheet_file.filename.split(".")[-1]
            await storage.save_sheet(sheet_file, new_id, current_user.email, file_ext)
        else:
            storage.copy_sheet(
                old_sheet.sheet_id, new_id, current_user.email, old_sheet.file_ext
            )
        new_sheet = models.Sheet(
            **form.data,
            owner_email=current_user.email,
            sheet_id=uuid.uuid4(),
            file_ext=file_ext,
        )
        new_sheet_in_db = await crud.update_sheet(old_sheet, new_sheet)
        return templates.TemplateResponse(
            "sheets/created.html",
            {"request": request, "sheet_id": new_sheet_in_db.sheet_id},
        )
    return "Something went wrong"


@sheet_router.get("/{sheet_id}")
async def get_sheet_info(
    request: Request,
    sheet_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    sheet_id = uuid.UUID(sheet_id)
    sheet = await crud.get_sheet_by_id(current_user.email, sheet_id)
    logger.debug(sheet.prev_versions)
    related_lists = {
        "piece": {
            "items": await crud.find_related(sheet, "piece", limit=3),
            "plural": False,
        },
        "composers": {
            "items": await crud.find_related(sheet, "composers", limit=3),
            "plural": True,
        },
        "tags": {
            "items": await crud.find_related(sheet, "tags", limit=3),
            "plural": True,
        },
    }
    return templates.TemplateResponse(
        "sheets/single.html",
        {"request": request, "sheet": sheet, "related_lists": related_lists,},
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
    sort_links = get_sort_links(request.url, sort, direction)
    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "page": page,
            "sort": sort,
            "direction": direction,
            "sheets": user_sheets,
            "prev_page": prev_page,
            "next_page": next_page,
            "title": "All Sheets",
            "sort_links": sort_links,
        },
    )
