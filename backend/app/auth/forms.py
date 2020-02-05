import wtforms
from wtforms.validators import InputRequired, Email

from app.dependencies import CSRFForm


class RequestLoginForm(CSRFForm):
    email = wtforms.StringField(
        "Email", validators=[InputRequired(), Email("Invalid Email.")]
    )
    login_type = wtforms.SelectField(
        "Login Method",
        choices=[("magic", "Magic Link"), ("code", "One Time Code")],
        validators=[InputRequired()],
    )
    submit = wtforms.SubmitField()
