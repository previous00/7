from flask import Blueprint

response_bp = Blueprint('response', __name__)

from app.response import routes  # noqa: E402, F401
