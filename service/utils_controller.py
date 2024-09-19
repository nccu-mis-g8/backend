from flask import Blueprint
import logging

utils_bp = Blueprint("utils", __name__)
logger = logging.getLogger(__name__)


# only allow to upload csv file
ALLOWED_EXTENSIONS = set(["csv"])


@utils_bp.post("/user/upload_file")
def upload_file():
    pass
