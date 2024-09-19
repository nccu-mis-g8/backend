from flask import (
    Blueprint,
    app,
    request,
    jsonify,
)
import json
import os
import logging

from repository.trainingfile_repo import TrainingFileRepo

utils_bp = Blueprint("utils", __name__)
logger = logging.getLogger(__name__)


# only allow to upload csv file
ALLOWED_EXTENSIONS = set(["csv"])


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@utils_bp.post("/user/upload_file")
def upload_file():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("userId")
    # Check if a file was provided in the request
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # Check if a file was actually selected
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # Validate if the file has a CSV extension
    if file and allowed_file(file.filename):
        saved_file = TrainingFileRepo.create_traingfile(user_id)
        file.save(os.path.join("../training_file", saved_file.filename))
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only CSV files are allowed."}),
            400,
        )
