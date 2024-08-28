from flask import Blueprint
import logging


train_model_bp = Blueprint("train_model", __name__)
logger = logging.getLogger(__name__)


@train_model_bp.post("/training_file")
def upload_training_file():
    pass
