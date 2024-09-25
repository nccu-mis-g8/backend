from flask import (
    Blueprint,
    request,
    jsonify,
)
from flasgger import swag_from
import json
import os
import logging


from repository.trainingfile_repo import TrainingFileRepo

utils_bp = Blueprint("utils", __name__)
logger = logging.getLogger(__name__)


FILE_DIRECTORY = "..\\training_file"


def allowed_file(filename, extension):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == extension


@utils_bp.post("/user/upload_file")
@swag_from(
    {
        "tags": ["Utils"],
        "description": "此API 用於上傳 CSV 檔案",
        "parameters": [
            {
                "name": "user_info",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "User information in JSON format",
            },
            {
                "name": "file",
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "The CSV file to upload",
            },
        ],
        "responses": {
            "200": {
                "description": "File uploaded successfully",
                "examples": {
                    "application/json": {"message": "File uploaded successfully"}
                },
            },
            "400": {
                "description": "Bad request due to missing file or wrong file type",
                "examples": {
                    "application/json": {"error": "No file part in the request"}
                },
            },
            "403": {
                "description": "Forbidden request",
                "examples": {"application/json": {"error": "Forbidden"}},
            },
            "500": {
                "description": "Internal Error",
                "examples": {"application/json": {"error": "Internal Server Error"}},
            },
        },
    }
)
def upload_csv_file():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("user_Id")

    # 確認 request 中是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 csv
    if file and allowed_file(file.filename, "csv"):
        # 確認目錄是否存在，若不存在則創建目錄

        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        current_file = TrainingFileRepo.find_first_training_file_by_user_id(
            user_id=user_id
        )
        is_renew = False  # 是否是覆蓋舊的
        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file is not None and (current_file.is_trained is False):
            os.remove(current_file.filename)
            TrainingFileRepo.delete_training_file_by_file_id(current_file.id)
            is_renew = True
        # 儲存檔案
        saved_file = TrainingFileRepo.create_trainingfile(
            user_id=user_id, original_file_name=file.filename
        )
        if saved_file is None:
            return (
                jsonify({"error": "Unable to create file."}),
                500,
            )
        file.save(os.path.join(FILE_DIRECTORY, saved_file.filename))
        if is_renew:
            return jsonify({"message": "File update successfully"}), 200
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only CSV files are allowed."}),
            400,
        )
