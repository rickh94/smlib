from fastapi import APIRouter, Depends, UploadFile, File
from starlette.requests import Request

from app.auth.models import UserInDB
from app.auth.security import get_current_active_user
from app.dependencies import templates
from app.sheets.forms import SheetForm

sheet_router = APIRouter()


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
        filename = sheet_file.filename
        return f"Valid Form, {filename}"
    return "Something went wrong"
