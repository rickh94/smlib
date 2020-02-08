import logging
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
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


@sheet_router.get("/download/{sheet_id}")
async def download_sheet_by_id(
    sheet_id: str, current_user: UserInDB = Depends(get_current_active_user)
):
    sheet_id = uuid.UUID(sheet_id)
    logger.debug(type(sheet_id))
    sheet = await crud.get_sheet_by_id(current_user.email, sheet_id)
    data = storage.get_sheet(sheet.sheet_id, sheet.owner_email, sheet.file_ext)
    filename = ""
    if sheet.type.lower() == "part" and sheet.instruments:
        filename = sheet.instruments[0].upper().replace(" ", "").replace(".", "") + "-"
    elif sheet.type == "score":
        filename = "SCORE-"
    filename += sheet.composers[0].split(" ")[-1] + "-"
    filename += sheet.piece.replace(" ", "").replace(".", "")
    filename += "." + sheet.file_ext
    return StreamingResponse(
        data.stream(32 * 1024),
        headers={"Content-Disposition": f"attachment; filename={filename}",},
    )
