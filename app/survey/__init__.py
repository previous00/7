from flask import Blueprint

survey_bp = Blueprint('survey', __name__)

from app.survey import routes  # noqa: E402, F401
