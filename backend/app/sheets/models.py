import datetime
from typing import Optional, List, Tuple

from pydantic import BaseModel, EmailStr, Field, UUID4


class Sheet(BaseModel):
    @staticmethod
    def sortable_fields():
        return [
            "piece",
            "composers",
            "genre",
            "tags",
            "instruments",
            "type",
            "catalog_number",
        ]

    @staticmethod
    def allowed_related_fields():
        return [
            "piece",
            "composers",
            "genre",
            "tags",
            "instruments",
            "type",
            "catalog_number",
        ]

    piece: str = Field(..., title="Piece Title", description="The title of the piece.")
    catalog_number: str = Field(
        None,
        title="Catalog Number",
        description="Any catalog information about the piece.",
    )
    composers: List[str] = Field(
        ...,
        title="Composers",
        description="The composers of the piece. (separated by commas)",
    )
    genre: Optional[str] = Field(
        None, title="Genre", description="The genre of the piece."
    )
    tags: Optional[List[str]] = Field(
        None,
        title="Tags",
        description="Additional tags to search against. (separated by commas)",
    )
    instruments: Optional[List[str]] = Field(
        None,
        title="Instruments",
        description="The instruments in the piece. (separated by commas)",
    )
    type: Optional[str] = Field(
        None,
        title="Type",
        description="The type of the sheet, e.g. part, score, lead-sheet.",
    )
    owner_email: EmailStr = Field(
        ..., title="Owner Email", description="Email address of owner of file"
    )
    sheet_id: UUID4 = Field(..., title="Unique ID")
    file_ext: str = Field(..., title="File Extension")
    current: bool = Field(
        True,
        title="Current",
        description="Whether this is the current version of a sheet.",
    )


class SheetWithVersions(Sheet):
    prev_versions: Optional[List[Tuple[UUID4, datetime.datetime]]] = Field(
        None,
        title="Previous Versions",
        description="UUIDs of previous versions of this sheet.",
    )


class SheetInDB(SheetWithVersions):
    _id: Optional[str] = None

    @property
    def id(self):
        return self._id

    def clean_empty_strings(self):
        if not self.genre:
            self.genre = None
        if not self.type:
            self.type = None
        if len(self.tags) == 1 and not self.tags[0]:
            self.tags = None
        if len(self.instruments) == 1 and not self.instruments[0]:
            self.instruments = None

    def clean_tags(self):
        self.tags = [tag.lower() for tag in self.tags]


class SheetOut(SheetWithVersions):
    pass
