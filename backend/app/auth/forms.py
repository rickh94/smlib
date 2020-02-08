import wtforms
from wtforms.validators import InputRequired, Email

from app.dependencies import CSRFForm


class RequestLoginForm(CSRFForm):
    email = wtforms.StringField(
        "Email",
        validators=[InputRequired(), Email("Invalid Email.")],
        render_kw={"type": "email", "placeholder": "name@example.com"},
    )
    login_type = wtforms.SelectField(
        "Login Method",
        choices=[("magic", "Magic Link"), ("code", "One Time Code")],
        validators=[InputRequired()],
    )
    submit = wtforms.SubmitField()


class SubmitCodeForm(CSRFForm):
    email = wtforms.HiddenField()
    code = wtforms.StringField(
        "Login Code", validators=[InputRequired()], render_kw={"placeholder": "123456"},
    )
    submit = wtforms.SubmitField()


class EnterEmailForm(CSRFForm):
    email = wtforms.StringField(
        "Email",
        validators=[InputRequired(), Email("Invalid Email.")],
        render_kw={"type": "email", "placeholder": "name@example.com"},
    )
    secret = wtforms.HiddenField()
    submit = wtforms.SubmitField()
