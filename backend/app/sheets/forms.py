import wtforms
from wtforms.validators import InputRequired, Optional

from app.dependencies import CSRFForm
from app.sheets.models import Sheet


def form_field_from_model(
    model, field_name, field_class=wtforms.StringField, validators=None, **kwargs
):
    if not validators:
        validators = []
    field = model.schema()["properties"][field_name]
    if field_name in model.schema()["required"]:
        validators.append(InputRequired())
    else:
        validators.append(Optional())
    return field_class(
        label=field["title"],
        description=field["description"],
        validators=validators,
        **kwargs
    )


class ListField(wtforms.Field):
    widget = wtforms.widgets.TextArea()

    def _value(self):
        if self.data:
            return ", ".join(self.data)
        else:
            return ""

    def process_formdata(self, valuelist):
        if valuelist:
            split_char = "," if "," in valuelist[0] else "\n"
            self.data = [x.strip() for x in valuelist[0].split(split_char)]
        else:
            self.data = []


class SheetForm(CSRFForm):
    piece = form_field_from_model(Sheet, "piece")
    composers = form_field_from_model(Sheet, "composers", field_class=ListField)
    genre = form_field_from_model(Sheet, "genre")
    tags = form_field_from_model(Sheet, "tags", field_class=ListField)
    instruments = form_field_from_model(Sheet, "instruments", field_class=ListField)
    type = form_field_from_model(Sheet, "type")
    catalog_number = form_field_from_model(Sheet, "catalog_number")
    sheet_file = wtforms.FileField("Sheet File", validators=[InputRequired()])
    submit = wtforms.SubmitField()


class UpdateSheetForm(SheetForm):
    sheet_file = wtforms.FileField("Sheet File (optional)")
