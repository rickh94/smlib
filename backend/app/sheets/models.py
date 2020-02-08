from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, UUID4


class SheetIn(BaseModel):
    piece: str = Field(..., title="Piece Title", description="The title of the piece.")
    composers: List[str] = Field(
        ..., title="Composers", description="The composer of the piece."
    )
    genre: Optional[str] = Field(
        None, title="Genre", description="The genre of the piece."
    )
    tags: Optional[List[str]] = Field(
        None, title="Tags", description="Additional tags to search against."
    )
    instruments: Optional[List[str]] = Field(
        None, title="Instruments", description="The instruments in the piece"
    )
    type: Optional[str] = Field(
        None,
        title="Type",
        description="The type of the sheet, e.g. part, score, lead-sheet.",
    )


class Sheet(SheetIn):
    owner_email: EmailStr = Field(
        ..., title="Owner Email", description="Email address of owner of file"
    )
    sheet_id: UUID4 = Field(..., title="Unique ID")


class SheetInDB(Sheet):
    _id: Optional[str] = None
    path: str = Field(
        ..., title="File Path", description="The path to the file in minio."
    )
    file_ext: str = Field(..., title="File Extension")

    @property
    def id(self):
        return self._id


class SheetOut(Sheet):
    pass
